from typing import TypedDict, List
import os
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# 1. Define the State
class AgentState(TypedDict):
    query: str
    context: List[str] 
    brief: str
    is_relevant: bool

# 2. Define the Nodes
def retrieve_node(state: AgentState):
    return {"context": state.get("context", ["No context provided"])}

def grade_node(state: AgentState):
    # Pro-tip: You could add logic here to check if context is empty
    return {"is_relevant": True}

def generate_brief_node(state: AgentState):
    # This model handles 1 million tokens - no more truncation needed!
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=os.getenv("GOOGLE_API_KEY") # Use env for security!
    )

    # You can now send the ENTIRE context without [:30000]
    full_context = "\n\n".join(state["context"])

    system_message = (
        "You are a professional AI Research Assistant. You are provided with text "
        "extracted from multiple PDF files.\n\n"
        "1. Compare information across documents if necessary.\n"
        "2. Always cite the filename of the document you are quoting.\n"
        "3. If documents contradict each other, point it out."
    )

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "User Query: {query}\n\nPDF Context:\n{context}")
    ])

    chain = prompt_template | llm
    
    response = chain.invoke({
        "query": state["query"],
        "context": full_context
    })
    
    return {"brief": response.content}


# 3. Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_node)
workflow.add_node("generate", generate_brief_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "grade")

workflow.add_conditional_edges(
    "grade",
    lambda x: "generate" if x["is_relevant"] else END
)
workflow.add_edge("generate", END)

app = workflow.compile()