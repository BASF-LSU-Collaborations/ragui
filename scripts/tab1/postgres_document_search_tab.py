#!/usr/bin/env python3
"""
Document Search Tab using PostgreSQL for BASF Document Assistant

Provides a conversational AI interface to search and analyze documents
using a PostgreSQL vector database.
"""

import streamlit as st
import os

# Import the PostgreSQL-based RAG function
from scripts.rag.postgres_rag import postgres_rag

# --- Helper Functions ---

def get_file_server_port():
    """Get the file server port from disk or use default."""
    port_file = os.path.expanduser("~/file_server_port.txt")
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 8069


def get_chat_history():
    """Return the last 6 raw messages for context."""
    history = []
    marker = "**📚 PostgreSQL Document Search Results**\n\n"
    for msg in st.session_state.messages:
        content = msg["content"]
        if msg["role"] == "user":
            history.append(content.replace("**You:** ", ""))
        else:
            if marker in content:
                history.append(content.split(marker, 1)[1])
            else:
                history.append(content)
    return history[-6:]

# --- Render Function ---

def render_document_search_tab():
    """Render the chat UI; messages scroll, input stays pinned."""
    st.header("Document Assistant")
    st.write("💬 Ask me questions about BASF documentation and chemical engineering!")

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! How can I help you with your BASF documents?"}
        ]

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    # Chat input (pinned at bottom)
    if user_input := st.chat_input("What would you like to know about BASF documentation?"):
        # Append user message
        user_msg = {"role": "user", "content": f"**You:** {user_input}"}
        st.session_state.messages.append(user_msg)

        # Perform RAG lookup immediately
        with st.spinner("🧪 Searching through BASF docs..."):
            history = get_chat_history()
            response, unique_sources = postgres_rag(
                user_input,
                history,
                top_n=5,
                purpose="summary"
            )

        # Build assistant reply
        base_url = f"http://localhost:{get_file_server_port()}"
        ai_content = f"**📚 PostgreSQL Document Search Results**\n\n{response}\n\n"
        if unique_sources:
            ai_content += "**Unique Source Files Used:**\n"
            for source, path in unique_sources.items():
                filename = os.path.basename(source)
                url = f"{base_url}/{path.lstrip('/')}"
                ai_content += f"- **{filename}** [<a href='{url}' target='_blank'>View</a>]\n"

        assistant_msg = {"role": "assistant", "content": ai_content}
        st.session_state.messages.append(assistant_msg)

        # Redisplay newly added messages in this run
        with st.chat_message("assistant"):
            st.markdown(ai_content, unsafe_allow_html=True)

# --- Main ---

if __name__ == "__main__":
    render_document_search_tab()
