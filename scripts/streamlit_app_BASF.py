import streamlit as st
import sys
import os
from pathlib import Path

# Ensure Python can find the 'scripts' folder
MODULE_DIR = Path(__file__).parent
sys.path.append(str(MODULE_DIR.parent))

# Import tab components using relative imports
from tab1.postgres_document_search_tab import render_document_search_tab
from tab2.document_cluster_tab import render_document_cluster_tab
from tab3.document_explorer_tab import render_document_explorer_tab

# Function to get the file server port
def get_file_server_port():
    """Get the file server port from the saved file or use default"""
    port_file = os.path.expanduser("~/file_server_port.txt")
    
    if os.path.exists(port_file):
        try:
            with open(port_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            pass
    
    # Default port if file doesn't exist or can't be read
    return 8069

# Set page config
st.set_page_config(page_title='Artificial Retrieval Intelligence', layout='wide')


# Initialize chat history and form submission state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

# Initialize filters
if 'filters' not in st.session_state:
    st.session_state.filters = {}

# Initialize tab switching flags
if 'switch_to_tab2' not in st.session_state:
    st.session_state.switch_to_tab2 = False
if 'switch_to_tab3' not in st.session_state:
    st.session_state.switch_to_tab3 = False

# Get file server port
file_server_port = get_file_server_port()

# Create filter sidebar
with st.sidebar:
    st.header('BASF Document Assistant')
    
    # Add PostgreSQL badge
    st.markdown('<span class="postgres-badge">PostgreSQL Vector DB</span>', unsafe_allow_html=True)
    
    # Display file server status
    st.success(f"Document File Server: Port {file_server_port}")
    
    # Add a divider
    st.divider()
    
    # Add a clear button
    if st.button('Clear Conversation'):
        st.session_state.messages = []
        st.rerun()

# Title for the app

# Create tabs with new names
tab1, tab2, tab3 = st.tabs(['Assistant', 'Explorer', 'Clusters'])

# Determine which tab to show based on the session state
if st.session_state.switch_to_tab2:
    # Reset the flag after detecting it
    st.session_state.switch_to_tab2 = False
    # Show the cluster tab content
    with tab3:
        render_document_cluster_tab()
    # Hide other tab content
    with tab1:
        st.empty()
    with tab2:
        st.empty()
elif st.session_state.switch_to_tab3:
    # Reset the flag after detecting it
    st.session_state.switch_to_tab3 = False
    # Show the document explorer tab
    with tab2:
        render_document_explorer_tab()
    # Hide other tab content
    with tab1:
        st.empty()
    with tab3:
        st.empty()
else:
    # Show all tab content with tab1 as default
    with tab1:
        render_document_search_tab()
    
    with tab2:
        render_document_explorer_tab()
        
    with tab3:
        if st.session_state.get('last_search_query'):
            st.info('You can visualize document relationships based on your most recent query.')
        render_document_cluster_tab()
