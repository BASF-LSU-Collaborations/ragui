# /home/jonathan_morse/ragui/scripts/streamlit_app.py
import streamlit as st
import sys
import os
import time

# Ensure Python can find the 'scripts' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the movie RAG function
from scripts.rag.rag_retrieval import movie_rag

# Import the clustering visualization (new)
from scripts.visualization.movie_clustering import render_movie_clustering_ui

# Set Streamlit Page Config
st.set_page_config(
    page_title="Movie Recommendation Assistant",
    page_icon="🎬",
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

# Function to get chat history for context
def get_chat_history():
    history = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            # Remove the "You:" prefix
            history.append(msg["content"].replace("**You:** ", ""))
        elif msg["role"] == "assistant":
            # Extract just the assistant response without the tool name
            content = msg["content"]
            if "**🎬 Movie Recommendations**\n\n" in content:
                history.append(content.split("**🎬 Movie Recommendations**\n\n")[1])
            else:
                history.append(content)
    return history[-6:] if len(history) > 6 else history  # Keep only last 6 exchanges for context

# Function to handle form submission
def submit_form():
    if st.session_state.user_question.strip():  # Only process if there's text
        st.session_state.current_question = st.session_state.user_question
        st.session_state.form_submitted = True
        
        # Get filter values
        filters = {}
        
        # Rating filter
        if st.session_state.rating_filter != "Any":
            filters["rating"] = st.session_state.rating_filter
        
        # Year filter
        if st.session_state.year_filter != "Any":
            filters["release_year"] = {"gt": int(st.session_state.year_filter)}
        
        # Type filter
        if st.session_state.type_filter != "Any":
            filters["type"] = st.session_state.type_filter
            
        st.session_state.filters = filters
        st.session_state.user_question = ""  # Clear the input field

# Create filter sidebar - IMPORTANT: define filters before they're used in the tabs
with st.sidebar:
    st.header("📌 Filter Options")
    
    # Rating filter
    rating_options = ["Any", "G", "PG", "PG-13", "R", "TV-MA", "TV-14", "TV-PG", "TV-Y7"]
    st.selectbox("Rating", rating_options, key="rating_filter")
    
    # Year filter
    year_options = ["Any", "2000", "2010", "2015", "2020"]
    st.selectbox("Released after year", year_options, key="year_filter")
    
    # Type filter
    type_options = ["Any", "Movie", "TV Show"]
    st.selectbox("Content type", type_options, key="type_filter")
    
    # Add some info about filters
    st.info("Select filters to narrow down recommendations. Choose 'Any' to disable a filter.")
    
    # Add a clear button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# Title for the app
st.title("🎬 Movie Recommendation Assistant")

# Create tabs for recommendation chat and clustering visualization
tab1, tab2 = st.tabs(["🍿 Movie Recommendations", "📊 Movie Clusters"])

# Tab 1: Movie Recommendation Chat Interface
with tab1:
    st.write("🍿 Tell me what kind of movie you're in the mood for, and I'll suggest something perfect!")
    
    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Create a form for user input
    with st.form(key="question_form", clear_on_submit=True):
        user_input = st.text_input(
            "🎬 What kind of movie are you in the mood for?", 
            key="user_question",
            placeholder="E.g., 'Something with action and comedy' or 'A thought-provoking drama'"
        )
        submit_button = st.form_submit_button("Get Recommendations", on_click=submit_form)
    
    # Process input after form submission
    if st.session_state.form_submitted:
        # Get the question from session state
        user_input = st.session_state.current_question
        
        # Display active filters if any
        filter_text = ""
        if st.session_state.filters:
            filter_parts = []
            if "rating" in st.session_state.filters:
                filter_parts.append(f"Rating: {st.session_state.filters['rating']}")
            if "release_year" in st.session_state.filters:
                filter_parts.append(f"After {st.session_state.filters['release_year']['gt']}")
            if "type" in st.session_state.filters:
                filter_parts.append(f"Type: {st.session_state.filters['type']}")
            
            if filter_parts:
                filter_text = f" (Filters: {', '.join(filter_parts)})"
        
        # Store user input in chat history
        st.session_state.messages.append({"role": "user", "content": f"**You:** {user_input}{filter_text}"})
        
        # Show loading animation
        with st.spinner("🎬 Finding perfect movies for you..."):
            # Get chat history for context
            chat_history = get_chat_history()
            
            # Call the movie recommendation RAG function
            response = movie_rag(user_input, chat_history, st.session_state.filters)
        
        # Format AI response
        ai_response = f"**🎬 Movie Recommendations**\n\n{response}"
        
        # Store AI response in chat history
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        
        # Display AI response
        with st.chat_message("assistant"):
            st.markdown(ai_response)
        
        # Reset submission flag for next question
        st.session_state.form_submitted = False
        
        # Rerun to update the UI (this will clear the input and show the new message)
        st.rerun()
    
    # Add some helpful examples at the bottom
    with st.expander("💡 Example Requests"):
        st.markdown("""
        - "I want something with lots of action and explosions"
        - "A romantic comedy for date night"
        - "A documentary about nature"
        - "Something like Stranger Things"
        - "A movie that will make me think"
        - "A light-hearted comedy for family movie night"
        """)

# Tab 2: Movie Clustering Visualization
with tab2:
    # Add a checkbox to limit data size for faster testing
    reduce_data = st.checkbox(
        "Use reduced dataset (faster loading)",
        value=True,
        help="Process only a subset of movies for faster visualization"
    )
    
    # Add sample size slider if using reduced dataset
    sample_size = 500  # Default
    if reduce_data:
        sample_size = st.slider(
            "Number of movies to visualize",
            min_value=100,
            max_value=2000,
            value=500,
            step=100,
            help="Smaller values will load faster but show fewer movies"
        )
    
    # Pass the sample size to the clustering visualization
    with st.spinner("Loading movie clusters... This may take a moment."):
        # This will call the clustering visualization function from our module
        # Add the sample_size parameter to pass to your function
        render_movie_clustering_ui(sample_size=sample_size if reduce_data else None)