#!/usr/bin/env python3
"""
Simple example demonstrating st.dialog (modal) in Streamlit,
embedding a PDF using an iframe.
"""

import streamlit as st
import time
import os
import warnings
from urllib.parse import quote # Import quote for URL encoding

# --- Helper Function to get File Server Port ---
def get_file_server_port():
    """Get the file server port from the saved file or use default"""
    port_file = os.path.expanduser("~/file_server_port.txt")
    default_port = 8070 # Use 8070 as the default based on user confirmation
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                port = int(f.read().strip())
                return port
        except (ValueError, IOError) as e:
             warnings.warn(f"Could not read port file {port_file}: {e}. Using default {default_port}.")
             pass
    return default_port

# --- Configuration for the PDF ---
# The specific PDF path you provided
PDF_LOCAL_PATH = "/shared_folders/team_1/document_batch/UTILS/TechTeam/4000 Air and Nitrogen/Projects/USE-206829 Geismar Plant Air Surge System/Compressor/Bids/Blackmer Bid/Blackmer HDL602C IOM.pdf"

# Define the function that will render the content of the dialog
@st.dialog("PDF Viewer Example")
def show_pdf_modal(pdf_title, pdf_url):
    """This function defines the content of the modal dialog."""
    st.subheader(f"Viewing: {pdf_title}")

    if pdf_url:
        # Embed the PDF using an iframe pointing to the file server URL
        st.markdown(f'<iframe src="{pdf_url}" width="100%" height="600px" style="border:none;" title="PDF Viewer"></iframe>', unsafe_allow_html=True)
        # Replace caption with a link button to the source URL
        st.link_button("Open Source URL", pdf_url, help="Opens the PDF source URL in a new browser tab.")
    else:
        st.error("Could not construct URL for the PDF. Is the file server running and the path correct?")

    # Removed the explicit close button. The dialog closes automatically
    # when the user clicks outside or another action causes a rerun.
    # if st.button("Close Viewer", key="modal_pdf_close_button"):
    #     st.rerun()

# --- Main Tab Rendering Function ---

def render_document_explorer_tab():
    """
    Renders a simple tab with a button to open a modal dialog displaying a PDF.
    """
    st.header("Modal PDF Viewer Test")

    # Get file server port
    file_server_port = get_file_server_port()
    pdf_url = None
    pdf_title = os.path.basename(PDF_LOCAL_PATH) # Get title early

    if file_server_port:
        # Construct the URL for the PDF
        if os.path.exists(PDF_LOCAL_PATH): # Check if path seems valid locally first
             relative_path = PDF_LOCAL_PATH.lstrip('/')
             relative_path_encoded = quote(relative_path) # URL encode
             pdf_url = f"http://localhost:{file_server_port}/{relative_path_encoded}"
        else:
             st.warning(f"Local path does not seem to exist: {PDF_LOCAL_PATH}. URL might be invalid.")
             # Still try to construct URL in case the path is only valid on the server
             relative_path = PDF_LOCAL_PATH.lstrip('/')
             relative_path_encoded = quote(relative_path)
             pdf_url = f"http://localhost:{file_server_port}/{relative_path_encoded}"
    else:
        st.warning("Could not determine file server port. Cannot construct PDF URL.")

    # --- Display Button ---
    # Button to trigger the modal (no columns needed now)
    if st.button("Open PDF in Modal", key="open_pdf_modal_button", disabled=(pdf_url is None)):
        show_pdf_modal(pdf_title, pdf_url)

    st.write("--- End of main page content ---")


# Example of how this might be called in your main Streamlit app
if __name__ == "__main__":
    # For testing the tab individually
    st.set_page_config(page_title="Modal PDF Test", layout="wide")
    render_document_explorer_tab()

