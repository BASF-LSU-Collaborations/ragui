# pages/movie_clusters.py
import streamlit as st
from scripts.visualization.movie_clustering import render_movie_clustering_ui

# Set page config
st.set_page_config(
    page_title="Movie Clusters",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    body {
        background-color: #121212;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Movie Clusters Visualization")

# Clustering controls
reduce_data = st.checkbox(
    "Use reduced dataset (faster loading)",
    value=True,
    help="Process only a subset of movies for faster visualization"
)

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

with st.spinner("Loading movie clusters... This may take a moment."):
    render_movie_clustering_ui(sample_size=sample_size if reduce_data else None)