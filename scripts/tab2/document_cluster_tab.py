import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.manifold import TSNE
from scripts.rag.rag_BASF import get_document_embeddings, get_document_metadata

def render_document_cluster_tab():
    """
    Renders the Document Clusters tab of the BASF Document Assistant
    """
    st.write("📊 Explore BASF document clusters based on content similarity")
    
    # Create a container for the visualization
    viz_container = st.container()
    
    # Create a container for the controls
    control_container = st.container()
    
    # Use the control container for user inputs
    with control_container:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Number of clusters selection
            num_clusters = st.slider("Number of clusters", min_value=2, max_value=10, value=5)
            
            # Dimension reduction technique
            dim_reduction = st.selectbox(
                "Dimension reduction technique",
                ["t-SNE", "PCA", "UMAP"],
                index=0
            )
            
        with col2:
            # Search for specific documents
            search_query = st.text_input(
                "Search for documents",
                placeholder="Enter keywords to highlight specific documents"
            )
            
            # Apply filters from sidebar
            use_filters = st.checkbox("Apply sidebar filters to visualization")
    
        # Button to generate/refresh visualization
        if st.button("Generate Visualization"):
            with st.spinner("Generating document clusters..."):
                # Get document embeddings and metadata
                embeddings, document_ids = get_document_embeddings()
                metadata = get_document_metadata(document_ids)
                
                # Apply filters if requested
                if use_filters:
                    filtered_indices = filter_documents(metadata)
                    embeddings = embeddings[filtered_indices]
                    filtered_doc_ids = [document_ids[i] for i in filtered_indices]
                    metadata = {doc_id: metadata[doc_id] for doc_id in filtered_doc_ids}
                    document_ids = filtered_doc_ids
                
                # Perform dimensionality reduction
                reduced_data = reduce_dimensions(embeddings, dim_reduction)
                
                # Create DataFrame for visualization
                df = create_visualization_dataframe(reduced_data, metadata, document_ids)
                
                # Apply clustering
                df = apply_clustering(df, num_clusters)
                
                # Highlight search results if query provided
                if search_query:
                    df['highlighted'] = df['title'].str.contains(search_query, case=False) | \
                                      df['type'].str.contains(search_query, case=False) | \
                                      df['department'].str.contains(search_query, case=False)
                else:
                    df['highlighted'] = False
                
                # Store in session state for display
                st.session_state.cluster_df = df
                st.session_state.show_clusters = True
    
    # Use the visualization container to display the clusters
    with viz_container:
        if "show_clusters" in st.session_state and st.session_state.show_clusters:
            display_cluster_visualization(st.session_state.cluster_df)
            
            # Document details on click
            if "selected_document" in st.session_state:
                doc_id = st.session_state.selected_document
                display_document_details(st.session_state.cluster_df, doc_id)

def filter_documents(metadata):
    """
    Apply filters from sidebar to the document metadata
    Returns indices of documents that match the filters
    """
    indices = []
    
    for i, (doc_id, doc_meta) in enumerate(metadata.items()):
        include = True
        
        # Apply rating filter (department)
        if st.session_state.rating_filter != "Any" and doc_meta.get("department") != st.session_state.rating_filter:
            include = False
            
        # Apply year filter
        if st.session_state.year_filter != "Any" and doc_meta.get("year", 0) < int(st.session_state.year_filter):
            include = False
            
        # Apply type filter
        if st.session_state.type_filter != "Any" and doc_meta.get("type") != st.session_state.type_filter:
            include = False
            
        if include:
            indices.append(i)
            
    return indices

def reduce_dimensions(embeddings, method="t-SNE"):
    """
    Reduce dimensions of embeddings for visualization
    """
    if method == "t-SNE":
        reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1) if len(embeddings) > 30 else 5)
        return reducer.fit_transform(embeddings)
    elif method == "PCA":
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=2)
        return reducer.fit_transform(embeddings)
    elif method == "UMAP":
        import umap
        reducer = umap.UMAP(n_components=2, random_state=42)
        return reducer.fit_transform(embeddings)
    
def create_visualization_dataframe(reduced_data, metadata, document_ids):
    """
    Create a DataFrame for visualization with reduced dimensions and metadata
    """
    df = pd.DataFrame(reduced_data, columns=['x', 'y'])
    
    # Add document metadata
    df['id'] = document_ids
    df['title'] = [metadata[doc_id].get('title', f'Document {i}') for i, doc_id in enumerate(document_ids)]
    df['type'] = [metadata[doc_id].get('type', 'Unknown') for doc_id in document_ids]
    df['department'] = [metadata[doc_id].get('department', 'Unknown') for doc_id in document_ids]
    df['year'] = [metadata[doc_id].get('year', 'Unknown') for doc_id in document_ids]
    df['path'] = [metadata[doc_id].get('path', '') for doc_id in document_ids]
    
    return df

