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
    """
    question: str
    generation: Optional[str]
    documents: List[Document]
    run_web_search: bool
    retry_count: int
