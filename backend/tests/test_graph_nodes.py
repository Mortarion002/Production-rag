from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END

from app.graph import nodes
from app.graph.graph import decide_to_generate, check_hallucination_edge, check_retrieval_edge


class FakeLLM(Runnable):
    """
    ChatOpenAI is a pydantic model and rejects setting arbitrary attributes
    (e.g. monkeypatching .invoke directly raises a pydantic ValueError), so
    node tests swap the whole module-level llm_fast/llm_smart reference for
    this instead. It's a real Runnable, so prompt | FakeLLM() | parser still
    composes into a normal RunnableSequence exactly like the real chains.
    """

    def __init__(self, mock):
        self._mock = mock

    def invoke(self, input, config=None, **kwargs):
        return self._mock(input)


# --- Edge functions (pure) ---

def test_decide_to_generate_routes_to_rewrite_when_no_relevant_docs():
    assert decide_to_generate({"run_web_search": True}) == "rewrite_query"


def test_decide_to_generate_routes_to_generate_when_docs_relevant():
    assert decide_to_generate({"run_web_search": False}) == "generate"


def test_check_retrieval_edge_routes_to_error_handler_when_error_set():
    assert check_retrieval_edge({"retrieval_error": "Qdrant down"}) == "handle_retrieval_error"


def test_check_retrieval_edge_routes_to_grade_documents_when_no_error():
    assert check_retrieval_edge({"retrieval_error": None}) == "grade_documents"
    assert check_retrieval_edge({}) == "grade_documents"


def test_check_hallucination_edge_loops_when_generation_none():
    assert check_hallucination_edge({"generation": None, "retry_count": 1}) == "generate"


def test_check_hallucination_edge_ends_when_generation_set():
    assert check_hallucination_edge({"generation": "an answer", "retry_count": 0}) == END
    assert check_hallucination_edge({"generation": "fallback message", "retry_count": 3}) == END


# --- hallucination_check ---

def _score(value: str) -> AIMessage:
    return AIMessage(content=f'{{"score": "{value}"}}')


def test_hallucination_check_grounded_and_useful_clears_feedback(monkeypatch):
    monkeypatch.setattr(nodes, "llm_fast", FakeLLM(MagicMock(return_value=_score("yes"))))
    result = nodes.hallucination_check({
        "question": "q", "documents": [], "generation": "an answer", "retry_count": 0, "steps": [],
    })
    assert result["generation"] == "an answer"
    assert result["hallucination_feedback"] is None
    assert result["retry_count"] == 0


def test_hallucination_check_not_useful_sets_feedback_and_retries(monkeypatch):
    # hallucination_grader says grounded ("yes"), answer_grader says not useful ("no")
    monkeypatch.setattr(nodes, "llm_fast", FakeLLM(MagicMock(side_effect=[_score("yes"), _score("no")])))
    result = nodes.hallucination_check({
        "question": "what is X?", "documents": [], "generation": "unrelated answer", "retry_count": 0, "steps": [],
    })
    assert result["generation"] is None
    assert result["retry_count"] == 1
    assert "what is X?" in result["hallucination_feedback"]


def test_hallucination_check_ungrounded_sets_feedback_and_retries(monkeypatch):
    monkeypatch.setattr(nodes, "llm_fast", FakeLLM(MagicMock(return_value=_score("no"))))
    result = nodes.hallucination_check({
        "question": "q", "documents": [], "generation": "hallucinated answer", "retry_count": 1, "steps": [],
    })
    assert result["generation"] is None
    assert result["retry_count"] == 2
    assert result["hallucination_feedback"]


def test_hallucination_check_returns_fallback_when_retries_exhausted(monkeypatch):
    monkeypatch.setattr(nodes, "llm_fast", FakeLLM(MagicMock(return_value=_score("no"))))
    result = nodes.hallucination_check({
        "question": "q", "documents": [], "generation": "hallucinated answer", "retry_count": nodes.MAX_RETRIES, "steps": [],
    })
    assert result["generation"] is not None
    assert result["hallucination_feedback"] is None
    assert result["retry_count"] == nodes.MAX_RETRIES


# --- generate ---

def test_generate_injects_feedback_into_prompt_when_present(monkeypatch):
    mock_invoke = MagicMock(return_value=AIMessage(content="final answer"))
    monkeypatch.setattr(nodes, "llm_smart", FakeLLM(mock_invoke))

    result = nodes.generate({
        "question": "q",
        "documents": [],
        "steps": [],
        "hallucination_feedback": "Stick to the context only.",
    })

    assert result["generation"] == "final answer"
    sent_prompt = mock_invoke.call_args[0][0].to_string()
    assert "Stick to the context only." in sent_prompt


def test_generate_omits_feedback_section_when_absent(monkeypatch):
    mock_invoke = MagicMock(return_value=AIMessage(content="final answer"))
    monkeypatch.setattr(nodes, "llm_smart", FakeLLM(mock_invoke))

    nodes.generate({"question": "q", "documents": [], "steps": []})

    sent_prompt = mock_invoke.call_args[0][0].to_string()
    assert "Note:" not in sent_prompt


# --- retrieve ---

def test_retrieve_sets_retrieval_error_instead_of_raising(monkeypatch):
    def _raise():
        raise ConnectionError("Qdrant unreachable")

    monkeypatch.setattr("app.services.ingestion.get_retriever", _raise)

    result = nodes.retrieve({"question": "q", "steps": []})

    assert result["documents"] == []
    assert "Qdrant unreachable" in result["retrieval_error"]


def test_retrieve_clears_retrieval_error_on_success(monkeypatch):
    fake_retriever = MagicMock()
    fake_retriever.invoke.return_value = ["doc1"]
    monkeypatch.setattr("app.services.ingestion.get_retriever", lambda: fake_retriever)

    result = nodes.retrieve({"question": "q", "steps": []})

    assert result["documents"] == ["doc1"]
    assert result["retrieval_error"] is None
