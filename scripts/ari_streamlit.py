#!/usr/bin/env python3
"""
Main Streamlit application script with a tabbed interface.

Renders the Chat interface in the first tab.
"""

import streamlit as st

# Import the main rendering function from the chat page module
try:
    # Assuming the chat code is saved as chat_page.py
    from tab1.chat import render_main_app as render_chat_tab_content
    from tab3.document_explorer_tab import render_document_explorer_tab 
    print("✅ Imported chat page content function.")
except ImportError as e:
    st.error(f"Failed to import from chat_page.py. Ensure it exists and contains 'render_main_app'. Error: {e}")
    # Define a dummy function to prevent crash
    def render_chat_tab_content():
        st.header("Chat Interface Error")
        st.error("Could not load the chat interface module (chat_page.py).")

# --- Main Execution Block ---
if __name__ == "__main__":
    # Set page config - Do this ONCE here in the main app script
    st.set_page_config(
        page_title="Artificial Retrieval Intelligence", # Overall App Title
        layout="wide"
    )
    st.markdown("""
        <style>
            .reportview-container {
                margin-top: -2em;
            }
            .stAppDeployButton {display:none;}  # <-- THIS LINE HIDES THE DEPLOY BUTTON
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Artificial Retrieval Intelligence") # Optional: Add an overall title above the tabs

    # Create Tabs
    tab1, tab2 = st.tabs(["Chat", "Document Explorer"])

    # Render content for Chat Tab
    with tab1:
        # Call the function imported from chat_page.py
        render_chat_tab_content()

    # Render content for Document Explorer Tab (Placeholder)
    with tab2:
        render_document_explorer_tab()
        # Example:
        # from document_explorer_page import render_document_explorer_page