def apply_clustering(df, num_clusters):
    """
    Apply clustering to the reduced data
    """
    from sklearn.cluster import KMeans
    
    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    df['cluster'] = kmeans.fit_predict(df[['x', 'y']])
    
    return df

def display_cluster_visualization(df):
    """
    Display the cluster visualization using Plotly
    """
    # Create color map for clusters
    cluster_colors = px.colors.qualitative.Bold
    
    # Create the scatter plot
    fig = go.Figure()
    
    # Add points for each cluster
    for cluster_id in df['cluster'].unique():
        cluster_df = df[df['cluster'] == cluster_id]
        
        # Regular points (not highlighted)
        regular_points = cluster_df[~cluster_df['highlighted']]
        if not regular_points.empty:
            fig.add_trace(go.Scatter(
                x=regular_points['x'],
                y=regular_points['y'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=cluster_colors[cluster_id % len(cluster_colors)],
                    opacity=0.7
                ),
                text=regular_points['title'],
                hoverinfo='text',
                hovertemplate='<b>%{text}</b><br>Type: ' + regular_points['type'] + '<br>Department: ' + regular_points['department'] + '<extra></extra>',
                customdata=regular_points['id'],
                name=f'Cluster {cluster_id + 1}'
            ))
        
        # Highlighted points (from search)
        highlighted_points = cluster_df[cluster_df['highlighted']]
        if not highlighted_points.empty:
            fig.add_trace(go.Scatter(
                x=highlighted_points['x'],
                y=highlighted_points['y'],
                mode='markers',
                marker=dict(
                    size=14,
                    color=cluster_colors[cluster_id % len(cluster_colors)],
                    line=dict(width=2, color='black'),
                    opacity=1.0
                ),
                text=highlighted_points['title'],
                hoverinfo='text',
                hovertemplate='<b>%{text}</b><br>Type: ' + highlighted_points['type'] + '<br>Department: ' + highlighted_points['department'] + '<extra></extra>',
                customdata=highlighted_points['id'],
                name=f'Cluster {cluster_id + 1} (Highlighted)',
                showlegend=False
            ))
    
    # Update layout
    fig.update_layout(
        title="BASF Document Clusters",
        xaxis=dict(title="Dimension 1", showticklabels=False),
        yaxis=dict(title="Dimension 2", showticklabels=False),
        legend_title="Clusters",
        height=600,
        margin=dict(l=20, r=20, t=40, b=20),
        hovermode="closest"
    )
    
    # Add click event
    config = {
        'displayModeBar': True,
        'responsive': True,
    }
    
    # Plot the figure with click event handling
    st.plotly_chart(fig, config=config, use_container_width=True)
    
    # Add callback for click events
    st.markdown("""
    <script>
        const plot = document.querySelector('.js-plotly-plot');
        plot.on('plotly_click', function(data) {
            const docId = data.points[0].customdata;
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: docId
            }, '*');
        });
    </script>
    """, unsafe_allow_html=True)
    
    # Add instructions
    st.caption("Click on a document point to view details")

def display_document_details(df, doc_id):
    """
    Display details for the selected document
    """
    doc_row = df[df['id'] == doc_id].iloc[0]
    
    st.subheader(f"📄 {doc_row['title']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Type:** {doc_row['type']}")
        st.write(f"**Department:** {doc_row['department']}")
    
    with col2:
        st.write(f"**Year:** {doc_row['year']}")
        st.write(f"**Cluster:** {int(doc_row['cluster']) + 1}")
    
    # Create URL for viewing document
    base_url = "http://localhost:8005"
    url_path = doc_row['path']
    if url_path.startswith("/"):
        url_path = url_path[1:]  # Remove leading slash
    
    full_url = f"{base_url}/{url_path}"
    
    # Document preview or link
    st.markdown(f"[View Document]({full_url})", unsafe_allow_html=True)
    
    # Optionally show related documents (from same cluster)
    with st.expander("Show Related Documents"):
        cluster_id = doc_row['cluster']
        related_docs = df[(df['cluster'] == cluster_id) & (df['id'] != doc_id)]
        
        if related_docs.empty:
            st.write("No related documents found in this cluster.")
        else:
            for i, row in related_docs.iterrows():
                st.write(f"- **{row['title']}** ({row['type']}, {row['department']})")