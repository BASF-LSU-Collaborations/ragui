#!/usr/bin/env python3
"""
run_rag_query.py

Orchestrates the RAG process:
1. Retrieves relevant context using rag_retriever.
2. Generates a structured (JSON) response including chunk IDs and source paths
   using the appropriate rag_generator function.
3. Prints the final structured response.
"""

import sys
import time
import warnings
import json # To pretty-print the final dict

# --- Configuration ---
# Adjust this path to point to your RAG scripts location if needed
RAG_SCRIPT_PATH = "." # Assume scripts are in the current directory
if RAG_SCRIPT_PATH not in sys.path:
    sys.path.append(RAG_SCRIPT_PATH)

# Define the search query you want to test
USER_QUERY = "What does ammonia do in the CHA synthesis reaction?"
# Define how many chunks to retrieve for context
NUM_CONTEXT_CHUNKS = 3

# --- Import RAG components ---
try:
    # Import the retriever function
    from rag_retriever import retrieve_and_format_context
    RETRIEVER_AVAILABLE = True
    print("✅ rag_retriever imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import rag_retriever: {e}")
    RETRIEVER_AVAILABLE = False
    # Define placeholder
    def retrieve_and_format_context(query, num_chunks=3): return "Error: Retriever not available.", {}

try:
    # Import the *structured* generator function (the latest one)
    # Make sure you are importing from the correct version of rag_generator.py
    from rag_generator import generate_response_from_context
    GENERATOR_AVAILABLE = True
    print("✅ rag_generator (structured) imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import structured rag_generator: {e}")
    GENERATOR_AVAILABLE = False
     # Define placeholder returning the expected dict structure
    def generate_response_from_context(query, context_block):
         return {"answer": "Error: Generator not available.", "sources": []}


# --- Main Execution ---
def main():
    """Runs the end-to-end RAG query process."""
    print("\n--- Running End-to-End RAG Query (Structured Output with Chunk ID) ---")

    if not RETRIEVER_AVAILABLE or not GENERATOR_AVAILABLE:
        print("❌ Cannot proceed: Required RAG components failed to import.")
        return

    # 1. Retrieve Context
    print(f"\n[1/2] Retrieving context for query: '{USER_QUERY}'")
    retrieval_start_time = time.time()
    # Call the retriever function
    context_block, retrieved_sources_map = retrieve_and_format_context(
        USER_QUERY,
        num_chunks=NUM_CONTEXT_CHUNKS
    )
    print(f"   Retrieval finished in {time.time() - retrieval_start_time:.2f}s")

    # Initialize final_response_dict in case context retrieval fails
    final_response_dict = {"answer": "Failed to retrieve context from the database.", "sources": []}

    if not context_block and RETRIEVER_AVAILABLE: # Check if retriever ran but found nothing
        print("\n❌ No context was retrieved. Cannot generate response.")
        # Use the pre-initialized error dict
    elif not RETRIEVER_AVAILABLE:
        print("\n❌ Retriever not available. Cannot generate response.")
        # Use the pre-initialized error dict
    else:
        # 2. Generate Structured Response only if context was retrieved
        print(f"\n[2/2] Generating structured response using retrieved context...")
        generation_start_time = time.time()
        # Call the structured generator function
        final_response_dict = generate_response_from_context(
            USER_QUERY,
            context_block
        )
        print(f"   Generation finished in {time.time() - generation_start_time:.2f}s")

    # 3. Display Final Results
    print("\n" + "="*10 + " Final RAG Output " + "="*10)
    print(f"\nQuery: {USER_QUERY}")

    # Pretty print the entire JSON object returned by the generator
    print("\nGenerated JSON Response:")
    print(json.dumps(final_response_dict, indent=2))

    # Optional: You could add code here to further process or display
    # the 'answer' and 'sources' fields separately if desired.

    print("="*42)


if __name__ == "__main__":
    # Ensure necessary environment variables (like OPENAI_API_KEY) are set
    # The rag_generator script should handle loading .env now
    main()
    print("\n✅ RAG query script finished.")
