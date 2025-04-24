import os
import asyncio
from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import BeautifulSoupTransformer
from langchain_core.documents import Document

# Set USER_AGENT environment variable
os.environ["USER_AGENT"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

async def load_data():
    # Load HTML asynchronously
    loader = AsyncChromiumLoader(["https://www.morgan.edu/computer-science/faculty-and-staff"])
    html = await loader.aload()

    # Transform
    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["p"])
    page_content = "\n".join([doc.page_content for doc in docs_transformed])
    meta_data = {"source":"morgan cs website"}

    langchain_docs = Document(page_content=page_content, meta_data=meta_data)
    # Print Result
    print(langchain_docs)

# Run the async function
asyncio.run(load_data())
