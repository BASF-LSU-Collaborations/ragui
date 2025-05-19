#!/usr/bin/env python3
"""
rag_retriever.py

Provides functions to retrieve relevant document chunks from the vector database
and format them as context for a RAG system.
"""

import sys
import time
import warnings
from typing import List, Tuple, Dict, Any

# --- Configuration ---
# Adjust this path to point to your VDB pipeline location
# Consider using environment variables or a config file in a real application
VDB_PIPELINE_PATH = "/shared_folders/team_1/mark_vdb/vdb_pipeline" #<-- ADJUST IF NEEDED

# Define the expected indices for the returned list/tuple from search_vdb
# Based on test.py output: [id, semantic_score, bm25_score, fused_score, filepath, markdown_path, content]
IDX_ID = 0
IDX_SEMANTIC_SCORE = 1
IDX_BM25_SCORE = 2
IDX_FUSED_SCORE = 3
IDX_FILEPATH = 4 # Path to original file (e.g., PDF)
IDX_MARKDOWN_PATH = 5 # Path to processed markdown file
IDX_CONTENT = 6 # Actual text content of the chunk
EXPECTED_RESULT_LENGTH = 7

# --- Add VDB pipeline to Python path ---
if VDB_PIPELINE_PATH not in sys.path:
    sys.path.append(VDB_PIPELINE_PATH)

# --- Import VDB pipeline functions ---
try:
    from init_vector_db import init_vector_db
    from search_vdb import search_vdb
    INIT_DB_AVAILABLE = True
    SEARCH_AVAILABLE = True
    print("✅ VDB pipeline functions imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import one or more VDB functions: {e}")
    if 'init_vector_db' not in locals(): INIT_DB_AVAILABLE = False
    if 'search_vdb' not in locals(): SEARCH_AVAILABLE = False
    # Define placeholders if imports fail
    def init_vector_db(wipe_database=False): return None, None
    def search_vdb(query, num_results=3): return []

# --- Core Retrieval Function ---

def retrieve_and_format_context(query: str, num_chunks: int = 3) -> Tuple[str, Dict[str, str]]:
    """
    Performs a hybrid search, retrieves relevant chunks, and formats them into a context block.

    Args:
        query (str): The user's search query.
        num_chunks (int): The maximum number of relevant chunks to retrieve.

    Returns:
        Tuple[str, Dict[str, str]]: A tuple containing:
            - context_block (str): Formatted string containing the content of retrieved chunks.
            - retrieved_sources (Dict[str, str]): Dictionary mapping original source file paths
                                                  to their corresponding markdown paths.
                                                  Returns empty dict if no results.
    """
    session = None
    engine = None
    context_block = ""
    retrieved_sources = {}
    search_results = []

    print(f"\n--- Starting Retrieval for Query: '{query}' ---")

    if not INIT_DB_AVAILABLE or not SEARCH_AVAILABLE:
        warnings.warn("❌ Cannot retrieve context: Required VDB functions not available.")
        return "", {}

    try:
        # 1. Connect to the database (consider managing connection externally for efficiency)
        # print("Connecting to database for retrieval...")
        connect_start_time = time.time()
        session, engine = init_vector_db(wipe_database=False)

        if not engine:
            warnings.warn("   ❌ Failed to establish database connection.")
            return "", {}
        # print(f"   Connected in {time.time() - connect_start_time:.2f}s")

        # 2. Perform the search
        # print(f"Performing search (Top {num_chunks} chunks)...")
        search_start_time = time.time()
        try:
            search_results = search_vdb(query, num_results=num_chunks)
            # print(f"   Search completed in {time.time() - search_start_time:.2f}s")
            # print(f"   Retrieved {len(search_results)} chunks.")
        except Exception as search_error:
            warnings.warn(f"   ❌ Error during search_vdb(): {search_error}")
            search_results = [] # Ensure it's empty on error

        # 3. Extract Content and Format Context Block
        # print("Processing retrieved chunks...")
        if search_results:
            for i, hit in enumerate(search_results):
                # print(f"Processing Hit {i+1}...")
                if isinstance(hit, (list, tuple)) and len(hit) == EXPECTED_RESULT_LENGTH:
                    # Extract relevant data
                    doc_id = hit[IDX_ID]
                    filepath = hit[IDX_FILEPATH] # Original file path
                    markdown_path = hit[IDX_MARKDOWN_PATH] # Processed file path
                    content = hit[IDX_CONTENT] # The actual chunk content
                    fused_score = hit[IDX_FUSED_SCORE]

                    if isinstance(content, str) and content.strip():
                        # Format the chunk for the context block
                        context_block += f"--- Chunk {i+1} (ID: {doc_id}, Score: {fused_score:.4f}) ---\n"
                        context_block += f"Source Document: {filepath}\n" # Use original path as source ref
                        context_block += f"Content:\n{content}\n\n"

                        # Store unique source documents
                        if filepath not in retrieved_sources:
                             retrieved_sources[filepath] = markdown_path # Store mapping if needed
                    else:
                        # print(f"  ⚠️ Skipping Hit {i+1} (ID: {doc_id}): Invalid or empty content.")
                        pass # Silently skip invalid content for cleaner context

                else:
                    warnings.warn(f"  ⚠️ Skipping Hit {i+1}: Unexpected result format or length.")
                    # print(f"      Raw Hit Data: {hit}") # Optional: for debugging

            if not context_block:
                 print("   No valid content retrieved to form a context block.")

        else:
            print("   No results returned from search.")

    except Exception as e:
        warnings.warn(f"\n❌ An unexpected error occurred during retrieval: {e}")
        # Ensure empty results are returned on error
        context_block = ""
        retrieved_sources = {}
    finally:
        # Close the connection
        if session and session.is_active:
            session.close()
            # print("Database session closed.")
        elif engine:
             # print("Database connection closed (or session inactive).")
             pass

    print(f"--- Retrieval Finished. Context length: {len(context_block)} chars ---")
    return context_block, retrieved_sources

# --- Example Usage (for direct testing) ---
if __name__ == "__main__":
    print("Running RAG Retriever Test...")
    test_query = "ammonia serves purely to absorb the heat of reaction of the highly exothermic process"
    num_chunks_to_get = 3

    context, sources = retrieve_and_format_context(test_query, num_chunks_to_get)

    print("\n--- Generated Context Block (Test Output) ---")
    if context:
        print(context)
    else:
        print("   (No context generated)")

    print("\n--- Retrieved Source Documents (Test Output) ---")
    if sources:
        for source, md_path in sources.items():
            print(f"- {source}")
    else:
        print("   (No sources identified)")

    print("\n✅ RAG retriever script test finished.")
