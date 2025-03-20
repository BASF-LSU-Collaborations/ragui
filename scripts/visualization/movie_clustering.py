"""
Movie clustering visualization component for Netflix recommendation system.
This module provides functions to cluster movie embeddings and visualize them in Streamlit.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from chromadb import PersistentClient
import os

# Import optional dependencies with error handling
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

try:
    from sklearn.manifold import TSNE
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def get_embeddings_from_chroma(chroma_path="./chroma_db", collection_name="netflix_movies", sample_size=None):
    """
    Extract embeddings, IDs and metadata from ChromaDB.
    
    Args:
        chroma_path: Path to ChromaDB directory
        collection_name: Name of the collection to use
        sample_size: Optional limit on number of items to retrieve (for faster processing)
        
    Returns:
        Dictionary with embeddings, ids, and metadatas
    """
    if not os.path.exists(chroma_path):
        raise FileNotFoundError(f"ChromaDB path not found: {chroma_path}")
    
    try:
        client = PersistentClient(chroma_path)
        collection = client.get_collection(collection_name)
        
        # Get collection count
        collection_count = collection.count()
        
        if sample_size and sample_size < collection_count:
            # Get a sample of the data if sample_size is specified
            st.info(f"Using a sample of {sample_size} movies out of {collection_count} total movies")
            
            # For simplicity, just get the first n items
            # In a production app, you might want to use random sampling
            result = collection.get(
                limit=sample_size,
                include=["embeddings", "metadatas"]
            )
        else:
            # Get all data from collection
            result = collection.get(include=["embeddings", "metadatas"])
        
        return {
            "embeddings": result["embeddings"],
            "ids": result["ids"],
            "metadatas": result["metadatas"]
        }
    except Exception as e:
        st.error(f"Error accessing ChromaDB: {str(e)}")
        return None


def reduce_dimensions(embeddings, n_components=2, method="umap", random_state=42):
    """
    Reduce dimensionality of embeddings for visualization.
    
    Args:
        embeddings: List of embedding vectors
        n_components: Number of dimensions to reduce to (2 or 3)
        method: Reduction method ('umap', 'tsne', or 'pca')
        random_state: Random seed for reproducibility
        
    Returns:
        Array of reduced embeddings
    """
    if method == "umap" and UMAP_AVAILABLE:
        reducer = umap.UMAP(n_components=n_components, random_state=random_state)
    elif method == "tsne" and SKLEARN_AVAILABLE:
        reducer = TSNE(n_components=n_components, random_state=random_state)
    elif method == "pca" and SKLEARN_AVAILABLE:
        reducer = PCA(n_components=n_components, random_state=random_state)
    else:
        if not SKLEARN_AVAILABLE:
            st.warning("scikit-learn not installed. Defaulting to PCA with NumPy.")
            # Fallback to simple PCA using NumPy
            cov_matrix = np.cov(np.array(embeddings).T)
            eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
            idx = eigenvalues.argsort()[::-1]
            eigenvectors = eigenvectors[:, idx]
            reduced_data = np.array(embeddings) @ eigenvectors[:, :n_components]
            return reduced_data
        else:
            # Default to PCA if the requested method is not available
            reducer = PCA(n_components=n_components, random_state=random_state)
    
    # Convert embeddings to numpy array if it's not already
    embeddings_array = np.array(embeddings)
    reduced_embeddings = reducer.fit_transform(embeddings_array)
    return reduced_embeddings


def cluster_movies(reduced_embeddings, method="kmeans", n_clusters=8, eps=0.5, min_samples=5):
    """
    Apply clustering algorithm to reduced embeddings.
    
    Args:
        reduced_embeddings: Array of reduced dimension embeddings
        method: Clustering method ('kmeans' or 'dbscan')
        n_clusters: Number of clusters for KMeans
        eps: Epsilon parameter for DBSCAN
        min_samples: Min samples parameter for DBSCAN
        
    Returns:
        Array of cluster assignments
    """
    if not SKLEARN_AVAILABLE:
        st.warning("scikit-learn not installed. Clustering unavailable.")
        return np.zeros(len(reduced_embeddings))
    
    if method == "kmeans":
        clustering = KMeans(n_clusters=n_clusters, random_state=42)
    elif method == "dbscan":
        clustering = DBSCAN(eps=eps, min_samples=min_samples)
    else:
        clustering = KMeans(n_clusters=n_clusters, random_state=42)
    
    clusters = clustering.fit_predict(reduced_embeddings)
    return clusters


def prepare_cluster_dataframe(data_dict, reduced_embeddings, clusters):
    """
    Create a DataFrame with clustering information for visualization.
    
    Args:
        data_dict: Dictionary with embeddings, ids, and metadatas
        reduced_embeddings: Array of reduced dimension embeddings
        clusters: Array of cluster assignments
        
    Returns:
        DataFrame with x, y, (z), id, cluster, and metadata columns
    """
    # Create dataframe with reduced dimensions
    if reduced_embeddings.shape[1] == 3:
        df = pd.DataFrame({
            'x': reduced_embeddings[:, 0],
            'y': reduced_embeddings[:, 1],
            'z': reduced_embeddings[:, 2],
            'id': data_dict["ids"],
            'cluster': clusters
        })
    else:
        df = pd.DataFrame({
            'x': reduced_embeddings[:, 0],
            'y': reduced_embeddings[:, 1],
            'id': data_dict["ids"],
            'cluster': clusters
        })
    
    # Add metadata
    for i, metadata in enumerate(data_dict["metadatas"]):
        if i < len(df):  # Safety check
            df.loc[i, "title"] = metadata.get("title", "Unknown")
            df.loc[i, "type"] = metadata.get("type", "Unknown")
            df.loc[i, "release_year"] = metadata.get("release_year", "Unknown")
            df.loc[i, "rating"] = metadata.get("rating", "Unknown")
    
    return df


def compute_clusters(chroma_path="./chroma_db", 
                     dim_reduction="umap", 
                     clustering_method="kmeans",
                     n_clusters=8,
                     n_dimensions=2,
                     sample_size=None):
    """
    Compute clusters for movie visualization.
    
    Args:
        chroma_path: Path to ChromaDB directory
        dim_reduction: Dimensionality reduction method
        clustering_method: Clustering algorithm
        n_clusters: Number of clusters
        n_dimensions: Number of dimensions for visualization (2 or 3)
        sample_size: Optional limit on number of items to retrieve (for faster processing)
        
    Returns:
        DataFrame with clustering information or None if error
    """
    try:
        # Get embeddings from ChromaDB
        data = get_embeddings_from_chroma(chroma_path, sample_size=sample_size)
        if data is None:
            return None
        
        # Reduce dimensions
        reduced_embeddings = reduce_dimensions(
            data["embeddings"], 
            n_components=n_dimensions, 
            method=dim_reduction
        )
        
        # Cluster
        clusters = cluster_movies(
            reduced_embeddings, 
            method=clustering_method, 
            n_clusters=n_clusters
        )
        
        # Create dataframe
        return prepare_cluster_dataframe(data, reduced_embeddings, clusters)
        
    except Exception as e:
        st.error(f"Error computing clusters: {str(e)}")
        return None


def display_cluster_visualization(cluster_df, color_by="cluster", is_3d=False):
    """
    Display a Plotly visualization of movie clusters.
    
    Args:
        cluster_df: DataFrame with clustering information
        color_by: Column to use for coloring points
        is_3d: Whether to use 3D visualization
    """
    if cluster_df is None or len(cluster_df) == 0:
        st.error("No cluster data available for visualization.")
        return
    
    hover_data = ['title', 'type', 'release_year', 'rating']
    
    if is_3d and 'z' in cluster_df.columns:
        fig = px.scatter_3d(
            cluster_df, 
            x='x', 
            y='y', 
            z='z',
            color=color_by,
            hover_data=hover_data,
            title=f'Movie Clusters (colored by {color_by})'
        )
    else:
        fig = px.scatter(
            cluster_df, 
            x='x', 
            y='y', 
            color=color_by,
            hover_data=hover_data,
            title=f'Movie Clusters (colored by {color_by})'
        )
    
    # Update layout for better visualization
    fig.update_layout(
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    # Display the plot
    st.plotly_chart(fig, use_container_width=True)


def render_movie_clustering_ui(sample_size=None):
    """
    Render the movie clustering UI component in Streamlit.
    This is the main function to call from the Streamlit app.
    
    Args:
        sample_size: Optional limit on number of items to retrieve (for faster processing)
    """
    st.header("Movie Clustering Visualization")
    st.write("Explore how movies are grouped based on their content and themes.")
    
    # Create a container for clustering settings
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            dim_reduction = st.selectbox(
                "Dimensionality Reduction Method", 
                ["pca", "umap", "tsne"],
                index=0,  # Default to PCA for speed
                help="Method used to reduce embedding dimensions for visualization"
            )
            
            clustering_method = st.selectbox(
                "Clustering Method", 
                ["kmeans", "dbscan"],
                index=0,
                help="Algorithm used to group movies"
            )
        
        with col2:
            n_dimensions = st.radio(
                "Visualization Dimensions",
                [2, 3],
                index=0,
                help="2D or 3D visualization"
            )
            
            n_clusters = st.slider(
                "Number of Clusters", 
                min_value=3, 
                max_value=20, 
                value=8,
                help="Number of movie clusters to create (for KMeans)"
            )
    
    color_by = st.selectbox(
        "Color By", 
        ["cluster", "type", "rating", "release_year"],
        index=0,
        help="Property to use for coloring points"
    )
    
    # Check if we already have the clustering data computed
    # Include sample_size in the cache key if it's provided
    sample_suffix = f"_sample{sample_size}" if sample_size else ""
    cluster_data_key = f"cluster_data_{dim_reduction}_{clustering_method}_{n_clusters}_{n_dimensions}{sample_suffix}"
    
    if cluster_data_key not in st.session_state:
        with st.spinner("Generating movie clusters... This may take a moment."):
            st.session_state[cluster_data_key] = compute_clusters(
                dim_reduction=dim_reduction,
                clustering_method=clustering_method,
                n_clusters=n_clusters,
                n_dimensions=n_dimensions,
                sample_size=sample_size
            )
    
    # Display the visualization
    display_cluster_visualization(
        st.session_state[cluster_data_key], 
        color_by=color_by,
        is_3d=(n_dimensions == 3)
    )
    
    # Add explanation
    with st.expander("How to use this visualization"):
        st.markdown("""
        ### Understanding the visualization:
        - Each point represents a movie or TV show in our database
        - Points that are close together have similar themes, content, or descriptions
        - Colors represent different groups of similar content
        - Hover over points to see details about each title
        
        ### Tips:
        - **For faster loading**: Choose PCA instead of UMAP or t-SNE
        - Try changing the clustering method or number of clusters to see different groupings
        - Use the "Color By" option to visualize different properties
        - Switch between 2D and 3D for different perspectives
        - In 3D mode, you can rotate the visualization by clicking and dragging
        """)
    
    # Add cluster analysis section
    if st.session_state[cluster_data_key] is not None:
        with st.expander("Cluster Analysis"):
            df = st.session_state[cluster_data_key]
            
            # Count titles per cluster
            cluster_counts = df['cluster'].value_counts().reset_index()
            cluster_counts.columns = ['Cluster', 'Count']
            
            # Display cluster sizes
            st.subheader("Cluster Sizes")
            st.bar_chart(cluster_counts.set_index('Cluster'))
            
            # Allow exploring specific clusters
            selected_cluster = st.selectbox(
                "Select a cluster to explore", 
                sorted(df['cluster'].unique())
            )
            
            cluster_movies = df[df['cluster'] == selected_cluster]
            st.write(f"Showing {len(cluster_movies)} movies in cluster {selected_cluster}")
            st.dataframe(
                cluster_movies[['title', 'type', 'release_year', 'rating']],
                use_container_width=True
            )


if __name__ == "__main__":
    # This allows testing the module directly
    import streamlit as st
    st.set_page_config(page_title="Movie Clusters", layout="wide")
    render_movie_clustering_ui()