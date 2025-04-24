import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing import List, TypedDict
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

# Get API key - use OPENAI_API_KEY as this is the standard name
openai_api_key = os.getenv("OPENAI_KEY")
if not openai_api_key:
    raise ValueError("Please set OPENAI_API_KEY in your environment variables")

#embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=openai_api_key)

# #Load &process documents (put in text file and read as a string)
loader = WebBaseLoader(
    web_paths=("https://www.morgan.edu/computer-science/faculty-and-staff","https://www.morgan.edu/computer-science/faculty-and-staff/shuangbao-wang","https://www.morgan.edu/computer-science/faculty-and-staff/md-rahman","https://www.morgan.edu/computer-science/faculty-and-staff/amjad-ali","https://www.morgan.edu/computer-science/faculty-and-staff/radhouane-chouchane","https://www.morgan.edu/computer-science/faculty-and-staff/monireh-dabaghchian","https://www.morgan.edu/computer-science/faculty-and-staff/jamell-dacon","https://www.morgan.edu/computer-science/faculty-and-staff/naja-mack","https://www.morgan.edu/computer-science/degrees-and-programs","https://www.morgan.edu/computer-science/admission-and-application"),
    bs_kwargs=dict( 
        parse_only=bs4.SoupStrainer(
            class_=("profile-box","body-copy","copy"),
        )
    ),
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=201)
all_splits = text_splitter.split_documents(docs)

# Set up vector store
connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
collection_name = "prof_info"

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)

# Index chunks
vector_store.add_documents(documents=all_splits)