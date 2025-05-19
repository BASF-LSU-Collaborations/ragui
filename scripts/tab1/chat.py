#!/usr/bin/env python3
"""
Streamlit Chat Page Code

Provides the conversational AI interface using modular RAG components.
Includes custom avatars and modal PDF viewer for cited sources.
Handles user input starting with "Create" as a special case by calling
a separate script (db_stats_provider.py) to get file extension counts,
generating a bar chart using st.bar_chart, and displaying it.
Intended to be run as the main page (e.g., 1_Chat.py) in a multi-page app.
"""

import streamlit as st
import os
import sys
import time
import warnings
from pathlib import Path
from urllib.parse import quote # For URL encoding
import pandas as pd # Keep pandas for potential future use AND for chart data
# from collections import Counter # No longer needed here
# --- Database Imports Removed (now in db_stats_provider.py) ---
# from sqlalchemy import text, inspect as sql_inspect

# --- Configuration ---
ASSISTANT_AVATAR_PATH = Path(__file__).resolve().parents[2] / "public" / "ariLogoBlck.png"
USER_AVATAR_PATH = Path(__file__).resolve().parents[2] / "public" / "user.png"

# --- Database Configuration Removed (now in db_stats_provider.py) ---
# DB_TABLE_NAME = "vector_db"
# DB_UNIQUE_DOC_COLUMN = "markdown"

# --- Robust Path Setup ---
# Get the directory of the current script (e.g., /home/jonathan_morse/ragui/scripts/tab1/chat.py)
SCRIPT_DIR = Path(__file__).resolve().parent
# Go up one level to the parent directory (e.g., /home/jonathan_morse/ragui/scripts/)
# This should be the main 'scripts' directory containing 'rag', 'tab1', etc.
SCRIPTS_ROOT_DIR = SCRIPT_DIR.parent

# --- Add necessary directories to sys.path ---

# Add the main 'scripts' directory (SCRIPTS_ROOT_DIR)
# This allows importing modules from sibling directories like 'rag' or 'tab1'
if str(SCRIPTS_ROOT_DIR) not in sys.path:
     sys.path.append(str(SCRIPTS_ROOT_DIR))
     print(f"Appended Scripts root path: {SCRIPTS_ROOT_DIR}") # Debugging

# Define expected paths for clarity (used in error messages)
RAG_SCRIPT_PATH = SCRIPTS_ROOT_DIR / 'rag'
STATS_SCRIPT_DIR = SCRIPTS_ROOT_DIR / 'tab1' # Path to the directory containing db_stats_provider.py

# --- VDB Path setup is still needed IF RAG components depend on it ---
# Path to the VDB pipeline directory (Keep absolute as it's outside the project)
VDB_PIPELINE_PATH = '/shared_folders/team_1/mark_vdb/vdb_pipeline'
if VDB_PIPELINE_PATH not in sys.path:
    sys.path.append(VDB_PIPELINE_PATH)
    print(f"Appended VDB pipeline path: {VDB_PIPELINE_PATH}") # Debugging


# --- Import RAG components ---
try:
    # Assuming rag_retriever.py and rag_generator.py are inside the 'rag' folder
    from rag.rag_retriever import retrieve_and_format_context
    from rag.rag_generator import generate_response_from_context
    RETRIEVER_AVAILABLE = True
    GENERATOR_AVAILABLE = True
    print("✅ RAG functions imported successfully.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import RAG functions: {e}. Check path: {RAG_SCRIPT_PATH}")
    RETRIEVER_AVAILABLE = False
    GENERATOR_AVAILABLE = False
    # Define placeholders
    def retrieve_and_format_context(query, num_chunks=3):
        st.error(f"Error: rag_retriever module not found. Check path: {RAG_SCRIPT_PATH}")
        return "Error: Retriever not available.", {}
    def generate_response_from_context(query, context_block):
        st.error(f"Error: rag_generator module not found. Check path: {RAG_SCRIPT_PATH}")
        return {"answer": "Error: Generator not available.", "sources": []}

