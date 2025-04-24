from langchain_core.documents import Document
import tempfile
from vector_store import embeddings, PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.document_loaders import TextLoader
from markitdown import MarkItDown

def add_transcript(transcript = r'C:\Users\lenye\Downloads\Academic Transcript.pdf'):
    import logging
    logging.getLogger("pdfminer").setLevel(logging.WARNING)
    md = MarkItDown(enable_plugins=False)
    result = md.convert(transcript)
    text_content = result.text_content
    # Save markdown to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as tmp_md:
        tmp_md.write(text_content)
        tmp_md_path = tmp_md.name

    # Load markdown file as documents
    loader = TextLoader(tmp_md_path,encoding="utf-8")
    docs = loader.load()

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=201)
    all_splits = text_splitter.split_documents(docs)

    connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"
    collection_name = "student_docs"

    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )

    document = Document(page_content = text_content)
    vector_store.add_documents(all_splits)
add_transcript()