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

def grade_generation_and_documents(state):
    """
    Determines whether the generation is grounded in the document and answers question.
    """
    print("---CHECK HALLUCINATIONS---")
    generation = state.get("generation")
    retry_count = state.get("retry_count", 0)
    
    if retry_count > 3:
        print("---DECISION: MAX RETRIES REACHED---")
        return END

    if generation is None:
        # It was grounded check fail, so we try again? Or we rewrite?
        # For this simplified flow, let's say if it failed grounding, we rewrite or regenerate.
        return "generate" # Simple loop back to generate (maybe with feedback in a real system)
    
    # If the earlier node returned a generation text (even "Sorry..."), we end.
    return END

workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node("rewrite_query", rewrite_query)
# workflow.add_node("hallucination_check", hallucination_check) # Merging logic into generate or edge often cleaner, but let's keep it separate if we want strict flow

# Logic for hallucination check is often better as a conditional edge or a node that outputs a status.
# The user asked for a specific "hallucination_check" node.
# Let's add it.
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
    retry_count = state.get("retry_count", 0)
    generation = state.get("generation")
    
    if generation is None and retry_count < 3:
         return "generate"
    elif generation is None and retry_count >= 3:
        return END # Failed
    
    # If generation is "Sorry..." or valid text
    return END

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
