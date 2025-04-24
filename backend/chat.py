import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph
from typing import List, TypedDict
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import re


# Load environment variables
load_dotenv()

# Initialize ElevenLabs for Voice Responses
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# Define state for application
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

def initialize_graph():
    # Get API keys
    openai_api_key = os.getenv("OPENAI_KEY")
    groq_api_key = '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'

    # Initialize LLM and embeddings
    llm = init_chat_model(model="llama3-8b-8192", api_key=groq_api_key, model_provider='groq', max_tokens = 200, temperature = 0.7)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=openai_api_key)

    # Set up vector store for Classes
    connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
    collection_name = "prof_docs"
    course_vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )
    connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
    collection_name = "prof_info"
    prof_vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )

    # Define prompt template
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an AI Academic Assistant(Benny) for Morgan State University's Computer Science department with a fun and quirky personality. Your goal is to help students by answering their questions accurately and in a friendly, conversational tone. Your responses should be very brief and not long winded. 

Instructions:

1.  Read the provided context carefully. The context contains the information necessary to answer the student's question.
2.  Answer the student's question directly and factually. Ensure the information you provide is accurate and based solely on the context.
3.  Avoid explicitly stating that the information comes from the provided context. Instead, present the information as if you are directly providing it in a friendly manner.
4.  Use a friendly and conversational tone. Imagine you are a helpful peer or advisor assisting the student. Employ natural language and avoid overly formal or robotic phrasing.
5.  If possible, incorporate elements of the student's question into your response to create a more natural flow.
6.  Prioritize clarity and conciseness. Deliver the information in a way that is easy for the student to understand.

Example:

Context: Dr. Shuangbao "Paul" Wang's email address is shuangbao.wang@morgan.edu.

Student Question: How do I contact Dr. Wang?

Good Response: You can reach Dr. Shuangbao "Paul" Wang at shuangbao.wang@morgan.edu.

Bad Response: According to the provided context, Dr. Shuangbao "Paul" Wang's email address is shuangbao.wang@morgan.edu.
"""),
        ("human", "Question: {question}\n\nContext: {context}")
    ])


    # Define application steps
    def retrieve(state: State):
        question = state['question']
        course_code = get_course(question) #grab the course code from the users answer
        # Check for professor-related keywords AND course-related keywords
        if ("professor" in question.lower() or "faculty" in question.lower() or "instructor" in question.lower()) and ("course" in question.lower() or "teach" in question.lower() or "class" in question.lower()):
            retrieved_docs = course_vector_store.similarity_search(question, k=10) # Likely the course data has this info
            return {"context": retrieved_docs}
        elif "professor" in question.lower() or "faculty" in question.lower() or "instructor" in question.lower():
            retrieved_docs = prof_vector_store.similarity_search(question, k=10)
            return {"context": retrieved_docs}
        else: # Assume it's primarily a question about courses
            retrieved_docs = course_vector_store.similarity_search(question, k=10)
            if course_code:
                grounded_docs = [
                    doc for doc in retrieved_docs
                    if course_code in doc.metadata.get("course_name","").replace(" ","").upper()
                ]
                if grounded_docs:
                    return {"context": grounded_docs}
        
        return {"context": retrieved_docs}

    def get_course(text:str):
        match = re.search(r'(COSC\s?\d{3})',text, re.IGNORECASE)
        return match.group(1).upper().replace(" ", "") if match else None
    
    def generate(state: State):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        formatted_prompt = prompt_template.format_messages(
            question=state["question"],
            context=docs_content
        )
        response = llm.invoke(formatted_prompt)
        return {"answer": response.content}

    # Build and compile the graph
    workflow = StateGraph(State)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    return workflow.compile(), course_vector_store, prof_vector_store

# Initialize the graph and vector stores
graph, course_vectore_store, prof_vector_store = initialize_graph()