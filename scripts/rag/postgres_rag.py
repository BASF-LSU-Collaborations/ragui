#!/usr/bin/env python3
"""
PostgreSQL-based RAG (Retrieval-Augmented Generation) System

This script implements a RAG system using PostgreSQL vector database for document retrieval
instead of ChromaDB. It retrieves relevant document chunks based on semantic similarity
and generates responses using OpenAI's API.
"""

import os
import sys
import json
import urllib.parse
from time import time
from typing import List, Dict, Tuple, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

# Add PostgreSQL vector database pipeline to Python path
sys.path.append('/shared_folders/team_1/mark_vdb/vdb_pipeline')

# Import required modules from the vector database pipeline
try:
    from init_vector_db import init_vector_db
    from search_vdb import search_vdb
    from vector import vector
    from variables import MODEL, NUM_OF_SEARCH_RESULTS
    from sentence_transformers import SentenceTransformer
    print("✅ PostgreSQL VDB modules loaded successfully")
    print(f"Using model: {MODEL}")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Load API keys from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Path to the JSON mapping file that contains file_path -> real_path mappings
STORE_JSON_PATH = "/shared_folders/team_1/colton_bruni/store_clean_test.json"

def load_store_data():
    """Load the store JSON mapping file."""
    try:
        with open(STORE_JSON_PATH, "r") as f:
            return json.load(f)
        print("✅ JSON mapping file loaded successfully")
    except Exception as e:
        print(f"⚠️ Error reading JSON mapping file: {e}")
        return {}


### 🔹 STEP 1: Rephrase the Technical Query Using Chat History
def rephrase_question(user_question: str, chat_history: list[str]) -> str:
    """
    Rephrase the question to make it self-contained, incorporating the chat history.
    This ensures the technical query fully references any missing context.
    """
    relevant_history = "\n".join(chat_history)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that rephrases technical queries to include all necessary context, especially for chemical engineering and industrial documentation."},
            {"role": "user", "content": f"Conversation history:\n{relevant_history}\n\nRephrase this technical question so that it fully references any missing subjects: '{user_question}'"}
        ],
        temperature=0.3,
        max_tokens=50
    )
    return response.choices[0].message.content.strip()


### 🔹 STEP 2: Retrieve Relevant Document Chunks from PostgreSQL Vector DB
def retrieve_documents(query: str, top_n: int = 5) -> List[Dict]:
    """
    Retrieve the top N relevant document chunks from the PostgreSQL vector database.
    
    Each returned entry includes document metadata and content along with similarity score.
    """
    # Initialize the database connection
    print(f"🔍 Searching for: '{query}'")
    start_time = time()
    
    # Perform vector search
    results = search_vdb(query, num_results=top_n)
    elapsed = time() - start_time
    print(f"✅ Found {len(results)} results in {elapsed:.2f} seconds")
    
    # Load the store data for file path mapping
    store_data = load_store_data()
    
    # Format results: Each document chunk with metadata and content
    documents = []
    for i, result in enumerate(results, 1):
        # Process result based on its format (could be tuple or dict)
        if isinstance(result, tuple):
            # Expected column order: id, chunkid, description, category, md, filepath, markdown, embedding, score
            doc_id = result[0]
            chunk_id = result[1]
            description = result[2]
            category = result[3]
            metadata = result[4]
            filepath = result[5]
            content = result[6]
            similarity_score = result[8] if len(result) > 8 else None
        elif isinstance(result, dict):
            doc_id = result.get("id")
            chunk_id = result.get("chunkid")
            description = result.get("description")
            category = result.get("category")
            metadata = result.get("md", {})
            filepath = result.get("filepath", "")
            content = result.get("markdown", "")
            similarity_score = result.get("score")
        else:
            print(f"⚠️ Unrecognized result format for result {i}")
            continue

        # Map to local file path
        if filepath.startswith("/data/projects/filefindr/"):
            local_path = filepath.replace("/data/projects/filefindr/", "/shared_folders/team_1/document_batch/")
        else:
            local_path = filepath
            
        # Get real path from store data if available
        file_key = filepath.split('/')[-1] if filepath else "Unknown"
        mapping = store_data.get(file_key, {})
        real_path = mapping.get("real_path", local_path)
        
        documents.append({
            "id": doc_id,
            "chunk_id": chunk_id,
            "description": description,
            "category": category,
            "metadata": metadata,
            "filepath": filepath,
            "local_path": local_path,
            "real_path": real_path,
            "content": content,
            "similarity_score": similarity_score
        })
    
    return documents


