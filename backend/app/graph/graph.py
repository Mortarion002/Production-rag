from langgraph.graph import END, StateGraph
from app.graph.state import GraphState
from app.graph.nodes import retrieve, grade_documents, generate, rewrite_query, hallucination_check

def decide_to_generate(state):
    """
    Determines whether to generate an answer, or re-generate a question.
    """
    print("---ASSESS GRADED DOCUMENTS---")
    run_web_search = state["run_web_search"]
    
    if run_web_search:
        # All documents were filtered out, so we re-generate
        print("---DECISION: TRANSFORM QUERY---")
        return "rewrite_query"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: GENERATE---")
        return "generate"

workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("hallucination_check", hallucination_check)


# Build graph
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade_documents")

workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "rewrite_query": "rewrite_query",
        "generate": "generate",
    },
)
workflow.add_edge("rewrite_query", "retrieve")
workflow.add_edge("generate", "hallucination_check")

def check_hallucination_edge(state):
    """
    hallucination_check always resolves `generation` to a non-None value
    (either a real answer or a fallback message) once retries are exhausted,
    so a None generation here always means "loop back and try again".
    """
    return "generate" if state.get("generation") is None else END

workflow.add_conditional_edges(
    "hallucination_check",
    check_hallucination_edge,
    {
        "generate": "generate",
        END: END
    }
)

# Compile
app = workflow.compile()
