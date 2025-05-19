#!/usr/bin/env python3
"""
db_stats_provider.py

Provides a function to connect to the database, retrieve unique document paths
from the specified column (`markdown` by default) of the `vector_db` table,
extract file extensions, and return the counts as a Counter object.
"""

import sys
import time
import warnings
import os
from collections import Counter
from sqlalchemy import text, inspect as sql_inspect
from pathlib import Path # Use pathlib for path manipulation

# --- Configuration ---
# Database Configuration
DB_TABLE_NAME = "vector_db" # The table containing chunks
DB_UNIQUE_DOC_COLUMN = "markdown" # Column representing the original document path

# --- VDB Pipeline Path Setup ---
# Assumes this script might be in a subdirectory like 'tab1' within 'scripts'
# Go up two levels to get to the assumed project root containing the shared folder path
try:
    SCRIPT_DIR_STATS = Path(__file__).resolve().parent
    SCRIPTS_ROOT_STATS = SCRIPT_DIR_STATS.parent
    # Adjust this path relative to SCRIPTS_ROOT_STATS if needed
    VDB_PIPELINE_PATH = '/shared_folders/team_1/mark_vdb/vdb_pipeline' # Keep absolute
    if VDB_PIPELINE_PATH not in sys.path:
        sys.path.append(VDB_PIPELINE_PATH)
        # print(f"Appended VDB pipeline path (from db_stats_provider): {VDB_PIPELINE_PATH}") # Debugging
except NameError:
     # __file__ might not be defined if run interactively, handle gracefully
     print("Warning: Could not automatically determine VDB pipeline path.")
     VDB_PIPELINE_PATH = '/shared_folders/team_1/mark_vdb/vdb_pipeline' # Fallback
     if VDB_PIPELINE_PATH not in sys.path:
        sys.path.append(VDB_PIPELINE_PATH)


# --- Import Database Initializer ---
# Use a flag to track import success for graceful error handling
INIT_DB_AVAILABLE = False
try:
    from init_vector_db import init_vector_db
    INIT_DB_AVAILABLE = True
    # print("✅ init_vector_db imported successfully (in db_stats_provider).") # Optional: uncomment for debugging
except ImportError as e:
    warnings.warn(f"⚠️ (db_stats_provider) Failed to import init_vector_db. Check VDB_PIPELINE_PATH: {e}")
    # Define a placeholder if needed elsewhere, though the main function checks the flag
    def init_vector_db(wipe_database=False): return None, None

# --- Helper Function ---
def get_extension(filepath):
    """Extracts the lowercase file extension from a path."""
    if not filepath or not isinstance(filepath, str):
        return None
    _, ext = os.path.splitext(filepath)
    # Return lowercase extension (e.g., '.pdf') or None if no extension
    return ext.lower() if ext else None

# --- Core Logic Function (Exported) ---
def get_extension_counts_from_db():
    """Connects to DB, fetches unique paths, and returns extension counts as a Counter."""
    if not INIT_DB_AVAILABLE:
        print("❌ (db_stats_provider) Cannot get counts: init_vector_db failed to import.")
        return None # Return None to indicate failure

    session = None
    engine = None
    extension_counts = Counter()
    print("(db_stats_provider) Attempting to get extension counts from database...")

    try:
        # 1. Connect
        print("   (db_stats_provider) Connecting to database...")
        connect_start_time = time.time()
        session, engine = init_vector_db(wipe_database=False) # Ensure wipe_database=False

        if not engine:
            print("      ❌ (db_stats_provider) Failed to establish database connection.")
            return None
        print(f"      (db_stats_provider) Connected in {time.time() - connect_start_time:.2f}s")
        inspector = sql_inspect(engine)

        # 2. Check Table and Column
        if not inspector.has_table(DB_TABLE_NAME, schema="public"):
             print(f"      ❌ (db_stats_provider) Table 'public.{DB_TABLE_NAME}' does not exist.")
             return None
        columns_info = inspector.get_columns(DB_TABLE_NAME, schema="public")
        existing_columns = [col['name'] for col in columns_info] if columns_info else []
        if DB_UNIQUE_DOC_COLUMN not in existing_columns:
             print(f"      ❌ (db_stats_provider) Column '{DB_UNIQUE_DOC_COLUMN}' not found in table '{DB_TABLE_NAME}'.")
             return None

        # 3. Fetch Unique Document Paths
        fetch_start_time = time.time()
        unique_paths = []
        try:
            query = text(f"""
                SELECT DISTINCT "{DB_UNIQUE_DOC_COLUMN}"
                FROM public."{DB_TABLE_NAME}"
                WHERE "{DB_UNIQUE_DOC_COLUMN}" IS NOT NULL;
            """)
            result = session.execute(query)
            unique_paths = [row[0] for row in result.fetchall()]
            print(f"      (db_stats_provider) Query completed in {time.time() - fetch_start_time:.2f}s")
            print(f"      (db_stats_provider) Retrieved {len(unique_paths)} unique paths.")

        except Exception as query_error:
            print(f"      ❌ (db_stats_provider) Error executing fetch query: {query_error}")
            return None # Stop if we can't get the paths

        # 4. Calculate Extension Counts
        calc_start_time = time.time()
        no_extension_count = 0
        invalid_path_count = 0

        for path in unique_paths:
            ext = get_extension(path)
            if ext:
                extension_counts[ext] += 1
            elif path is None or not isinstance(path, str):
                 invalid_path_count += 1
            else:
                no_extension_count +=1

        print(f"      (db_stats_provider) Calculation finished in {time.time() - calc_start_time:.2f}s")
        if no_extension_count > 0:
            print(f"      (db_stats_provider) (Ignored {no_extension_count} paths with no extension)")
        if invalid_path_count > 0:
             print(f"      (db_stats_provider) (Ignored {invalid_path_count} invalid/NULL paths)")

        return extension_counts # Return the Counter object

    except Exception as e:
        print(f"   ❌ (db_stats_provider) An unexpected error occurred during data retrieval: {e}")
        import traceback
        traceback.print_exc()
        return None # Return None on error
    finally:
        # 5. Close connection
        if session and session.is_active:
             try:
                 session.close()
                 # print("   (db_stats_provider) Database session closed.") # Optional debug
             except Exception as close_err:
                 print(f"   (db_stats_provider) Error closing session: {close_err}")
        elif engine:
             # print("   (db_stats_provider) Database connection closed (or session inactive).") # Optional debug
             pass # Engine might be closed automatically depending on setup

# --- Main Execution (for Standalone Testing) ---
if __name__ == "__main__":
    print(f"\n--- Running Standalone: Getting File Extension Counts ---")
    # 1. Get data
    counts = get_extension_counts_from_db()

    # 2. Print counts if retrieved
    if counts is not None:
        if counts:
            print("\n--- File Extension Statistics ---")
            # Sort by count descending for better readability
            sorted_extensions = counts.most_common()
            print("Extension | Count")
            print("----------|-------")
            for ext, count in sorted_extensions:
                print(f"{ext:<9} | {count}")
            print("---------------------------------")
        else:
            print("\nNo files with extensions found in the database.")
    else:
        print("\nCould not retrieve extension counts from database.")

    print(f"\n✅ Standalone script finished.")