### 🔹 STEP 3: Generate a Technical Response Using OpenAI
def generate_document_response(query: str, documents: List[Dict], purpose: str = "summary") -> str:
    """
    Generate a response based on the retrieved document chunks.
    The response will reference the source files and provide a concise technical answer.
    """
    if not documents:
        return "I couldn't find any relevant information. Please try rephrasing your query or broadening the search."
    
    # Prepare document content block for the prompt
    doc_block = ""
    for i, doc in enumerate(documents, 1):
        doc_block += f"Chunk {i}:\n"
        doc_block += f"Source: {doc['filepath']}\n"
        doc_block += f"Content: {doc['content'][:500]}{'...' if len(doc['content']) > 500 else ''}\n"
        if doc['similarity_score'] is not None:
            doc_block += f"Relevance Score: {doc['similarity_score']}\n"
        doc_block += "\n"
    
    system_message = (
        "You are an expert assistant in chemical engineering and industrial documentation. "
        "When providing answers, reference the source files as 'Chunk X'. "
        "Focus on technical accuracy and clarity. Be concise but thorough."
    )
    
    prompt = f"""
User Query: "{query}"

I have retrieved the following document chunks from our technical documentation collection:
{doc_block}

Based on the above documents, please provide a concise and accurate technical response that references the source files.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()


### 🔹 STEP 4: Full PostgreSQL RAG Function
def postgres_rag(user_request: str, chat_history: List[str], top_n: int = 5, purpose: str = "summary") -> Tuple[str, Dict]:
    """
    Main RAG function that orchestrates the entire process:
    1. Rephrase the user's technical query using chat history.
    2. Retrieve relevant document chunks from the PostgreSQL vector database.
    3. Generate a technical response that references the source files.
    4. Return the response along with a dictionary of unique source files and their paths.
    """
    # Initialize the PostgreSQL database connection
    database, engine = init_vector_db(wipe_database=False)
    print("✅ Connected to PostgreSQL vector database")
    
    # Rephrase the query for better retrieval
    rephrased = rephrase_question(user_request, chat_history)
    print(f"📝 Rephrased query: {rephrased}")
    
    # Retrieve relevant documents
    matching_documents = retrieve_documents(rephrased, top_n=top_n)
    
    if not matching_documents:
        return ("I couldn't find any relevant information. Please try rephrasing your query or broadening the search.", {})
    
    # Generate response
    response = generate_document_response(rephrased, matching_documents, purpose)
    
    # Collect unique source files and their paths
    unique_sources = {}
    for doc in matching_documents:
        source_file = doc.get("filepath", "Unknown")
        local_path = doc.get("local_path", "Not Available")
        real_path = doc.get("real_path", local_path)
        
        if source_file not in unique_sources:
            unique_sources[source_file] = real_path
    
    return response, unique_sources


### 🔹 TESTING THE POSTGRES RAG SYSTEM
if __name__ == "__main__":
    # Test conversation history
    conversation_history = [
        "Hi, I'm reviewing our chemical engineering documentation.",
        "I'm particularly interested in how catalytic processes work in our reactors."
    ]
    
    # Example: A technical query
    user_request = "Explain the catalytic processes and reactions in our latest designs."
    
    print("\n🧪 User Request:", user_request)
    response, sources = postgres_rag(user_request, conversation_history)
    
    print("\n🧪 Generated Response:\n", response)
    print("\n📚 Referenced Sources:")
    for source, path in sources.items():
        print(f"- {source}: {path}")