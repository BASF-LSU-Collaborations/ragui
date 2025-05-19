#!/usr/bin/env python3
"""
Streamlit Chat Page Code

Provides the conversational AI interface using modular RAG components.
Includes custom avatars and modal PDF viewer for cited sources.
Intended to be run as the main page (e.g., 1_Chat.py) in a multi-page app.
Fixes rendering order issue after user input and path calculation error.
"""

import streamlit as st
import os
import sys
import time
import warnings
from pathlib import Path
from urllib.parse import quote # For URL encoding
import pandas as pd # Keep pandas for potential future use or if helper functions need it

# --- Configuration ---
ASSISTANT_AVATAR_PATH = "/home/jonathan_morse/ragui/public/white_symbol.png" # Path to your custom assistant avatar
USER_AVATAR_PATH = "/home/jonathan_morse/ragui/public/user.png" # Path to your custom user avatar

# --- Robust Path Setup ---
# Get the directory of the current script (e.g., /home/jonathan_morse/ragui/scripts/tab1/)
SCRIPT_DIR = Path(__file__).resolve().parent
# Go up one level to the parent directory (e.g., /home/jonathan_morse/ragui/scripts/)
SCRIPTS_ROOT = SCRIPT_DIR.parent

# Path to the rag scripts directory (e.g., /home/jonathan_morse/ragui/scripts/rag)
# Now correctly looks for 'rag' folder within the SCRIPTS_ROOT
RAG_SCRIPT_PATH = SCRIPTS_ROOT / 'rag'
if str(RAG_SCRIPT_PATH) not in sys.path:
    sys.path.append(str(RAG_SCRIPT_PATH))
    print(f"Appended RAG script path: {RAG_SCRIPT_PATH}") # Debugging
# Also add the parent 'scripts' directory itself, in case modules need to import siblings
if str(SCRIPTS_ROOT) not in sys.path:
     sys.path.append(str(SCRIPTS_ROOT))
     print(f"Appended Scripts root path: {SCRIPTS_ROOT}") # Debugging


# Path to the VDB pipeline directory (Keep absolute as it's outside the project)
VDB_PIPELINE_PATH = '/shared_folders/team_1/mark_vdb/vdb_pipeline'
if VDB_PIPELINE_PATH not in sys.path:
    sys.path.append(VDB_PIPELINE_PATH)
    print(f"Appended VDB pipeline path: {VDB_PIPELINE_PATH}") # Debugging


# --- Import RAG components ---
# Import the new modular functions
try:
    # Now Python should be able to find the module in the corrected RAG_SCRIPT_PATH
    from rag_retriever import retrieve_and_format_context
    RETRIEVER_AVAILABLE = True
    print("✅ rag_retriever imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import rag_retriever: {e}")
    RETRIEVER_AVAILABLE = False
    # Define a placeholder function if import fails
    def retrieve_and_format_context(query, num_chunks=3):
        """Placeholder for retriever if import fails."""
        st.error(f"Error: rag_retriever module not found. Check path: {RAG_SCRIPT_PATH}")
        return "Error: Retriever not available.", {}

try:
    # Now Python should be able to find the module in the corrected RAG_SCRIPT_PATH
    from rag_generator import generate_response_from_context
    GENERATOR_AVAILABLE = True
    print("✅ rag_generator (structured) imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import structured rag_generator: {e}")
    GENERATOR_AVAILABLE = False
    # Define a placeholder function if import fails
    def generate_response_from_context(query, context_block):
        """Placeholder for generator if import fails."""
        st.error(f"Error: rag_generator module not found. Check path: {RAG_SCRIPT_PATH}")
        return {"answer": "Error: Generator not available.", "sources": []}

# --- Helper Functions ---

def get_file_server_port():
    """Get the file server port from disk or use default."""
    port_file = os.path.expanduser("~/file_server_port.txt")
    default_port = 8070 # Use confirmed port
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                port = int(f.read().strip())
                return port
        except Exception as e:
            warnings.warn(f"Could not read port file {port_file}: {e}. Using default {default_port}.")
            pass
    return default_port

# --- Modal Dialog Function ---
# Ensure you have Streamlit version 1.33+ for st.dialog
@st.dialog("Document Viewer")
def show_pdf_modal(pdf_title, pdf_url):
    """Defines the content of the modal dialog for viewing PDFs."""
    st.subheader(f"Viewing: {pdf_title}")
    if pdf_url:
        # Embed the PDF using an iframe
        st.markdown(f'<iframe src="{pdf_url}" width="100%" height="650px" style="border:none;" title="PDF Viewer"></iframe>', unsafe_allow_html=True)
        # Add a button to open in new tab as well
        st.link_button("Open Document in New Tab", pdf_url, help="Opens the PDF source URL in a new browser tab.")
    else:
        st.error("Could not construct URL for the PDF.")

# --- Chat Rendering Function ---

