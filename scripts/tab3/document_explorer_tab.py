#!/usr/bin/env python3
"""
Document Explorer Tab for BASF Document Assistant

Uses search_vdb for hybrid search on the vector_db table,
allowing filtering by file type and viewing selected PDFs in a modal dialog.
Displays results in a table, uses a select box for choosing a PDF,
and a button to trigger the modal.
"""

import streamlit as st
import pandas as pd
import os
import sys
import time
from pathlib import Path
import warnings
from urllib.parse import quote # For URL encoding

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
    # Display error prominently in Streamlit if import fails
    # Use a placeholder function to avoid crashing if import fails later
    SEARCH_AVAILABLE = False
    def search_vdb(query, num_results=3):
        st.error(f"Fatal Error: Failed to import search function (search_vdb). "
                 f"Check VDB_PIPELINE_PATH: '{VDB_PIPELINE_PATH}'. Error: {e}")
        return []
    print(f"Failed to import search_vdb: {e}") # Log error

# --- Helper Functions ---

def get_file_server_port():
    """Get the file server port from the saved file or use default"""
    port_file = os.path.expanduser("~/file_server_port.txt")
    default_port = 8070 # Use 8070 based on user confirmation
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                port = int(f.read().strip())
                return port
        except (ValueError, IOError) as e:
             warnings.warn(f"Could not read port file {port_file}: {e}. Using default {default_port}.")
             pass
    return default_port

def map_extension_to_type(extension):
    """Maps a file extension (lowercase, starting with '.') to a display type."""
    if extension in ['.pdf']: return "PDF"
    elif extension in ['.doc', '.docx']: return "DOC/DOCX"
    elif extension in ['.xls', '.xlsx', '.csv']: return "XLS/XLSX"
    elif extension in ['.ppt', '.pptx']: return "PPT/PPTX"
    elif extension in ['.txt', '.md']: return "TXT"
    elif extension in ['.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff']: return "Image"
    else: return "Other"

# --- Modal Dialog Function ---
@st.dialog("Document Viewer")
def show_pdf_modal(pdf_title, pdf_url):
    """This function defines the content of the modal dialog."""
    st.subheader(f"Viewing: {pdf_title}")
    if pdf_url:
        st.markdown(f'<iframe src="{pdf_url}" width="100%" height="650px" style="border:none;" title="PDF Viewer"></iframe>', unsafe_allow_html=True)
        st.link_button("Open Document", pdf_url, help="Opens the PDF source URL in a new browser tab.")
    else:
        st.error("Could not construct URL for the PDF.")


# --- Main Tab Rendering Function ---

