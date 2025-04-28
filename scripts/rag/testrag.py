#!/usr/bin/env python3
"""
basic_vdb_search.py

Connects to the database, performs a hybrid search using search_vdb,
parses the results based on the expected list structure, and prints
the retrieved information clearly.
"""

import sys
import time
import json
import warnings
from decimal import Decimal # Import if needed for score types, though conversion happens later

# --- Configuration ---
# Adjust this path to point to your VDB pipeline location
VDB_PIPELINE_PATH = "/shared_folders/team_1/mark_vdb/vdb_pipeline" #<-- ADJUST IF NEEDED
# Define the search query you want to test
# TEST_SEARCH_QUERY = "I need help disassembling a dryer model 1600"
TEST_SEARCH_QUERY = "ammonia serves purely to absorb the heat of reaction of the highly exothermic process"
# Define how many results you want
NUM_RESULTS = 5
# Define the expected indices for the returned list/tuple from search_vdb
# Based on test.py output: [id, semantic_score, bm25_score, fused_score, filepath, markdown_path, content]
IDX_ID = 0
IDX_SEMANTIC_SCORE = 1
IDX_BM25_SCORE = 2
IDX_FUSED_SCORE = 3
IDX_FILEPATH = 4
IDX_MARKDOWN_PATH = 5
IDX_CONTENT = 6
EXPECTED_RESULT_LENGTH = 7 # Number of items expected in each result list/tuple

# --- Add VDB pipeline to Python path ---
if VDB_PIPELINE_PATH not in sys.path:
    sys.path.append(VDB_PIPELINE_PATH)

# --- Import VDB pipeline functions ---
try:
    # Only need init_vector_db and search_vdb for this script
    from init_vector_db import init_vector_db
    from search_vdb import search_vdb
    INIT_DB_AVAILABLE = True
    SEARCH_AVAILABLE = True
    print("✅ VDB pipeline functions imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import one or more VDB functions: {e}")
    if 'init_vector_db' not in locals(): INIT_DB_AVAILABLE = False
    if 'search_vdb' not in locals(): SEARCH_AVAILABLE = False
    # Define placeholders
    def init_vector_db(wipe_database=False): return None, None
    def search_vdb(query, num_results=3): return []

# --- Main Execution ---
def main():
    """Main function to execute the search and print results."""
    session = None
    engine = None

    print("\n--- Basic VDB Search Test ---")

    # Check if required functions are available
    if not INIT_DB_AVAILABLE or not SEARCH_AVAILABLE:
        print("❌ Cannot proceed: Required VDB functions failed to import.")
        return

    try:
        # 1. Connect to the database
        print("Connecting to database...")
        connect_start_time = time.time()
        session, engine = init_vector_db(wipe_database=False)

        if not engine:
            print("   ❌ Failed to establish database connection via init_vector_db.")
            return # Exit if connection failed

        print(f"   Connected in {time.time() - connect_start_time:.2f}s")

        # 2. Perform the search
        print(f"\nPerforming search for: '{TEST_SEARCH_QUERY}' (Top {NUM_RESULTS} results)")
        search_start_time = time.time()
        search_results = [] # Initialize
        try:
            search_results = search_vdb(TEST_SEARCH_QUERY, num_results=NUM_RESULTS)
            print(f"   Search completed in {time.time() - search_start_time:.2f}s")
            print(f"   Found {len(search_results)} results.")

        except Exception as search_error:
            print(f"   ❌ Error during search_vdb(): {search_error}")
            # Optionally re-raise if you want the script to stop on search error
            # raise search_error

        # 3. Parse and Display the results
        print("\n--- Parsed Search Results ---")
        if search_results:
            for i, hit in enumerate(search_results):
                print(f"\n--- Hit {i+1} ---")
                if isinstance(hit, (list, tuple)) and len(hit) == EXPECTED_RESULT_LENGTH:
                    # Extract data using defined indices
                    doc_id = hit[IDX_ID]
                    semantic_score = hit[IDX_SEMANTIC_SCORE]
                    bm25_score = hit[IDX_BM25_SCORE]
                    fused_score = hit[IDX_FUSED_SCORE]
                    filepath = hit[IDX_FILEPATH]
                    markdown_path = hit[IDX_MARKDOWN_PATH]
                    content = hit[IDX_CONTENT]

                    # Print extracted data clearly
                    print(f"  ID             : {doc_id}")
                    print(f"  Semantic Score : {semantic_score:.4f}")
                    print(f"  BM25 Score     : {bm25_score:.4f}")
                    print(f"  Fused Score    : {fused_score:.4f}")
                    print(f"  File Path      : {filepath}")
                    print(f"  Markdown Path  : {markdown_path}")
                    print(f"  Content Preview: {content if isinstance(content, str) else 'N/A'}")

                else:
                    print(f"  ⚠️ Unexpected result format or length: {type(hit)}, Length: {len(hit) if hasattr(hit, '__len__') else 'N/A'}")
                    print(f"  Raw Hit Data: {hit}") # Print raw data for debugging
        else:
            print("   No results returned or search failed.")

    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
    finally:
        # 4. Close the connection
        if session and session.is_active:
            session.close()
            print("\nDatabase session closed.")
        elif engine:
             print("\nDatabase connection closed (or session inactive).")

    print(f"\n✅ Search script finished.")


if __name__ == "__main__":
    main()
