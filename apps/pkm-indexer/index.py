# Updated imports for langchain 0.2.0
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os
import asyncio

async def indexKB():
    try:
        # Create folders if they don't exist
        os.makedirs("pkm", exist_ok=True)
        os.makedirs("pkm_index", exist_ok=True)
        
        # Check if any markdown files exist
        has_md_files = False
        for root, dirs, files in os.walk("pkm"):
            if any(file.endswith(".md") for file in files):
                has_md_files = True
                break
        
        if not has_md_files:
            print("No markdown files found in pkm directory. Creating empty index.")
            # Create an empty index
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectorstore = FAISS.from_texts(["placeholder"], embeddings)
            vectorstore.save_local("pkm_index")
            return
            
        # Continue with normal indexing if files exist
        loader = DirectoryLoader('pkm', glob="**/*.md")
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)
        vectorstore.save_local("pkm_index")
        print("Indexed PKM to pkm_index")
    except Exception as e:
        print(f"Indexing failed: {e}")
        # Create an empty index as fallback
        try:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectorstore = FAISS.from_texts(["Error creating index. Please add content to pkm folder."], embeddings)
            vectorstore.save_local("pkm_index")
        except Exception as inner_e:
            print(f"Failed to create fallback index: {inner_e}")

async def searchKB(query):
    try:
        if not os.path.exists("pkm_index"):
            return "No index found. Please add documents to your PKM system first."
            
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local("pkm_index", embeddings)
        docs = vectorstore.similarity_search(query, k=3)
        
        if not docs:
            return "No relevant documents found for your query."
            
        return "\n\n---\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Search failed: {e}"