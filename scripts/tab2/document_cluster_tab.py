# scripts/tab2/document_cluster_tab.py
import streamlit as st
import pandas as pd
import numpy as np
import ast  # For safely evaluating string representations of lists
import time # To measure execution time
import sys
import os
import warnings
import re # For case-insensitive search

# --- Plotly and Scikit-learn ---
try:
    import plotly.express as px
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from sklearn.manifold import TSNE
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# --- Database ---
from sqlalchemy import text

# --- Configuration ---
# Adjust this path to point to your VDB pipeline location
# It needs to be accessible from where Streamlit runs
# Consider using environment variables or relative paths for better deployment
VDB_PIPELINE_PATH = "/shared_folders/team_1/mark_vdb/vdb_pipeline" #<-- ADJUST IF NEEDED
EXPECTED_DIMENSION = 384 # Should match the embedding dimension
RANDOM_STATE = 42 # For reproducible t-SNE results
# t-SNE Parameters
TSNE_PERPLEXITY = 30
TSNE_ITERATIONS = 300 # Number of optimization iterations
TSNE_COMPONENTS = 2   # 2 for 2D plot, 3 for 3D

# --- Add VDB pipeline to Python path ---
# Ensure the path is correct relative to the Streamlit script's execution location
if VDB_PIPELINE_PATH not in sys.path:
    # Using absolute path; consider alternatives for portability
    sys.path.append(VDB_PIPELINE_PATH)
    print(f"Appended to sys.path: {VDB_PIPELINE_PATH}") # For debugging

# --- Import database initializer ---
try:
    from init_vector_db import init_vector_db
    INIT_DB_AVAILABLE = True
    print("Successfully imported init_vector_db.") # For debugging
except ImportError as e:
    # Display error prominently in Streamlit if import fails
    # Use a placeholder function to avoid crashing if import fails later
    INIT_DB_AVAILABLE = False
    def init_vector_db(wipe_database=False):
        st.error(f"Fatal Error: Failed to import database connection module (init_vector_db). "
                 f"Check VDB_PIPELINE_PATH: '{VDB_PIPELINE_PATH}'. Error: {e}")
        return None, None
    print(f"Failed to import init_vector_db: {e}") # Log error


# --- Helper function to parse embeddings ---
def parse_embedding(embedding_raw):
    """Safely parses string representation of embedding list."""
    if isinstance(embedding_raw, str):
        try:
            # Use ast.literal_eval for safe evaluation of '[num1, num2,...]' format
            parsed = ast.literal_eval(embedding_raw)
            if isinstance(parsed, list) and len(parsed) == EXPECTED_DIMENSION:
                return parsed
            else:
                return None
        except (ValueError, SyntaxError):
            return None
    elif isinstance(embedding_raw, (list, np.ndarray)): # Handle if already parsed somehow
         if len(embedding_raw) == EXPECTED_DIMENSION:
             return list(embedding_raw) # Ensure list format if numpy array
         else:
             return None
    else:
        return None

# --- Cached data loading and processing function ---
# Use st.cache_data for caching results. It reruns if the function code changes.
@st.cache_data(show_spinner="Loading and processing cluster data...")
def load_and_process_data_for_viz():
    """
    Connects to DB, fetches data, parses embeddings, and performs t-SNE.
    Returns a DataFrame ready for plotting.
    """
    if not INIT_DB_AVAILABLE:
        return None

    session = None
    engine = None
    df_processed = pd.DataFrame()
    embedding_matrix = None
    print("Attempting to load and process data...") # Debugging

    try:
        # --- 1) Connect and Fetch Data ---
        connect_start = time.time()
        session, engine = init_vector_db(wipe_database=False)
        # Handle connection failure from placeholder
        if engine is None:
             # Error is displayed by init_vector_db placeholder
             return None
        print(f"DB Connection time: {time.time() - connect_start:.2f}s")

        fetch_start = time.time()
        query_select = text("""
            SELECT doc_id, embedding, cluster_id, cluster_name, summary
            FROM public.summary_vectors
            WHERE embedding IS NOT NULL AND cluster_name IS NOT NULL;
        """)
        df_plot = pd.read_sql(query_select, con=engine)
        print(f"Fetched {len(df_plot)} records. Fetch time: {time.time() - fetch_start:.2f}s")

        if df_plot.empty:
            warnings.warn("No data found with embeddings and cluster names in the database.")
            return None

        # --- 2) Parse Embeddings ---
        parse_start = time.time()
        df_plot['parsed_embedding'] = df_plot['embedding'].apply(parse_embedding)
        initial_rows = len(df_plot)
        df_processed = df_plot.dropna(subset=['parsed_embedding']).copy()
        parsed_rows = len(df_processed)
        if initial_rows > parsed_rows:
             warnings.warn(f"Dropped {initial_rows - parsed_rows} rows due to embedding parsing errors.")
        if df_processed.empty:
             warnings.warn("No valid embeddings could be parsed after filtering. Cannot visualize.")
             return None
        embedding_matrix = np.array(df_processed['parsed_embedding'].tolist())
        print(f"Parsed {parsed_rows} embeddings. Shape: {embedding_matrix.shape}. Parse time: {time.time() - parse_start:.2f}s")

        # --- 3) Perform t-SNE ---
        if not SKLEARN_AVAILABLE:
             warnings.warn("Scikit-learn (TSNE) not available. Cannot perform dimensionality reduction.")
             return None
        tsne_start = time.time()
        print(f"Performing t-SNE on {len(df_processed)} points...")
        tsne = TSNE(n_components=TSNE_COMPONENTS, perplexity=TSNE_PERPLEXITY, n_iter=TSNE_ITERATIONS,
                    random_state=RANDOM_STATE, metric='cosine', n_jobs=-1)
        tsne_results = tsne.fit_transform(embedding_matrix)
        print(f"t-SNE finished. Time: {time.time() - tsne_start:.2f}s")

        df_processed['tsne_1'] = tsne_results[:, 0]
        df_processed['tsne_2'] = tsne_results[:, 1]
        if TSNE_COMPONENTS == 3:
            df_processed['tsne_3'] = tsne_results[:, 2]

        # Add summary preview here before returning
        df_processed['summary_preview'] = df_processed['summary'].str[:150] + '...'

        return df_processed

    except Exception as e:
        print(f"Error during data loading/processing: {e}")
        warnings.warn(f"An error occurred during data loading or processing: {str(e)}")
        return None
    finally:
        if session:
            session.close()
            print("DB session closed.")


