# /home/jonathan_morse/ragui/scripts/tab1/document_search_tab.py
import streamlit as st
import urllib.parse
import os

# Import the document RAG function
from _deprecated.rag_BASF import document_rag

def render_document_search_tab():
    """
    Renders the Document Search tab of the BASF Document Assistant
    """
    st.write("📚 Ask me questions about BASF documentation and chemical engineering!")
    
    # Create a container for the chat history
    chat_container = st.container()
    
    # Create a container for the input form at the bottom
    form_container = st.container()
    
    # Use the form container to place the input form at the bottom
    with form_container:
        # Create a form for user input
        with st.form(key="question_form", clear_on_submit=True):
            user_input = st.text_input(
                "🧪 What would you like to know about BASF documentation?", 
                key="user_question",
                placeholder="E.g., 'Explain the catalytic process in our latest reactor design' or 'What are the safety protocols for chemical handling?'"
            )
            submit_button = st.form_submit_button("Search Documents", on_click=submit_form)
            
        # Add some helpful examples below the form
        with st.expander("💡 Example Questions"):
            st.markdown("""
            - "What are the safety protocols for chemical handling?"
            - "Explain the catalytic process in our latest reactor design"
            - "What are the maintenance procedures for our equipment?"
            - "How do we handle waste disposal in our facility?"
            - "What are the quality control measures for our products?"
            - "Explain the process flow in our production line"
            """)
    
    # Now use the chat container to display previous messages
    with chat_container:
        # Display previous messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)
    
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
        user_message = f"**You:** {user_input}{filter_text}"
        st.session_state.messages.append({"role": "user", "content": user_message})
        
        # Immediately display the user's message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_message, unsafe_allow_html=True)
        
        # Show loading animation
        with st.spinner("🧪 Searching through BASF documentation..."):
            # Get chat history for context
            chat_history = get_chat_history()
            
            # Call the document RAG function and unpack the response and unique sources.
            response, unique_sources = document_rag(user_input, chat_history, st.session_state.filters)
        
        # Replace with your actual server URL
        base_url = "http://localhost:8069"
        
        # Store sources in session state for persistent display
        if "source_documents" not in st.session_state:
            st.session_state.source_documents = {}
        
        # Update the current sources
        st.session_state.source_documents = unique_sources
        
        # Format AI response
        ai_content = f"**📚 Document Search Results**\n\n{response}\n\n"
        
        # Add sources section to the response with embedded links
        if unique_sources:
            ai_content += "**Unique Source Files Used:**\n"
            
            # Replace with your actual server URL
            base_url = "http://localhost:8069"
            
            for source, path in unique_sources.items():
                # Properly handle the path for URL
                url_path = path
                if url_path.startswith("/"):
                    url_path = url_path[1:]  # Remove leading slash
                
                # Create full URL
                full_url = f"{base_url}/{url_path}"
                
                # Add source with clickable link using HTML - only show filename, not full path
                ai_content += f'- **{source}** [<a href="{full_url}" target="_blank" class="pdf-link">View Document</a>]\n'
        
        # Store the complete formatted response in chat history
        chat_response = {"role": "assistant", "content": ai_content}
        st.session_state.messages.append(chat_response)
        
        # Add after displaying the AI response
        # Inside the if st.session_state.form_submitted: block
                
        # Display AI response
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(ai_content, unsafe_allow_html=True)

        # Add a button to visualize the results
        if st.button("📊 Visualize Document Relationships", key="visualize_button"):
            # Store the query for use in tab 2
            st.session_state.last_search_query = user_input
            # Set the flag to switch to tab 2
            st.session_state.switch_to_tab2 = True
            # We need to remove the active_tab variable to avoid conflicts
            if "active_tab" in st.session_state:
                del st.session_state.active_tab
            # Rerun to update the UI
            st.rerun()

        # Reset submission flag for next question
        st.session_state.form_submitted = False

def get_chat_history():
    """
    Gets the chat history for context
    Returns the last 6 exchanges if available
    """
    history = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            # Remove the "You:" prefix
            history.append(msg["content"].replace("**You:** ", ""))
        elif msg["role"] == "assistant":
            # Extract just the assistant response without the tool name
            content = msg["content"]
            if "**📚 Document Search Results**\n\n" in content:
                history.append(content.split("**📚 Document Search Results**\n\n")[1])
            else:
                history.append(content)
    return history[-6:] if len(history) > 6 else history  # Keep only last 6 exchanges for context

def submit_form():
    """
    Handles form submission
    Sets up the necessary session state variables
    """
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