def render_document_explorer_tab():
    """
    Renders the Document Explorer tab using search_vdb with modal PDF viewer triggered by selectbox + button
    """
    if not SEARCH_AVAILABLE: return

    file_server_port = get_file_server_port()

    st.header("Document Explorer")
    st.write("Find documents using hybrid search. Select a PDF from the results below and click 'View Selected PDF' to open it.")



    # --- Initialize session state ---
    if 'explorer_vdb_results_df' not in st.session_state:
        st.session_state.explorer_vdb_results_df = pd.DataFrame()
    # Store the *data* (title, url) of the PDF selected in the selectbox
    if 'selected_pdf_data_for_modal' not in st.session_state:
         st.session_state.selected_pdf_data_for_modal = None

    # --- Search Interface ---
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search documents:", key="explorer_search_query_vdb_select_btn",
                                     placeholder="Enter keywords or concepts...")
    with col2:
        num_results = st.number_input("Max results", min_value=5, max_value=100, value=20, step=5,
                                      key="explorer_num_results_vdb_select_btn")

    # --- Filters ---
    with st.expander("Filters", expanded=False):
        file_types = ["PDF", "DOC/DOCX", "Image", "Other"]
        selected_types = st.multiselect("Filter by File Type", file_types, key="explorer_file_types_vdb_select_btn")

    # --- Search Execution ---
    if st.button("Search Documents", key="explorer_search_button_vdb_select_btn"):
        st.session_state.explorer_vdb_results_df = pd.DataFrame() # Clear previous results
        st.session_state.selected_pdf_data_for_modal = None # Reset selection

        if search_query:
            with st.spinner("Searching documents..."):
                start_time = time.time()
                try:
                    search_results_raw = search_vdb(search_query, num_results=num_results)
                    elapsed = time.time() - start_time

                    if search_results_raw:
                        st.success(f"Found {len(search_results_raw)} potential matches in {elapsed:.2f} seconds. Processing and filtering...")
                        processed_data = []
                        results_indices = ["id", "semantic_score", "bm25_score", "fused_score",
                                           "filepath", "markdown_path", "content"]

                        for hit in search_results_raw:
                            if not isinstance(hit, (list, tuple)) or len(hit) != len(results_indices): continue
                            doc_id, _, _, fused_score, original_filepath, _, content_preview_full = hit

                            if original_filepath and isinstance(original_filepath, str):
                                filename = os.path.basename(original_filepath)
                                file_ext = os.path.splitext(filename)[1].lower()
                                doc_type = map_extension_to_type(file_ext)
                            else: filename, doc_type = "Unknown", "Other"

                            if selected_types and doc_type not in selected_types: continue

                            view_url = None
                            if original_filepath and file_server_port:
                                relative_path = original_filepath.lstrip('/')
                                relative_path_encoded = quote(relative_path) # URL encode
                                view_url = f"http://localhost:{file_server_port}/{relative_path_encoded}"

                            content_preview = content_preview_full[:150] + '...' if isinstance(content_preview_full, str) else 'N/A'

                            processed_data.append({
                                'ID': doc_id, 'Title': filename, 'Type': doc_type,
                                'Relevance': fused_score, 'Content Preview': content_preview,
                                'View URL': view_url, '_is_pdf': (doc_type == "PDF" and view_url is not None)
                            })

                        if processed_data:
                            st.session_state.explorer_vdb_results_df = pd.DataFrame(processed_data)
                        else:
                             st.warning("No documents match your filters.")

                    else:
                        st.warning("No matching documents found.")
                except Exception as e:
                    st.error(f"Error during search: {str(e)}")
                    st.exception(e)
        else:
            st.warning("Please enter a search query.")

    # --- Display Filtered Results Table and PDF Selector ---
    if not st.session_state.explorer_vdb_results_df.empty:
        st.divider()
        st.subheader("Search Results")
        df_display = st.session_state.explorer_vdb_results_df

        # --- PDF Selection Row ---
        col_select, col_button = st.columns([3, 1]) # Adjust ratio as needed

        with col_select:
            # Create dictionary of PDF options {Display Text: {'title': Title, 'url': URL}}
            pdf_options_dict = {
                f"{row['Title']} (ID: {row['ID']})": {'title': row['Title'], 'url': row['View URL']}
                for index, row in df_display[df_display['_is_pdf']].iterrows()
            }
            pdf_option_keys = ["--- Select a PDF to view ---"] + list(pdf_options_dict.keys())

            # Use selectbox for PDF selection
            selected_display_key = st.selectbox(
                "Select PDF:", # Shorter label
                options=pdf_option_keys,
                index=0, # Default to placeholder
                key="pdf_modal_selector_btn",
                label_visibility="collapsed" # Hide label, use placeholder
            )
            # Store the selected data (title, url) in session state immediately
            if selected_display_key != "--- Select a PDF to view ---":
                 st.session_state.selected_pdf_data_for_modal = pdf_options_dict.get(selected_display_key)
            else:
                 st.session_state.selected_pdf_data_for_modal = None

        with col_button:
            # Button to trigger the modal, enabled only if a PDF is selected
            view_button_disabled = st.session_state.selected_pdf_data_for_modal is None
            if st.button("View Document", key="view_pdf_button", disabled=view_button_disabled):
                # Retrieve data from session state and show modal
                selected_data = st.session_state.selected_pdf_data_for_modal
                if selected_data:
                     show_pdf_modal(selected_data['title'], selected_data['url'])
                     # Optional: Reset selection after viewing?
                     # st.session_state.selected_pdf_data_for_modal = None
                     # st.rerun() # Might cause immediate close if not careful

        # --- Display Dataframe ---
        st.dataframe(
            df_display[['ID', 'Title', 'Type', 'Relevance', 'Content Preview']], # Columns to show
            column_config={
                "ID": st.column_config.TextColumn("ID"),
                "Title": st.column_config.TextColumn("Document Title"),
                "Type": st.column_config.TextColumn("Type"),
                "Relevance": st.column_config.ProgressColumn(
                    "Relevance", min_value=0,
                    max_value=max(1.0, df_display['Relevance'].max() * 1.1) if not df_display.empty else 1.0,
                    format="%.4f"
                ),
                "Content Preview": st.column_config.TextColumn("Preview", width="large"),
            },
            use_container_width=True,
            hide_index=True,
            key="results_dataframe_select_btn"
        )

        # --- Export Button ---
        st.divider()
        csv = df_display.drop(columns=['_is_pdf']).to_csv(index=False).encode('utf-8')
        st.download_button(
            "Export Results to CSV", csv,
            f"vdb_search_{search_query[:20] if search_query else 'results'}.csv",
            "text/csv", key="download_vdb_csv_select_btn"
        )

    # Add helpful information in an expander
    # with st.expander("Tips", expanded=False):
    #     st.markdown(f"""
    #     - Use the **select box** above the results table to choose a PDF, then click the **View Selected PDF** button.
    #     - The selected PDF will open in a modal window.
    #     - Document links assume the file server is running on port **{file_server_port}** and accessible from your browser at `http://localhost:{file_server_port}/<path>`.
    #     - Search uses a combination of keyword and semantic matching via the `search_vdb` function.
    #     """)

# Example of how this might be called in your main Streamlit app
# if __name__ == "__main__":
#     st.set_page_config(page_title="Document Explorer VDB", layout="wide")
#     render_document_explorer_tab()
