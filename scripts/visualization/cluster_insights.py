import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from openai import OpenAI
import time
from tqdm import tqdm

def get_movie_description(movie_id):
    """
    Retrieve the movie description from the original data.
    
    Args:
        movie_id: ID of the movie to retrieve description for
        
    Returns:
        Movie description string or None if not found
    """
    # This is a placeholder - you'll need to implement this based on your data structure
    # For example, you might load descriptions from your JSON files or query ChromaDB
    
    try:
        # Option 1: Read from your movie_descriptions.json file
        import json
        import os
        
        data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'movie_descriptions.json')
        
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                descriptions = json.load(f)
                
            if movie_id in descriptions:
                return descriptions[movie_id]
        
        # Option 2: Use your ChromaDB collection (if the ID matches)
        from scripts.rag.rag_retrieval import get_movies_collection
        
        collection = get_movies_collection()
        result = collection.get(ids=[movie_id], include=["documents"])
        
        if result and result["documents"] and len(result["documents"]) > 0:
            return result["documents"][0]
        
        return "No description available"
    
    except Exception as e:
        st.error(f"Error retrieving movie description: {str(e)}")
        return "No description available"

def generate_cluster_insights(cluster_df, openai_client):
    """
    Generate insights for each cluster based on movie descriptions.
    
    Args:
        cluster_df: DataFrame with movie data and cluster assignments
        openai_client: OpenAI client for generating insights
        
    Returns:
        DataFrame with cluster insights
    """
    insights = []
    
    # Process each cluster
    for cluster_id in sorted(cluster_df['cluster'].unique()):
        # Get movies in this cluster
        cluster_movies = cluster_df[cluster_df['cluster'] == cluster_id]
        
        # Get a sample of movie titles and descriptions for analysis
        # Limit to 10 movies to avoid token limits
        sample_movies = cluster_movies.head(10)
        movie_details = []
        
        for _, movie in sample_movies.iterrows():
            title = movie.get('title', 'Unknown')
            
            # Retrieve the movie description from the original data
            movie_id = movie.get('id')
            description = get_movie_description(movie_id)
            
            if description:
                movie_details.append(f"Title: {title}\nDescription: {description}")
        
        # Use OpenAI to analyze the cluster
        # Note: Use double curly braces for JSON template to avoid f-string issues
        prompt = f"""
        Analyze these {len(movie_details)} movies from the same cluster and identify:
        1. Common themes, genres, or narrative elements
        2. Distinctive plot patterns or character archetypes
        3. A short descriptive label (3-5 words) that captures the essence of this cluster
        4. Three representative tags/keywords
        
        Here are the movies:
        
        {"\n\n".join(movie_details)}
        
        Provide your analysis in this JSON format:
        {{{{
            "cluster_label": "Short descriptive label",
            "themes": ["Theme 1", "Theme 2", "Theme 3"],
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "description": "A paragraph describing what makes movies in this cluster similar."
        }}}}
        """
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["cluster_id"] = cluster_id
            result["movie_count"] = len(cluster_movies)
            insights.append(result)
            
        except Exception as e:
            # Fallback to simple analysis if OpenAI fails
            insights.append({
                "cluster_id": cluster_id,
                "cluster_label": f"Cluster {cluster_id}",
                "themes": [],
                "keywords": [],
                "description": f"A group of {len(cluster_movies)} similar movies.",
                "movie_count": len(cluster_movies)
            })
    
    return pd.DataFrame(insights)

def find_representative_movies(cluster_df, n=3):
    """
    Find the most representative movies for each cluster.
    
    Args:
        cluster_df: DataFrame with movie data and cluster assignments
        n: Number of representative movies to find per cluster
        
    Returns:
        Dict mapping cluster IDs to lists of representative movies
    """
    # We'll need the original embeddings to find central movies
    try:
        from scripts.rag.rag_retrieval import get_movies_collection
        
        collection = get_movies_collection()
        representatives = {}
        
        for cluster_id in sorted(cluster_df['cluster'].unique()):
            # Get movies in this cluster
            cluster_movies = cluster_df[cluster_df['cluster'] == cluster_id]
            
            # Get the IDs of movies in this cluster
            movie_ids = cluster_movies['id'].tolist()
            
            # Retrieve embeddings for these movies
            result = collection.get(
                ids=movie_ids,
                include=["embeddings", "metadatas", "documents"]
            )
            
            if len(result["embeddings"]) == 0:
                representatives[cluster_id] = []
                continue
                
            # Calculate the centroid (average embedding) for this cluster
            centroid = np.mean(result["embeddings"], axis=0)
            
            # Calculate distance of each movie to the centroid
            distances = []
            for i, embedding in enumerate(result["embeddings"]):
                distance = np.linalg.norm(embedding - centroid)
                distances.append((i, distance))
            
            # Sort by distance and get the closest N movies
            distances.sort(key=lambda x: x[1])
            closest_indices = [d[0] for d in distances[:n]]
            
            # Get the representative movies
            rep_movies = []
            for idx in closest_indices:
                if idx < len(result["ids"]):
                    movie_data = {
                        "id": result["ids"][idx],
                        "title": result["metadatas"][idx].get("title", "Unknown"),
                        "type": result["metadatas"][idx].get("type", "Unknown"),
                        "rating": result["metadatas"][idx].get("rating", "Unknown"),
                        "release_year": result["metadatas"][idx].get("release_year", "Unknown"),
                        "description": result["documents"][idx] if idx < len(result["documents"]) else ""
                    }
                    rep_movies.append(movie_data)
            
            representatives[cluster_id] = rep_movies
        
        return representatives
    
    except Exception as e:
        st.error(f"Error finding representative movies: {str(e)}")
        return {}