# --- Import Database Initializer Removed (now only needed in db_stats_provider.py) ---
# try:
#     from init_vector_db import init_vector_db
#     INIT_DB_AVAILABLE = True
#     print("✅ init_vector_db imported successfully.")
# except ImportError as e:
#     warnings.warn(f"⚠️ Failed to import init_vector_db. Check VDB_PIPELINE_PATH: {e}")
#     INIT_DB_AVAILABLE = False
#     def init_vector_db(wipe_database=False): return None, None # Placeholder

# --- Import Data Fetching Function ---
try:
    # Import from the new script name in the 'tab1' directory
    from tab1.db_stats_provider import get_extension_counts_from_db
    STATS_FUNCTION_AVAILABLE = True
    print("✅ Stats function imported successfully from tab1.db_stats_provider.")
except ImportError as e:
    warnings.warn(f"⚠️ Failed to import stats function from tab1.db_stats_provider: {e}. Check path: {STATS_SCRIPT_DIR}")
    STATS_FUNCTION_AVAILABLE = False
    def get_extension_counts_from_db(): return None # Placeholder


# --- Helper Functions ---

# get_extension is no longer needed here, it's in db_stats_provider.py
# def get_extension(filepath): ...

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
@st.dialog("Document Viewer")
def show_pdf_modal(pdf_title, pdf_url):
    """Defines the content of the modal dialog for viewing PDFs."""
    st.subheader(f"Viewing: {pdf_title}")
    if pdf_url:
        st.markdown(f'<iframe src="{pdf_url}" width="100%" height="650px" style="border:none;" title="PDF Viewer"></iframe>', unsafe_allow_html=True)
    else:
        st.error("Could not construct URL for the PDF.")

# --- Chat Rendering Function ---