# --- Main rendering function for the tab ---
def render_document_cluster_tab():
    """Renders the Document Cluster Map tab in Streamlit."""
    st.header("Document Cluster Map (t-SNE Visualization)")

    # Check for dependencies
    if not INIT_DB_AVAILABLE:
        # Error already shown by placeholder init_vector_db
        return
    if not SKLEARN_AVAILABLE:
        st.error("Scikit-learn library is missing (`pip install scikit-learn`). Cannot perform t-SNE.")
        return
    if not PLOTLY_AVAILABLE:
        st.error("Plotly library is missing (`pip install plotly`). Cannot display plot.")
        return

    st.markdown("""
        Visualize documents clustered by semantic similarity. Search within summaries
        to highlight relevant documents on the map.
    """)

    # --- Search Input ---
    search_term = st.text_input("Search summaries to highlight:", key="cluster_search")

    # Load data (potentially cached) and perform t-SNE
    df_viz_data = load_and_process_data_for_viz()

    if df_viz_data is not None and not df_viz_data.empty:
        try:
            # --- Filter based on search term ---
            highlighted_docs = pd.Series(False, index=df_viz_data.index) # Default: nothing highlighted
            num_found = 0 # Initialize count
            if search_term:
                # Case-insensitive search within the 'summary' column
                search_regex = re.compile(re.escape(search_term), re.IGNORECASE)
                # Create a boolean series indicating matches
                highlighted_docs = df_viz_data['summary'].apply(lambda x: bool(search_regex.search(x)) if pd.notnull(x) else False)
                num_found = highlighted_docs.sum()
                st.info(f"Found {num_found} documents matching '{search_term}'. Highlighting on plot.")
            else:
                 st.info("Enter a search term to highlight documents.")


            # --- Create Interactive Plot ---
            plot_start = time.time()
            st.write(f"Generating plot for {len(df_viz_data)} documents...")

            # Ensure cluster_name is treated as a category for consistent coloring
            df_viz_data['cluster_name'] = df_viz_data['cluster_name'].astype('category')

            # --- Define appearance based on search ---
            # Size: Smaller overall, larger for highlighted docs
            sizes = np.where(highlighted_docs, 6, 3).tolist() # <<< REDUCED SIZES (e.g., 6 and 3)
            # Opacity: Lower for non-highlighted docs
            opacities = np.where(highlighted_docs, 0.9, 0.4).tolist() # <<< Slightly higher base opacity

            plot_params = {
                'data_frame': df_viz_data,
                'x': 'tsne_1',
                'y': 'tsne_2',
                'color': 'cluster_name', # Color by cluster name
                'size': sizes,          # Use calculated sizes
                'opacity': opacities,   # Use calculated opacities
                'hover_data': ['doc_id', 'summary_preview', 'cluster_name', 'cluster_id'],
                'title': f'Document Clusters (Highlighting: {search_term if search_term else "None"})',
                'labels': {'tsne_1': 't-SNE Dimension 1', 'tsne_2': 't-SNE Dimension 2', 'cluster_name': 'Cluster Name'},
                'category_orders': {"cluster_name": sorted(df_viz_data['cluster_name'].unique())}
            }

            if TSNE_COMPONENTS == 3 and 'tsne_3' in df_viz_data.columns:
                plot_params['z'] = 'tsne_3'
                plot_params['labels']['tsne_3'] = 't-SNE Dimension 3'
                fig = px.scatter_3d(**plot_params)
            else:
                fig = px.scatter(**plot_params)

            # Update layout and marker appearance (size/opacity now set directly in px.scatter)
            fig.update_layout(
                margin=dict(l=0, r=0, b=0, t=40),
                legend_title_text='Cluster Name',
            )

            # Display the plot in Streamlit
            st.plotly_chart(fig, use_container_width=True)
            print(f"Plot generation time: {time.time() - plot_start:.2f}s")

            # --- Optional: Display Cluster Info ---
            with st.expander("View Cluster Details"):
                cluster_counts = df_viz_data['cluster_name'].value_counts().sort_index()
                st.write("Document Count per Cluster:")
                st.dataframe(cluster_counts)

            # --- Optional: Show Search Results List ---
            if search_term and num_found > 0:
                 with st.expander(f"View {num_found} Search Results for '{search_term}'", expanded=False):
                     # Display matching documents
                     st.dataframe(df_viz_data.loc[highlighted_docs, ['doc_id', 'cluster_name', 'summary_preview']])


        except Exception as e:
            st.error(f"An error occurred during plot generation: {str(e)}")
            st.exception(e)

    elif df_viz_data is None:
         # This message is shown if data loading failed
         st.warning("Could not load or process data for visualization. Please check database connection and data integrity.")
    else: # df_viz_data is empty
         st.warning("No documents found in the database matching the criteria (embedding and cluster name not NULL).")


# Example of how this might be called in your main Streamlit app
# if __name__ == "__main__":
#     # Set page config (optional, do this once at the start of your app)
#     # st.set_page_config(layout="wide")
#     render_document_cluster_tab()

