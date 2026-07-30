from typing import List, TypedDict, Optional
from langchain_core.documents import Document

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        run_web_search: whether to add web search
        retry_count: number of retries for generation/hallucination checks
        hallucination_feedback: corrective note from hallucination_check for the next generate attempt
        steps: names of nodes visited, in execution order, for reporting back to the caller
        retrieval_error: set by retrieve() when the vector store is unreachable, short-circuits to a fallback answer
    """
    question: str
    generation: Optional[str]
    documents: List[Document]
    run_web_search: bool
    retry_count: int
    hallucination_feedback: Optional[str]
    steps: List[str]
    retrieval_error: Optional[str]
