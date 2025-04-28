#!/usr/bin/env python3
"""
Document Explorer Tab for BASF Document Assistant

Uses search_vdb for hybrid search on the vector_db table,
allowing filtering by file type.
"""

import streamlit as st
import pandas as pd
import os
import sys
import time
from pathlib import Path
import warnings

# Add necessary paths for imports
MODULE_DIR = Path(__file__).parent
# Adjust paths as necessary for your project structure
# sys.path.append(str(MODULE_DIR.parent)) # Assuming rag module is one level up
VDB_PIPELINE_PATH = '/shared_folders/team_1/mark_vdb/vdb_pipeline'
if VDB_PIPELINE_PATH not in sys.path:
    sys.path.append(VDB_PIPELINE_PATH)
    print(f"Appended to sys.path: {VDB_PIPELINE_PATH}") # For debugging

# Import required modules from VDB pipeline
try:
    # We primarily need search_vdb for this tab
    from search_vdb import search_vdb
    SEARCH_AVAILABLE = True
    print("Successfully imported search_vdb.") # For debugging
except ImportError as e:
    st.error(f"Fatal Error: Failed to import search function (search_vdb). "
             f"Check VDB_PIPELINE_PATH: '{VDB_PIPELINE_PATH}'. Error: {e}")
    SEARCH_AVAILABLE = False
    # Define a placeholder to avoid crashing
    def search_vdb(query, num_results=3): return []

# --- Helper Functions ---

def get_file_server_port():
    """Get the file server port from the saved file or use default"""
    port_file = os.path.expanduser("~/file_server_port.txt")
    default_port = 8069 # Default port
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                port = int(f.read().strip())
                print(f"Read file server port: {port}") # Debugging
                return port
        except (ValueError, IOError) as e:
             warnings.warn(f"Could not read port file {port_file}: {e}. Using default {default_port}.")
             pass # Fall through to default
    else:
        print(f"Port file {port_file} not found. Using default {default_port}.") # Debugging

    return default_port

def map_extension_to_type(extension):
    """Maps a file extension (lowercase, starting with '.') to a display type."""
    if extension in ['.pdf']:
        return "PDF"
    elif extension in ['.doc', '.docx']:
        return "DOC/DOCX"
    elif extension in ['.xls', '.xlsx', '.csv']:
        return "XLS/XLSX"
    elif extension in ['.ppt', '.pptx']:
        return "PPT/PPTX"
    elif extension in ['.txt', '.md']:
        return "TXT"
    elif extension in ['.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff']:
        return "Image" # Consolidate image types
    else:
        return "Other"

# --- Main Tab Rendering Function ---

