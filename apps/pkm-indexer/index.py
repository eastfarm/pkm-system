# File: apps/pkm-indexer/index.py
import os
import asyncio
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pkm-indexer")

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
            logger.info("No markdown files found in pkm directory. Creating empty index.")
            # Create a simple fallback index
            create_fallback_index("No documents available in knowledge base")
            return
            
        # Skip DirectoryLoader and go directly to manual loading
        logger.info("Found markdown files, starting indexing...")
        documents = manual_load_markdown_files('pkm')
        
        if not documents:
            create_fallback_index("Failed to load documents manually")
            return
        
        try:
            # Try importing required dependencies for splitting and indexing
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS
        except ImportError as e:
            logger.error(f"Failed to import required LangChain dependencies: {e}")
            create_fallback_index(f"Indexing failed due to missing dependencies: {e}")
            return
        
        # Continue with processing
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        
        # Try loading embeddings
        try:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        except Exception as embed_error:
            logger.error(f"Failed to load embeddings model: {embed_error}")
            create_fallback_index(f"Failed to load embeddings model: {embed_error}")
            return
            
        # Try creating vectorstore
        try:
            vectorstore = FAISS.from_documents(texts, embeddings)
            vectorstore.save_local("pkm_index")
            logger.info("Indexed PKM to pkm_index")
        except Exception as vectorstore_error:
            logger.error(f"Failed to create vector store: {vectorstore_error}")
            create_fallback_index(f"Failed to create vector store: {vectorstore_error}")
            return
            
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        create_fallback_index(f"Indexing failed: {e}")

def create_fallback_index(error_message):
    """Create a simple JSON file as a fallback when vectorstore creation fails"""
    fallback_path = os.path.join("pkm_index", "fallback.json")
    os.makedirs("pkm_index", exist_ok=True)
    
    with open(fallback_path, "w") as f:
        json.dump({
            "error": error_message,
            "is_fallback": True,
            "timestamp": str(datetime.now())
        }, f)
    
    logger.info(f"Created fallback index with error: {error_message}")

def manual_load_markdown_files(directory):
    """Manual implementation to load markdown files without using DirectoryLoader"""
    try:
        # Import Document class for creating document objects
        from langchain_core.documents import Document
        import frontmatter
        
        documents = []
        logger.info(f"Manually loading markdown files from {directory}")
        
        # Walk through all files in the directory
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Read the file
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Try to parse frontmatter
                        try:
                            post = frontmatter.loads(content)
                            metadata = dict(post.metadata)
                            text = post.content
                        except Exception as fm_error:
                            logger.warning(f"Frontmatter parsing failed for {file_path}: {fm_error}")
                            # If frontmatter parsing fails, use the whole content
                            metadata = {"source": file_path}
                            text = content
                        
                        # Create Document object
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": file_path,
                                **metadata
                            }
                        )
                        
                        documents.append(doc)
                        logger.info(f"Successfully loaded document: {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Error loading {file_path}: {e}")
        
        logger.info(f"Manually loaded {len(documents)} documents")
        return documents
    except Exception as e:
        logger.error(f"Failed in manual document loading: {e}")
        return []

async def searchKB(query):
    try:
        fallback_path = os.path.join("pkm_index", "fallback.json")
        
        # Check if we're using fallback mode
        if os.path.exists(fallback_path):
            with open(fallback_path, "r") as f:
                fallback_data = json.load(f)
            
            return f"Search unavailable: {fallback_data.get('error', 'Unknown indexing error')}"
            
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