def render_main_app(): # Keeping user's function name
    """Render the main chat UI using the modular RAG system."""
    st.header("BASF Document Assistant")

    # Initialize message history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! How can I help you with your BASF documents?", "sources": []}
        ]

    # === Display Chat History Loop ===
    for msg_index, msg in enumerate(st.session_state.messages):
        role = msg.get("role")
        if role not in ["user", "assistant"]:
            continue

        avatar = ASSISTANT_AVATAR_PATH if role == "assistant" else USER_AVATAR_PATH

        with st.chat_message(role, avatar=avatar):
            # 1. Pull out content and sources
            content = msg.get("content", "")
            sources = msg.get("sources", [])

            # 2. If assistant and has sources, append [1][2]… markers
            if role == "assistant" and sources:
                citation_markers = "".join(f"[{i+1}]" for i in range(len(sources)))
                content = f"{content} {citation_markers}"

            # 3. Display the (possibly annotated) content
            st.markdown(content, unsafe_allow_html=True)

        # 4. Display sources if they exist, numbered to match the markers
        if role == "assistant" and sources:
            st.markdown("**Cited Sources:**")
            file_server_port = get_file_server_port()
            displayed_sources_in_msg = set()

            for source_index, source_info in enumerate(sources):
                if isinstance(source_info, dict):
                    idx = source_index + 1
                    chunk_id    = source_info.get("chunk_id", "N/A")
                    source_path = source_info.get("source", "Unknown")
                    display_name = os.path.basename(source_path) if source_path != "Unknown" else "Unknown Source"

                    # Build URL if it's a PDF
                    view_url = None
                    if source_path.lower().endswith(".pdf") and file_server_port:
                        try:
                            rel = source_path.lstrip("/")
                            view_url = f"http://localhost:{file_server_port}/{quote(rel)}"
                        except Exception:
                            view_url = None

                    # Render the name itself as a button to open the modal
                    if view_url:
                        button_key = f"pdf_link_{msg_index}_{source_index}"
                        if st.button(f"[{idx}] {display_name}", key=button_key):
                            show_pdf_modal(display_name, view_url)
                    else:
                        # Fallback for non‐PDF or missing URL
                        st.markdown(f"[{idx}] **{display_name}** *(Link unavailable)*", unsafe_allow_html=True)

                    displayed_sources_in_msg.add(source_path)
                else:
                    st.markdown(f"- {source_info} *(Unexpected source format)*", unsafe_allow_html=True)



    # === Handle Chat Input ===
    if user_input := st.chat_input("What would you like to know?"):
        # 1. ALWAYS Append user message to history first
        st.session_state.messages.append({"role": "user", "content": user_input})

        # --- START 'Create' Keyword Handling ---
        if user_input.strip().lower().startswith("create"):
            # --- Handle Special 'Create' Command ---
            # Check if the imported stats function is available
            if not STATS_FUNCTION_AVAILABLE:
                 st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, the statistics function (from db_stats_provider) is currently unavailable.",
                    "sources": []
                 })
            else:
                with st.spinner("Generating file distribution chart..."):
                    chart_data_series = None # Initialize chart data as None
                    content = "" # Initialize content message
                    try:
                        # --- Call the imported function ---
                        print("Calling get_extension_counts_from_db...")
                        extension_counts = get_extension_counts_from_db() # Returns Counter or None

                        # --- Process the results ---
                        if extension_counts is not None:
                            if extension_counts: # Check if Counter is not empty
                                # Convert Counter to Pandas Series for st.bar_chart
                                chart_data_series = pd.Series(extension_counts).sort_values(ascending=False) # Sort for better viz
                                content = "Okay, here is the file extension distribution from the database:"
                            else:
                                content = "Found no files with extensions in the database to plot."
                        else:
                            # Function returned None, indicating an error during DB interaction
                            content = "Sorry, I could not retrieve the necessary data from the database to create the chart."

                    except Exception as e:
                         # Catch errors during the function call or data processing
                         st.error(f"An error occurred while creating the chart: {e}")
                         st.exception(e)
                         content = "Sorry, an unexpected error occurred while trying to generate the chart."

                    # Append the final message (content + chart data)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": content,
                        "sources": [],
                        "chart_data": chart_data_series # Store the Pandas Series (or None)
                    })

        else:
            # --- Handle Normal RAG Query (Original Logic) ---
            if not RETRIEVER_AVAILABLE or not GENERATOR_AVAILABLE:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, I cannot process your request right now due to a system configuration issue.",
                    "sources": []
                })
                st.error("Cannot process query: RAG components are not available.")
            else:
                with st.spinner("Searching documents and generating response..."):
                    start_time = time.time()
                    try:
                        # 1. Retrieve context
                        context_block, retrieved_sources_map = retrieve_and_format_context(
                            user_input, num_chunks=3
                        )

                        # 2. Handle empty or error contexts
                        if context_block == "Error: Retriever not available.":
                            final_response_dict = {
                                "answer": "Error: Could not connect to the document retrieval system.",
                                "sources": []
                            }
                        elif not context_block:
                            final_response_dict = {
                                "answer": "I couldn't find relevant information in the documents to answer that specific query.",
                                "sources": []
                            }
                        else:
                            # 3. Build chat history (excluding the new user_input)
                            chat_history = [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.messages[:-1]
                                if m["role"] in ("user", "assistant")
                            ]
                            # 4. Trim to last 6 messages (3 full turns) to manage token usage
                            chat_history = chat_history[-6:]

                            # 5. Generate response with history
                            final_response_dict = generate_response_from_context(
                                user_input,
                                context_block,
                                chat_history=chat_history
                            )

                        # 6. Append assistant’s reply
                        elapsed = time.time() - start_time
                        print(f"RAG process completed in {elapsed:.2f}s")

                        assistant_answer = final_response_dict.get(
                            "answer",
                            "Sorry, I encountered an error generating the response."
                        )
                        cited_sources = final_response_dict.get("sources", [])
                        if not isinstance(cited_sources, list):
                            cited_sources = []

                        assistant_msg = {
                            "role": "assistant",
                            "content": assistant_answer,
                            "sources": cited_sources
                        }
                        st.session_state.messages.append(assistant_msg)

                    except Exception as e:
                        st.error(f"An error occurred during RAG processing: {e}")
                        st.exception(e)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "Sorry, an unexpected error occurred while processing your request.",
                            "sources": []
                        })

        # 3. ALWAYS rerun to refresh the UI
        st.rerun()

        # --- END 'Create' Keyword Handling ---


# --- Main Execution Block ---
if __name__ == "__main__":
    st.set_page_config(
        page_title="BASF Chat",
        layout="wide"
    )
    render_main_app()