def render_main_app(): # Keeping user's function name
    """Render the main chat UI using the modular RAG system."""
    st.header("BASF Document Assistant") # Consider making title more specific like "Chat" if used in multi-page app
    st.write("Ask questions about BASF documentation and chemical engineering.")

    # Check dependencies
    if not RETRIEVER_AVAILABLE or not GENERATOR_AVAILABLE:
        st.error("Required RAG components (retriever or generator) failed to load. Please check imports and paths.")
        # Consider returning if critical components are missing
        # return

    # Initialize message history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            # Store content and sources for assistant messages
            {"role": "assistant", "content": "Hello! How can I help you with your BASF documents?", "sources": []}
        ]

    # === Display Chat History Loop ===
    # This loop now handles rendering ALL messages, including the latest ones after a rerun
    for msg_index, msg in enumerate(st.session_state.messages):
        # Determine avatar based on role
        avatar = ASSISTANT_AVATAR_PATH if msg["role"] == "assistant" else USER_AVATAR_PATH if msg["role"] == "user" else None

        with st.chat_message(msg["role"], avatar=avatar):
            # Display the main text content
            st.markdown(msg["content"], unsafe_allow_html=True)

            # If it's an assistant message and has sources, display them with buttons
            if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
                st.markdown("**Cited Sources:**")
                file_server_port = get_file_server_port()
                displayed_sources_in_msg = set() # Track displayed source files for this specific message

                for source_index, source_info in enumerate(msg["sources"]):
                    if isinstance(source_info, dict):
                        chunk_id = source_info.get('chunk_id', 'N/A')
                        source_path = source_info.get('source', 'Unknown')
                        display_name = os.path.basename(source_path) if source_path != 'Unknown' else 'Unknown Source'

                        # Basic source info line
                        source_line = f"- **{display_name}** (Chunk ID: {chunk_id})"

                        # Check if it's a PDF and has a valid path
                        is_pdf = source_path != 'Unknown' and source_path.lower().endswith('.pdf')
                        view_url = None
                        if is_pdf and file_server_port:
                            try:
                                relative_path = source_path.lstrip('/')
                                relative_path_encoded = quote(relative_path)
                                view_url = f"http://localhost:{file_server_port}/{relative_path_encoded}"
                            except Exception:
                                view_url = None # Handle potential errors during URL creation

                        # Display source info and button if applicable
                        cols = st.columns([0.8, 0.2]) # Adjust ratio as needed
                        with cols[0]:
                            st.markdown(source_line, unsafe_allow_html=True)
                        with cols[1]:
                            if view_url:
                                # Use unique key combining message index, source index, path, and chunk_id
                                button_key = f"view_pdf_chat_{msg_index}_{source_index}_{source_path}_{chunk_id}"
                                st.button(
                                    f"View PDF", # Label is just "View PDF"
                                    key=button_key, # The unique key is still passed here
                                    on_click=show_pdf_modal,
                                    args=(display_name, view_url),
                                    use_container_width=True
                                )
                            elif source_path != 'Unknown' and source_path not in displayed_sources_in_msg:
                                # Show unavailable link only once per source file within this message
                                st.markdown("*(Link unavailable)*", unsafe_allow_html=True)

                        displayed_sources_in_msg.add(source_path) # Track displayed sources within this message

                    else:
                         # Handle cases where source_info might not be a dictionary
                         st.markdown(f"- {source_info} *(Unexpected source format)*", unsafe_allow_html=True)


    # === Handle Chat Input ===
    # This section now only processes input and triggers a rerun.
    # The actual display happens in the loop above.
    if user_input := st.chat_input("What would you like to know?"):
        # 1. Append user message to history (but DO NOT display it here)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 2. Perform RAG Lookup
        if not RETRIEVER_AVAILABLE or not GENERATOR_AVAILABLE:
             st.error("Cannot process query: RAG components are not available.")
             # Optionally add a temporary assistant error message to history
             # assistant_msg = {"role": "assistant", "content": "Sorry, I cannot process your request right now.", "sources": []}
             # st.session_state.messages.append(assistant_msg)
             # st.rerun() # Rerun even if error to show the error message potentially
        else:
            with st.spinner("Searching documents and generating response..."):
                start_time = time.time()
                # Ensure RAG functions are called correctly
                context_block, retrieved_sources_map = retrieve_and_format_context(user_input, num_chunks=3)

                # Handle potential errors from retriever before calling generator
                if context_block == "Error: Retriever not available.":
                     final_response_dict = {"answer": "Error: Could not connect to the document retrieval system.", "sources": []}
                elif not context_block:
                     final_response_dict = {"answer": "I couldn't find relevant information in the documents to answer that specific query.", "sources": []}
                else:
                     # Only call generator if context is valid
                     final_response_dict = generate_response_from_context(user_input, context_block)

                elapsed = time.time() - start_time
                print(f"RAG process completed in {elapsed:.2f}s")

                # 3. Prepare and append assistant response to history
                assistant_answer = final_response_dict.get('answer', "Sorry, I encountered an error generating the response.")
                cited_sources = final_response_dict.get('sources', [])
                if not isinstance(cited_sources, list): cited_sources = []

                assistant_msg = {"role": "assistant", "content": assistant_answer, "sources": cited_sources}
                st.session_state.messages.append(assistant_msg)

                # 4. Rerun to make the history loop display the new user and assistant messages
                st.rerun()


# --- Main Execution Block ---
if __name__ == "__main__":
    # Set page config - this should ideally be done only once in the main script
    # if this file is the main script (e.g., 1_Chat.py)
    # REMOVE or COMMENT OUT if this code is imported by another script (like streamlit_app.py)
    st.set_page_config(
        page_title="BASF Chat", # Title for this page
        layout="wide"
    )
    # Call the main rendering function for the chat page
    render_main_app()
