import streamlit as st
import sys
import os
import time

# Ensure Python can find the 'scripts' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the movie RAG function
from scripts.rag.rag_retrieval import movie_rag

# Set Streamlit Page Config
st.set_page_config(
    page_title="Movie Recommendation Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS 
st.markdown("""
    <style>
    .stSpinner > div {
        animation: pulse 1.5s infinite;
        color: #E50914 !important;
    }
    
    /* Smooth transition for recommendations */
    .stChatMessage {
        opacity: 0;
        animation: fadeIn 0.5s ease-out forwards;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Hover effects for filter buttons */
    .stPopover > button {
        transition: all 0.3s ease !important;
    }
    
    .stPopover > button:hover {
        background-color: rgba(229, 9, 20, 0.1) !important;
        transform: scale(1.05) !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

# Initialize filters with default values
if "rating_filter" not in st.session_state:
    st.session_state.rating_filter = []
    
if "year_filter" not in st.session_state:
    st.session_state.year_filter = []
    
if "type_filter" not in st.session_state:
    st.session_state.type_filter = []

def get_chat_history():
    history = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            history.append(msg["content"].replace("**You:** ", ""))
        elif msg["role"] == "assistant":
            content = msg["content"]
            if "**🎬 Movie Recommendations**\n\n" in content:
                history.append(content.split("**🎬 Movie Recommendations**\n\n")[1])
            else:
                history.append(content)
    return history[-6:] if len(history) > 6 else history

def submit_form():
    if st.session_state.user_question.strip():
        st.session_state.current_question = st.session_state.user_question
        st.session_state.form_submitted = True
        
        # Collect filters
        filters = {}
        
        # Rating filter
        if st.session_state.rating_filter:
            filters["rating"] = st.session_state.rating_filter[0]
        
        # Year filter
        if st.session_state.year_filter:
            filters["release_year"] = {"gt": int(st.session_state.year_filter[0])}
        
        # Type filter
        if st.session_state.type_filter:
            filters["type"] = st.session_state.type_filter[0]
            
        st.session_state.filters = filters
        st.session_state.user_question = ""  # Clear input field

# Title for the app
st.title("🎬 Movie Recommendation Assistant")


# filter options
rating_options = ["G", "PG", "PG-13", "R", "TV-MA", "TV-14", "TV-PG", "TV-Y7"]
year_options = ["2000", "2010", "2015", "2020"]
type_options = ["Movie", "TV Show"]

# Filter container
filter_container = st.container()
with filter_container:
    col1, col2, col3 = st.columns([1,1,1], gap="small")
    
    with col1:
        rating_popover = st.popover("📊 Ratings", use_container_width=True)
        with rating_popover:
            st.subheader("Select Ratings")
            
            # clear button
            if st.button("Clear Selection", key="clear_ratings"):
                st.session_state.rating_filter = []
                for option in rating_options:
                    st.session_state[f"rating_{option}"] = False
            
            selected_ratings = []
            for option in rating_options:
                if st.checkbox(option, key=f"rating_{option}"):
                    selected_ratings.append(option)
            st.session_state.rating_filter = selected_ratings
            if selected_ratings:
                st.write("Selected: " + ", ".join(selected_ratings))
        
    with col2:
        year_popover = st.popover("📅 Years", use_container_width=True)
        with year_popover:
            st.subheader("Released After")
            
            
            if st.button("Clear Selection", key="clear_years"):
                st.session_state.year_filter = []
                for option in year_options:
                    st.session_state[f"year_{option}"] = False
            
            selected_years = []
            for option in year_options:
                if st.checkbox(option, key=f"year_{option}"):
                    selected_years.append(option)
            if len(selected_years) > 1:
                st.warning("Please select only one year")
                selected_years = [selected_years[-1]]
            st.session_state.year_filter = selected_years
            if selected_years:
                st.write("Selected: " + ", ".join(selected_years))
        
    with col3:
        type_popover = st.popover("🎬 Type", use_container_width=True)
        with type_popover:
            st.subheader("Content Type")
            
            
            if st.button("Clear Selection", key="clear_types"):
                st.session_state.type_filter = []
                for option in type_options:
                    st.session_state[f"type_{option}"] = False
            
            selected_types = []
            for option in type_options:
                if st.checkbox(option, key=f"type_{option}"):
                    selected_types.append(option)
            if len(selected_types) > 1:
                st.warning("Please select only one type")
                selected_types = [selected_types[-1]]
            st.session_state.type_filter = selected_types
            if selected_types:
                st.write("Selected: " + ", ".join(selected_types))
                 
# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input form
with st.form(key="question_form", clear_on_submit=True):
    user_input = st.text_input(
        "", 
        key="user_question",
        placeholder="Looking for a movie?"
    )
    submit_button = st.form_submit_button("Get Recommendations", on_click=submit_form)

# Process input and show recommendations
if st.session_state.form_submitted:
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
    
    st.session_state.messages.append({"role": "user", "content": f"**You:** {user_input}{filter_text}"})
    
    with st.spinner("🎬 Finding perfect movies for you..."):
        chat_history = get_chat_history()
        response = movie_rag(user_input, chat_history, st.session_state.filters)
    
    ai_response = f"**🎬 Movie Recommendations**\n\n{response}"
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    
    with st.chat_message("assistant"):
        st.markdown(ai_response)
    
    st.session_state.form_submitted = False
    st.rerun()

# Example requests
with st.expander("💡 Example Requests"):
    st.markdown("""
    - "I want something with lots of action and explosions"
    - "A romantic comedy for date night"
    - "A documentary about nature"
    - "Something like Stranger Things"
    - "A movie that will make me think"
    - "A light-hearted comedy for family movie night"
    """)