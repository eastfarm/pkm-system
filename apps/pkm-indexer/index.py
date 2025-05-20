# File: apps/pkm-indexer/index.py
import os
import logging
import json
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pkm-indexer")

# Simple text-based search as a fallback
def simple_text_search(query, directory="pkm", limit=3):
    """
    Perform a simple text-based search on markdown files.
    This is a fallback when vector search is not available.
    """
    results = []
    query_terms = query.lower().split()
    
    try:
        # Walk through all markdown files in the directory
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Read the file content
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        # Calculate a simple relevance score
                        score = 0
                        content_lower = content.lower()
                        
                        # Check for exact phrase match (highest relevance)
                        if query.lower() in content_lower:
                            score += 10
                        
                        # Check for individual term matches
                        for term in query_terms:
                            score += content_lower.count(term)
                        
                        # If there's any match, add to results
                        if score > 0:
                            # Extract title from frontmatter or filename
                            title = file
                            title_match = re.search(r"title:\s*(.+)", content)
                            if title_match:
                                title = title_match.group(1).strip()
                            
                            results.append({
                                "score": score,
                                "title": title,
                                "content": content,
                                "path": file_path
                            })
                    
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
        
        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return results[:limit]
    
    except Exception as e:
        logger.error(f"Error in simple search: {e}")
        return []

async def indexKB():
    """
    Simple placeholder for the indexing function.
    This version doesn't use FAISS or sentence-transformers.
    """
    try:
        # Create folders if they don't exist
        os.makedirs("pkm", exist_ok=True)
        os.makedirs("pkm_index", exist_ok=True)
        
        # Create a simple index file to indicate successful indexing
        index_info = {
            "indexed_at": datetime.now().isoformat(),
            "method": "simple_text_search",
            "status": "ready"
        }
        
        with open(os.path.join("pkm_index", "index_info.json"), "w") as f:
            json.dump(index_info, f)
            
        logger.info("Created simple text search index")
        return True
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        return False

async def searchKB(query):
    """
    Search the knowledge base using simple text search.
    This is a fallback when FAISS is not available.
    """
    try:
        # Check if pkm directory exists
        if not os.path.exists("pkm"):
            return "No documents found in your knowledge base. Please add content first."
        
        # Perform simple text search
        results = simple_text_search(query)
        
        if not results:
            return "No relevant documents found for your query."
        
        # Format results
        formatted_results = []
        for result in results:
            # Format the content
            content_preview = result["content"]
            if len(content_preview) > 1000:
                content_preview = content_preview[:1000] + "..."
                
            formatted_results.append(f"## {result['title']}\n\n{content_preview}\n\n")
        
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        return f"Search failed: {e}"