def render_document_explorer_tab():
    """
    Renders the Document Explorer tab using search_vdb
    """
    # Check dependencies
    if not SEARCH_AVAILABLE:
        # Error already shown during import
        return

    # Get the current file server port
    file_server_port = get_file_server_port()

    st.header("Document Explorer")
    st.write("Find documents using hybrid search (semantic + keyword).")

    # Display file server status
    st.info(f"📂 Document server active on port: {file_server_port}")

    # --- Search Interface ---
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search documents:",
            key="explorer_search_query_vdb", # Use unique key
            placeholder="Enter keywords or concepts to search for..."
        )
    with col2:
        num_results = st.number_input("Max results", min_value=5, max_value=100, value=20, step=5, key="explorer_num_results_vdb") # Allow more results

    # --- Filters ---
    with st.expander("Filters", expanded=False):
        # File type filter - updated based on analysis
        # Grouped image types for simplicity
        file_types = ["PDF", "DOC/DOCX", "Image", "Other"]
        selected_types = st.multiselect("Filter by File Type", file_types, key="explorer_file_types_vdb")

        # Category filter - Commented out as category isn't directly returned by search_vdb output structure shown
        # categories = ["Process Documentation", "Safety Protocols", "Research Reports",
        #              "Engineering Specs", "Operation Manuals", "Technical Drawings"]
        # selected_categories = st.multiselect("Document Category", categories, key="explorer_categories_vdb")

    # --- Search Execution ---
    if st.button("Search Documents", key="explorer_search_button_vdb"):
        if search_query:
            with st.spinner("Searching documents using VDB pipeline..."):
                start_time = time.time()
                try:
                    # Call search_vdb from the imported pipeline
                    # Assuming it handles its own DB connection
                    search_results = search_vdb(search_query, num_results=num_results)
                    elapsed = time.time() - start_time

                    if search_results:
                        st.success(f"Found {len(search_results)} potential matches in {elapsed:.2f} seconds. Applying filters...")

                        # --- Process and Filter Results ---
                        data = []
                        results_indices = ["id", "semantic_score", "bm25_score", "fused_score",
                                           "filepath", "markdown_path", "content"] # Based on test.py output structure

                        for hit in search_results:
                            # Basic check for expected structure (list/tuple of length 7)
                            if not isinstance(hit, (list, tuple)) or len(hit) != len(results_indices):
                                warnings.warn(f"Skipping malformed search result: {hit}")
                                continue

                            # Extract data based on known positions
                            doc_id = hit[0]
                            fused_score = hit[3]
                            original_filepath = hit[4] # Use this for extension and link
                            content_preview_full = hit[6]

                            # --- Apply File Type Filter ---
                            if original_filepath and isinstance(original_filepath, str):
                                filename = os.path.basename(original_filepath)
                                file_ext = os.path.splitext(filename)[1].lower()
                                doc_type = map_extension_to_type(file_ext)
                            else:
                                filename = "Unknown"
                                doc_type = "Other"

                            if selected_types and doc_type not in selected_types:
                                continue # Skip if file type doesn't match filter

                            # --- Apply Category Filter (Commented Out) ---
                            # category = "Unknown" # Placeholder - category not in results list
                            # if selected_categories and category not in selected_categories:
                            #     continue

                            # --- Prepare URL for viewing ---
                            # Assumes file server maps shared folder structure
                            doc_path_for_url = original_filepath
                            # Adjust path if needed based on file server root
                            # Example: Remove a base part if server root is different
                            # if doc_path_for_url.startswith('/shared_folders/team_1/document_batch/'):
                            #     doc_path_for_url = doc_path_for_url.replace('/shared_folders/team_1/document_batch/', '', 1)

                            # Remove leading slash for URL construction
                            if doc_path_for_url.startswith('/'):
                                doc_path_for_url = doc_path_for_url[1:]
                            view_url = f"http://localhost:{file_server_port}/{doc_path_for_url}"

                            # Content preview (truncated)
                            content_preview = content_preview_full[:150] + '...' if isinstance(content_preview_full, str) else 'N/A'

                            # Prepare row for dataframe
                            data.append({
                                'ID': doc_id,
                                'Title': filename,
                                'Type': doc_type,
                                # 'Category': category, # Add back if category data becomes available
                                'Relevance': fused_score, # Use the fused score
                                'Content Preview': content_preview,
                                'View URL': view_url
                            })

                        # --- Display Filtered Results ---
                        if data:
                            df = pd.DataFrame(data)
                            st.info(f"Displaying {len(df)} documents after filtering.")

                            # Display as a sortable table
                            st.dataframe(
                                df,
                                column_config={
                                    "ID": st.column_config.TextColumn("ID"),
                                    "Title": st.column_config.TextColumn("Document Title"),
                                    "Type": st.column_config.TextColumn("Type"),
                                    # "Category": st.column_config.TextColumn("Category"),
                                    "Relevance": st.column_config.ProgressColumn(
                                        "Relevance Score",
                                        # Adjust min/max based on expected score range from search_vdb
                                        min_value=0,
                                        max_value=max(1.0, df['Relevance'].max() * 1.1) if not df.empty else 1.0, # Dynamic max
                                        format="%.4f" # Show more precision for fused score
                                    ),
                                    "Content Preview": st.column_config.TextColumn("Preview"),
                                    "View URL": st.column_config.LinkColumn("View Document", display_text="Open")
                                },
                                use_container_width=True,
                                hide_index=True
                            )

                            # Add export option
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                "Export Results to CSV",
                                csv,
                                f"vdb_search_{search_query[:20]}.csv", # Dynamic filename
                                "text/csv",
                                key="download_vdb_csv"
                            )

                        else:
                            st.warning("No documents match your filters. Try adjusting your search criteria.")
                    else:
                        st.warning("No matching documents found in the initial search. Try different search terms.")

                except Exception as e:
                    st.error(f"Error during search or processing: {str(e)}")
                    st.exception(e) # Show traceback for debugging
        else:
            st.warning("Please enter a search query.")

    # Add helpful information in an expander
    with st.expander("Tips for effective document search", expanded=False):
        st.markdown(f"""
        ### Search Tips

        - Use specific technical terms or concepts.
        - Try variations of terms if you don't get expected results.
        - Use the Filters to narrow down by document type.
        - Search uses a combination of keyword and semantic matching.

        ### Document Access

        Documents are served from the file server running on port {file_server_port}.
        Click the 'Open' link to view the document directly. Ensure the file server is running
        and accessible from your browser. The links assume the file paths returned by the search
        are correctly mapped by the server.
        """)

# Example of how this might be called in your main Streamlit app
# if __name__ == "__main__":
#     # For testing the tab individually
#     st.set_page_config(page_title="Document Explorer VDB", layout="wide")
#     render_document_explorer_tab()