def display_enhanced_cluster_visualization(cluster_df, color_by="cluster", is_3d=False, insights_df=None, representatives=None):
    """
    Display an enhanced Plotly visualization of movie clusters with insights.
    
    Args:
        cluster_df: DataFrame with clustering information
        color_by: Column to use for coloring points
        is_3d: Whether to use 3D visualization
        insights_df: DataFrame with cluster insights
        representatives: Dict with representative movies for each cluster
    """
    if cluster_df is None or len(cluster_df) == 0:
        st.error("No cluster data available for visualization.")
        return
    
    # Create layout with two columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create and display the scatter plot
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
        
        # If we have cluster insights, add annotations
        if insights_df is not None and color_by == "cluster":
            for _, row in insights_df.iterrows():
                cluster_id = row["cluster_id"]
                label = row["cluster_label"]
                
                # Get the centroid of this cluster
                cluster_points = cluster_df[cluster_df["cluster"] == cluster_id]
                if len(cluster_points) > 0:
                    x_center = cluster_points["x"].mean()
                    y_center = cluster_points["y"].mean()
                    
                    # Add annotation
                    if is_3d:
                        z_center = cluster_points["z"].mean()
                        fig.add_annotation(
                            x=x_center, y=y_center, z=z_center,
                            text=label,
                            showarrow=True,
                            arrowhead=1,
                            font=dict(size=12, color="black", family="Arial Black")
                        )
                    else:
                        fig.add_annotation(
                            x=x_center, y=y_center,
                            text=label,
                            showarrow=True,
                            arrowhead=1,
                            font=dict(size=12, color="black", family="Arial Black")
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
    
    # Display cluster insights in the sidebar
    with col2:
        if insights_df is not None and color_by == "cluster":
            st.markdown("### Cluster Insights")
            
            # Create a selectbox to choose which cluster to view
            cluster_options = [f"Cluster {row['cluster_id']}: {row['cluster_label']}" 
                              for _, row in insights_df.iterrows()]
            
            selected_cluster_option = st.selectbox(
                "Select a cluster to explore",
                cluster_options
            )
            
            # Extract the cluster ID from the selected option
            selected_cluster_id = int(selected_cluster_option.split(":")[0].replace("Cluster ", "").strip())
            
            # Display insights for the selected cluster
            selected_insight = insights_df[insights_df["cluster_id"] == selected_cluster_id].iloc[0]
            
            st.markdown(f"#### {selected_insight['cluster_label']}")
            st.markdown(f"**Movies in cluster:** {selected_insight['movie_count']}")
            
            st.markdown("**Themes:**")
            for theme in selected_insight["themes"]:
                st.markdown(f"- {theme}")
            
            st.markdown("**Keywords:**")
            st.markdown(", ".join(selected_insight["keywords"]))
            
            st.markdown("**Description:**")
            st.markdown(selected_insight["description"])
            
            # Show representative movies if available
            if representatives and selected_cluster_id in representatives:
                st.markdown("#### Representative Movies")
                rep_movies = representatives[selected_cluster_id]
                
                for movie in rep_movies:
                    with st.container():
                        st.markdown(f"**{movie['title']}** ({movie['release_year']})")
                        st.markdown(f"*{movie['type']} • {movie['rating']}*")
                        
                        # Add a button to use this movie in the recommendation system
                        if st.button(f"Find movies like '{movie['title']}'", key=f"btn_{movie['id']}"):
                            # Store this movie title in session state for the RAG system
                            st.session_state.recommendation_seed = movie['title']
                            # Force a rerun to switch to the recommendation tab
                            st.rerun()