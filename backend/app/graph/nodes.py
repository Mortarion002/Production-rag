from typing import Any, Dict
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.config import settings
from app.graph.state import GraphState

# --- Initialize LLMs ---
llm_fast = ChatOpenAI(model=settings.LLM_MODEL_FAST, temperature=0, api_key=settings.OPENAI_API_KEY)
llm_smart = ChatOpenAI(model=settings.LLM_MODEL_SMART, temperature=0, api_key=settings.OPENAI_API_KEY)

# --- Prompts ---
# Re-writer
rewrite_prompt = PromptTemplate(
    template="""You a question re-writer that converts an input question to a better version that is optimized \n 
    for vectorstore retrieval. Look at the initial and formulate an improved question. \n
    Here is the initial question: \n\n {question}. Improved question with no preamble: \n """,
    input_variables=["question"],
)

# Grader
grade_prompt = PromptTemplate(
    template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
    Here is the retrieved document: \n\n {document} \n\n
    Here is the user question: {question} \n
    If the document contains keywords or semantic meaning related to the question, grade it as relevant. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question. \n
    Provide the binary score as a JSON with a single key 'score' and no premable or explanation.""",
    input_variables=["question", "document"],
)

# Generator
generate_prompt = PromptTemplate(
    template="""You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. \n
    If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise. \n
    {feedback_section}Question: {question} \n
    Context: {context} \n
    Answer:""",
    input_variables=["question", "context", "feedback_section"],
)

MAX_RETRIES = 3

# Hallucination Checker
hallucination_prompt = PromptTemplate(
    template="""You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. \n 
    Here are the facts:
    \n ------- \n
    {documents} 
    \n ------- \n
    Here is the answer: {generation}
    Give a binary score 'yes' or 'no' score to indicate whether the answer is grounded in / supported by a set of facts. \n
    Provide the binary score as a JSON with a single key 'score' and no premable or explanation.""",
    input_variables=["generation", "documents"],
)

answer_grader_prompt = PromptTemplate(
    template="""You are a grader assessing whether an answer matches / resolves a question \n 
    Here is the answer:
    \n ------- \n
    {generation} 
    \n ------- \n
    Here is the question: {question}
    Give a binary score 'yes' or 'no' score to indicate whether the answer resolves the question. \n
    Provide the binary score as a JSON with a single key 'score' and no premable or explanation.""",
    input_variables=["generation", "question"],
)


# --- Nodes ---

def retrieve(state: GraphState):
    """
    Retrieve documents from vectorstore

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE---")
    question = state["question"]
    steps = state.get("steps", []) + ["retrieve"]

    # Implement actual Qdrant retrieval
    try:
        from app.services.ingestion import get_retriever
        retriever = get_retriever()
        docs = retriever.invoke(question)
    except Exception as e:
        print(f"Error during retrieval: {e}")
        raise e
        # Fallback for resiliency
        # docs = [Document(page_content=f"Could not retrieve documents. Error: {e}")]

    return {"documents": docs, "question": question, "steps": steps}

def generate(state: GraphState):
    """
    Generate answer using RAG on retrieved documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    steps = state.get("steps", []) + ["generate"]
    feedback = state.get("hallucination_feedback")
    feedback_section = f"Note: {feedback} \n    " if feedback else ""

    # RAG generation
    rag_chain = generate_prompt | llm_smart | StrOutputParser()
    generation = rag_chain.invoke({"context": documents, "question": question, "feedback_section": feedback_section})
    return {"documents": documents, "question": question, "generation": generation, "steps": steps}

def grade_documents(state: GraphState):
    """
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will filter it out

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Update documents key with only relevant documents
    """
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    steps = state.get("steps", []) + ["grade_documents"]

    # Score each doc
    grader = grade_prompt | llm_fast | JsonOutputParser()
    
    filtered_docs = []
    run_web_search = False # Default

    for d in documents:
        score = grader.invoke({"question": question, "document": d.page_content})
        grade = score['score']
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            # If we filter out too many, maybe we flag for web search (optional extension)
            continue
            
    if not filtered_docs:
        print("---GRADE: NO RELEVANT DOCUMENTS, RUN WEB SEARCH/REWRITE---")
        run_web_search = True
        
    return {"documents": filtered_docs, "question": question, "run_web_search": run_web_search, "steps": steps}

def rewrite_query(state: GraphState):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """
    print("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]
    steps = state.get("steps", []) + ["rewrite_query"]

    # Re-write question
    chain = rewrite_prompt | llm_fast | StrOutputParser()
    better_question = chain.invoke({"question": question})
    return {"documents": documents, "question": better_question, "steps": steps}

def hallucination_check(state: GraphState):
    """
    Checks if the generation is grounded in the documents and answers the question.
    """
    print("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    retry_count = state.get("retry_count", 0)
    steps = state.get("steps", []) + ["hallucination_check"]

    hallucination_grader = hallucination_prompt | llm_fast | JsonOutputParser()
    answer_grader = answer_grader_prompt | llm_fast | JsonOutputParser()

    score = hallucination_grader.invoke({"documents": documents, "generation": generation})
    grade = score['score']

    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check answer relevance
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score['score']
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return {"generation": generation, "retry_count": retry_count, "hallucination_feedback": None, "steps": steps}

        print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
        if retry_count >= MAX_RETRIES:
            return {
                "generation": "I wasn't able to produce an answer that directly addresses your question based on the available documents.",
                "retry_count": retry_count,
                "hallucination_feedback": None,
                "steps": steps,
            }
        feedback = f"Your previous answer did not directly address the question '{question}'. Answer that question directly and concisely using only the context below."
        return {"generation": None, "retry_count": retry_count + 1, "hallucination_feedback": feedback, "steps": steps}

    print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS---")
    if retry_count >= MAX_RETRIES:
        return {
            "generation": "I couldn't verify that my answer is fully supported by the provided documents, so I'm unable to give a confident response.",
            "retry_count": retry_count,
            "hallucination_feedback": None,
            "steps": steps,
        }
    feedback = "Your previous answer included claims not supported by the provided context. Rewrite the answer using only information found in the context below; if the context doesn't contain the answer, say you don't know."
    return {"generation": None, "retry_count": retry_count + 1, "hallucination_feedback": feedback, "steps": steps}
