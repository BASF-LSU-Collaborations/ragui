# /home/jonathan_morse/ragui/scripts/streamlit_app_BASF.py
import streamlit as st
import sys
import os
import time
import urllib.parse
import streamlit.components.v1 as components

# Ensure Python can find the 'scripts' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import tab components
from scripts.tab1.document_search_tab import render_document_search_tab

# Set Streamlit Page Config
st.set_page_config(
    page_title="BASF Document Assistant",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Custom Styling
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        font-size: 16px;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #E50914;
    }
    .stButton>button {
        background-color: #E50914;
        color: white;
        font-size: 16px;
        border-radius: 10px;
        padding: 8px 20px;
    }
    .stMarkdown {
        font-size: 18px;
    }
    .stSelectbox>div>div>select {
        font-size: 16px;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #E50914;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #222;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E50914 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize chat history and form submission state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

# Initialize filters
if "filters" not in st.session_state:
    st.session_state.filters = {}

# Initialize sidebar selections if not present
if "rating_filter" not in st.session_state:
    st.session_state.rating_filter = "Any"
    
if "year_filter" not in st.session_state:
    st.session_state.year_filter = "Any"
    
if "type_filter" not in st.session_state:
    st.session_state.type_filter = "Any"

# Create filter sidebar - IMPORTANT: define filters before they're used in the tabs
with st.sidebar:
    st.header("📌 Filter Options")
    
    # Document type filter
    type_options = ["Any", "Safety Protocol", "Technical Specification", "Process Documentation", "Maintenance Guide", "Quality Control"]
    st.selectbox("Document Type", type_options, key="type_filter")
    
    # Year filter
    year_options = ["Any", "2020", "2021", "2022", "2023", "2024"]
    st.selectbox("Document Year", year_options, key="year_filter")
    
    # Department filter
    dept_options = ["Any", "Engineering", "Safety", "Quality Control", "Operations", "Maintenance"]
    st.selectbox("Department", dept_options, key="rating_filter")
    
    # Add some info about filters
    st.info("Select filters to narrow down document search. Choose 'Any' to disable a filter.")
    
    # Add a clear button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# Title for the app
st.title("🧪 BASF Document Assistant")

# Create tabs for document chat and clustering visualization
tab1, tab2 = st.tabs(["📚 Document Search", "📊 Document Clusters"])

# Tab 1: Document Search Interface - Now using the imported function
with tab1:
    render_document_search_tab()

# Tab 2: Document Clustering Visualization
