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
    body {
        background-color: #121212;
        color: white;
    }
            
    /* Remove the "Press Enter to submit form" text */
    .stForm .stTextInput > div > div > label {
        display: none !important;
    }
    
    /* Optional: Further customize the form input */
    .stForm .stTextInput > div > div > input {
        width: 100% !important;
        padding: 10px !important;
        border-radius: 8px !important;
        border: 2px solid #E50914 !important;
        background-color: #222 !important;
        color: white !important;
        font-size: 16px !important;
    }
    
    /* Customize the submit button to match */
    .stForm button {
        background-color: #E50914 !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        transition: background 0.3s ease-in-out !important;
    }
    
    .stForm button:hover {
        background-color: #A0070E !important;
            
    .stTextInput>div>div>input {
        font-size: 16px;
        padding: 12px;
        border-radius: 8px;
        border: 2px solid #E50914;
        background-color: #222;
        color: white;
    }
    .stButton>button {
        background-color: #E50914 !important;
        color: white !important;
        font-size: 16px;
        border-radius: 8px;
        padding: 10px 24px;
        transition: background 0.3s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #B20710 !important;
    }
    .stMarkdown {
        font-size: 18px;
        color: white;
    }
    .stSelectbox>div>div>select {
        font-size: 16px;
        padding: 10px;
        border-radius: 8px;
        border: 2px solid #E50914;
        background-color: #222;
        color: white;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        # background-color: #222;
        border-radius: 4px 4px 0px 0px;
        padding: 12px;
        color: white;
        font-weight: bold;
        transition: background 0.3s ease-in-out;
    }
    .stTabs [aria-selected="true"] {
        # background-color: #E50914 !important;
        color: white !important;
    }
    .stSidebar {
        background-color: #262730;
        padding: 20px;
        border-radius: 12px;
    }
    .stInfo {
        background-color: #222;
        color: white;
        padding: 10px;
        border-radius: 8px;
    }
    .chat-container {
        display: flex;
        flex-direction: column;
        height: 75vh; /* Adjust as needed */
    }
    .chat-messages {
        flex-grow: 1;
        overflow-y: auto;
    }
    .chat-input {
        margin-top: auto;
        display: flex;
    }
    .chat-input input {
        flex-grow: 1;
        margin-right: 10px;
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
    st.header("Movie Filters")
    
    # Rating Filter Popover
    rating_popover = st.popover("Ratings")
    with rating_popover:
        st.subheader("Select Ratings")
        rating_options = ["G", "PG", "PG-13", "R", "TV-MA", "TV-14", "TV-PG", "TV-Y7"]
        
        # Use checkboxes instead of multiselect
        selected_ratings = []
        for option in rating_options:
            if st.checkbox(option, key=f"rating_{option}"):
                selected_ratings.append(option)
        
        # Display selected ratings
        st.session_state.rating_filter = selected_ratings[0] if selected_ratings else "Any"
        
        # Show current selection
        if selected_ratings:
            st.write("Selected: " + ", ".join(selected_ratings))
    
    # Year Filter Popover
    year_popover = st.popover("Years")
    with year_popover:
        st.subheader("Released After")
        year_options = ["2000", "2010", "2015", "2020"]
        
        # Use checkboxes for years
        selected_years = []
        for option in year_options:
            if st.checkbox(option, key=f"year_{option}"):
                selected_years.append(option)
        
        # Ensure only one year is selected
        if len(selected_years) > 1:
            st.warning("Please select only one year")
            selected_years = [selected_years[-1]]
        
        st.session_state.year_filter = selected_years[0] if selected_years else "Any"
        
        # Show current selection
        if selected_years:
            st.write("Selected: " + ", ".join(selected_years))
    
    # Type Filter Popover
    type_popover = st.popover("Type")
    with type_popover:
        st.subheader("Content Type")
        type_options = ["Movie", "TV Show"]
        
        # Use checkboxes for types
        selected_types = []
        for option in type_options:
            if st.checkbox(option, key=f"type_{option}"):
                selected_types.append(option)
        
        # Ensure only one type is selected
        if len(selected_types) > 1:
            st.warning("Please select only one type")
            selected_types = [selected_types[-1]]
        
        st.session_state.type_filter = selected_types[0] if selected_types else "Any"
        
        # Show current selection
        if selected_types:
            st.write("Selected: " + ", ".join(selected_types))
    
    # Clear conversation button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()
    
    # Info about filters
    st.info("Click filter buttons to customize your recommendations.")

# Title for the app
st.title("🎬 Movie Recommendation Assistant")

# Create tabs for recommendation chat and clustering visualization
tab1, tab2 = st.tabs(["🍿 Movie Recommendations", "📊 Movie Clusters"])

# Tab 1: Movie Recommendation Chat Interface
with tab1:
    
    
    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # Create a form for user input
    with st.form(key="question_form", clear_on_submit=True):
        user_input = st.text_input(
            "", 
            key="user_question",
            placeholder="Looking for a movie?"
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