# File: apps/pkm-indexer/index.py
import os
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pkm-indexer")

async def indexKB():
    try:
        # Create folders if they don't exist
        os.makedirs("pkm", exist_ok=True)
        os.makedirs("pkm_index", exist_ok=True)
        
        # Try importing required dependencies
        try:
            from langchain_community.document_loaders import DirectoryLoader
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS
        except ImportError as e:
            logger.error(f"Failed to import required dependencies: {e}")
            # Create a text file as a placeholder index
            with open("pkm_index/error.txt", "w") as f:
                f.write(f"Indexing failed due to missing dependencies: {e}")
            return
        
        # Check if any markdown files exist
        has_md_files = False
        for root, dirs, files in os.walk("pkm"):
            if any(file.endswith(".md") for file in files):
                has_md_files = True
                break
        
        if not has_md_files:
            logger.info("No markdown files found in pkm directory. Creating empty index.")
            try:
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                vectorstore = FAISS.from_texts(["placeholder"], embeddings)
                vectorstore.save_local("pkm_index")
            except Exception as e:
                logger.error(f"Failed to create empty index: {e}")
                # Create a text file as a placeholder index
                with open("pkm_index/empty.txt", "w") as f:
                    f.write("No documents found. Please add content to your PKM system.")
            return
            
        # Continue with normal indexing if files exist
        logger.info("Found markdown files, starting indexing...")
        loader = DirectoryLoader('pkm', glob="**/*.md")
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(texts, embeddings)
        vectorstore.save_local("pkm_index")
        logger.info("Indexed PKM to pkm_index")
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        # Create a text file as a placeholder index
        with open("pkm_index/error.txt", "w") as f:
            f.write(f"Indexing failed: {e}")

async def searchKB(query):
    try:
        # First check if we have a real index or just error files
        if os.path.exists("pkm_index/error.txt"):
            with open("pkm_index/error.txt", "r") as f:
                error_msg = f.read()
            return f"Search unavailable: {error_msg}"
            
        if os.path.exists("pkm_index/empty.txt"):
            return "No documents found in your knowledge base. Please add content first."
            
        # Try importing required dependencies
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS
        except ImportError as e:
            return f"Search failed: Could not import required libraries. {str(e)}"
            
        if not os.path.exists("pkm_index"):
            return "No index found. Please add documents to your PKM system first."
            
        # Try loading the embeddings model
        try:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception as e:
            return f"Search failed: Could not load embeddings model. {str(e)}"
            
        # Try loading the vector store
        try:
            vectorstore = FAISS.load_local("pkm_index", embeddings)
        except Exception as e:
            return f"Search failed: Could not load search index. {str(e)}"
            
        docs = vectorstore.similarity_search(query, k=3)
        
        if not docs:
            return "No relevant documents found for your query."
            
        return "\n\n---\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        return f"Search failed: {e}"