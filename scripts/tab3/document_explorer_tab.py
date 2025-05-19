#!/usr/bin/env python3
"""
Document Explorer Tab for BASF Document Assistant

Uses search_vdb for hybrid search on the vector_db table,
allowing filtering by file type and viewing selected PDFs in a modal dialog
with adjustable size. Displays results in a table, uses a select box for
choosing a PDF, and a button to trigger the modal.
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




@st.dialog("Document Viewer")
def show_pdf_modal(pdf_title, pdf_url,
                   modal_width="20%",  # Adjust to desired overall modal width
                   modal_max_height="90vh"
                   ):
    """
    Displays a PDF within a modal dialog. Aims to eliminate the modal's
    own scrollbar and suggests an initial view mode for the PDF viewer.
    """
    # --- Add this line back to display the title ---
    st.subheader(f"Viewing: {pdf_title}")
    # ----------------------------------------------

    # --- CSS Injection ---
    # Keep the value that correctly sizes the iframe container itself
    # Note: You might need to re-adjust this if the subheader changes the required space
    non_iframe_space_estimate = "200px"

    modal_css = f"""
    <style>
        /* Make modal wider */
        div[role="dialog"] {{
            width: {modal_width} !important;
            max-width: {modal_width} !important;
            height: auto !important; /* Let content determine height up to max */
            max-height: {modal_max_height} !important;
            overflow-y: hidden !important; /* Keep modal scrollbar hidden */
            overflow-x: hidden !important;
        }}

        /* Keep iframe at 65% width but center it */
        div[role="dialog"] iframe {{
             height: calc({modal_max_height} - {non_iframe_space_estimate}) !important;
             width: 65% !important; /* Keep this width */
             border: none !important;
             display: block !important; /* Needed for margin auto */
             margin-left: auto !important; /* Add centering */
             margin-right: auto !important; /* Add centering */
        }}

        /* Optional: Header styling - Ensure this doesn't conflict */
         div[role="dialog"] h3 {{ /* This targets the st.subheader */
             margin-top: 5px !important;
             margin-bottom: 10px !important;
             flex-shrink: 0;
             /* Add text-align: center; if you want the title centered */
             /* text-align: center; */
         }}
    </style>
    """
    st.markdown(modal_css, unsafe_allow_html=True)
    # --- End CSS Injection ---

    # --- Display Iframe ---
    if pdf_url:
        pdf_url_with_view = f"{pdf_url}#view=Fit"
        st.markdown(
            # Use the modified URL with the hash parameter
            f'<iframe src="{pdf_url_with_view}" title="PDF Viewer"></iframe>',
            unsafe_allow_html=True
        )
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

    # --- Initialize session state ---
    if 'explorer_vdb_results_df' not in st.session_state:
        st.session_state.explorer_vdb_results_df = pd.DataFrame()
    if 'selected_pdf_data_for_modal' not in st.session_state:
         st.session_state.selected_pdf_data_for_modal = None

    # --- Search Interface ---
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search documents:", key="explorer_search_query_vdb_select_btn",
                                     placeholder="Enter keywords or concepts...")
    with col2:
        num_results = st.number_input("Max results", min_value=5, max_value=100, value=5, step=5,
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
                    # Assuming search_vdb returns a list of tuples/lists with filepath at index 4
                    search_results_raw = search_vdb(search_query, num_results=num_results)
                    elapsed = time.time() - start_time

                    if search_results_raw:
                        st.success(f"Found {len(search_results_raw)} potential matches in {elapsed:.2f} seconds. Processing and filtering...")
                        processed_data = []
                        # Make sure this matches the actual structure returned by search_vdb
                        results_indices = ["id", "semantic_score", "bm25_score", "fused_score",
                                           "filepath", "markdown_path", "content"]

                        for hit in search_results_raw:
                             # Basic validation of the hit structure
                            if not isinstance(hit, (list, tuple)) or len(hit) < 5: # Check at least up to filepath index
                                warnings.warn(f"Skipping malformed search result: {hit}")
                                continue

                            # Safely unpack, assuming order based on results_indices
                            doc_id = hit[0]
                            fused_score = hit[3]
                            original_filepath = hit[4]
                            content_preview_full = hit[6] if len(hit) > 6 else 'N/A' # Handle potential shorter results

                            if original_filepath and isinstance(original_filepath, str):
                                filename = os.path.basename(original_filepath)
                                file_ext = os.path.splitext(filename)[1].lower()
                                doc_type = map_extension_to_type(file_ext)
                            else:
                                filename, doc_type = "Unknown", "Other"
                                original_filepath = None # Ensure it's None if not valid

                            # Apply type filter
                            if selected_types and doc_type not in selected_types: continue

                            # Construct view URL
                            view_url = None
                            if original_filepath and file_server_port:
                                try:
                                    # Ensure path is relative for URL construction
                                    relative_path = original_filepath.lstrip('/')
                                    relative_path_encoded = quote(relative_path) # URL encode
                                    view_url = f"http://localhost:{file_server_port}/{relative_path_encoded}"
                                except Exception as url_e:
                                     warnings.warn(f"Could not create URL for {original_filepath}: {url_e}")


                            content_preview = content_preview_full[:150] + '...' if isinstance(content_preview_full, str) else 'N/A'

                            processed_data.append({
                                'ID': doc_id, 'Title': filename, 'Type': doc_type,
                                'Relevance': fused_score, 'Content Preview': content_preview,
                                'View URL': view_url,
                                '_is_pdf': (doc_type == "PDF" and view_url is not None),
                                # '_original_filepath': original_filepath # Keep if needed for orientation check
                            })

                        if processed_data:
                            st.session_state.explorer_vdb_results_df = pd.DataFrame(processed_data)
                        else:
                             st.warning("No documents match your search criteria and filters.")

                    else:
                        st.warning("No matching documents found.")
                except Exception as e:
                    st.error(f"Error during search or processing: {str(e)}")
                    st.exception(e) # Show full traceback in console/logs
        else:
            st.warning("Please enter a search query.")

    # --- Display Filtered Results Table and PDF Selector ---
    if not st.session_state.explorer_vdb_results_df.empty:
        st.divider()
        st.subheader("Search Results")
        df_display = st.session_state.explorer_vdb_results_df

        # --- PDF Selection Row ---
        col_select, col_button = st.columns([3, 1])

        with col_select:
            # Create dictionary of PDF options {Display Text: {'title': Title, 'url': URL}}
            # Filter for rows where _is_pdf is True
            pdf_options_dict = {
                f"{row['Title']} (ID: {row['ID']})": {'title': row['Title'], 'url': row['View URL']}
                for index, row in df_display[df_display['_is_pdf']].iterrows() # Ensure filtering
            }
            pdf_option_keys = ["--- Select a PDF to view ---"] + list(pdf_options_dict.keys())

            selected_display_key = st.selectbox(
                "Select PDF:",
                options=pdf_option_keys,
                index=0,
                key="pdf_modal_selector_btn",
                label_visibility="collapsed"
            )

            if selected_display_key != "--- Select a PDF to view ---":
                 st.session_state.selected_pdf_data_for_modal = pdf_options_dict.get(selected_display_key)
            else:
                 st.session_state.selected_pdf_data_for_modal = None

        with col_button:
            view_button_disabled = st.session_state.selected_pdf_data_for_modal is None
            if st.button("View Document", key="view_pdf_button", disabled=view_button_disabled):
                selected_data = st.session_state.selected_pdf_data_for_modal
                if selected_data and selected_data.get('url'): # Check for URL
                     # --- Call the modal with desired size parameters ---
                     show_pdf_modal(
                         pdf_title=selected_data['title'],
                         pdf_url=selected_data['url'],
                         # --- Adjust these values as needed ---
                         modal_width="90%",        # Example: Make it wider
                         modal_max_height="85vh"   # Example: Adjust max height
                     )
                     # --- End modal call ---
                elif selected_data: # Handle case where selection exists but URL doesn't
                    st.error("Selected PDF item is missing a valid view URL.")
                # No 'else' needed as button is disabled if no selection

        # --- Display Dataframe ---
        st.dataframe(
            df_display[['ID', 'Title', 'Type', 'Relevance', 'Content Preview']],
            column_config={
                "ID": st.column_config.TextColumn("ID"),
                "Title": st.column_config.TextColumn("Document Title"),
                "Type": st.column_config.TextColumn("Type"),
                "Relevance": st.column_config.ProgressColumn(
                    "Relevance", min_value=0,
                    max_value=(df_display['Relevance'].max() * 1.1 if not df_display.empty and pd.notna(df_display['Relevance'].max()) and df_display['Relevance'].max() > 0 else 1.0),
                    format="%.4f"
                ),
                "Content Preview": st.column_config.TextColumn("Preview", width="large"),
            },
            use_container_width=True,
            hide_index=True,
            key="results_dataframe_select_btn"
        )



