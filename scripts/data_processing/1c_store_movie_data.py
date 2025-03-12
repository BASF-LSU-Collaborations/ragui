import json
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables from .env
load_dotenv()

# Get project root directory (two levels up from this script)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DATA_DIR = os.path.join(ROOT_DIR, "data")
CHROMA_DB_DIR = os.path.join(ROOT_DIR, "chroma_db")

# Ensure ChromaDB directory exists
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# Get OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("⚠ OpenAI API key is missing! Ensure it is set in the '.env' file.")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)
embed_model = "text-embedding-3-small"

# Load movie descriptions
descriptions_path = os.path.join(DATA_DIR, "movie_descriptions.json")
metadata_path = os.path.join(DATA_DIR, "movie_metadata.json")

if not os.path.exists(descriptions_path) or not os.path.exists(metadata_path):
    raise FileNotFoundError("⚠ Required dataset files are missing. Ensure 'movie_descriptions.json' and 'movie_metadata.json' exist.")

with open(descriptions_path, "r") as file:
    descriptions = json.load(file)

with open(metadata_path, "r") as file:
    metadata = json.load(file)

print(f"✅ Loaded {len(descriptions)} movie descriptions.")

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name="netflix_movies")
print("✅ ChromaDB initialized and collection created.")

def get_embedding(text):
    """Fetch an embedding for a given text using OpenAI."""
    response = client.embeddings.create(model=embed_model, input=text)
    return response.data[0].embedding

# Process in batches to avoid API rate limits
BATCH_SIZE = 100

# Store movie descriptions and metadata in ChromaDB
for i in tqdm(range(0, len(descriptions), BATCH_SIZE), desc="🔄 Processing batches"):
    batch_descriptions = descriptions[i:i+BATCH_SIZE]
    batch_metadata = metadata[i:i+BATCH_SIZE]
    batch_ids = [data["id"] for data in batch_metadata]

    # Generate embeddings for the batch
    batch_embeddings = [get_embedding(desc) for desc in batch_descriptions]

    # Add to ChromaDB
    collection.add(
        ids=batch_ids,
        embeddings=batch_embeddings,
        metadatas=batch_metadata,
        documents=batch_descriptions
    )

print("✅ Successfully stored all movie data in ChromaDB!")

# Create a simple search function to test
def search_movies(query, n_results=5):
    """Search movies based on query similarity using embeddings."""
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results

print("\n🔍 Testing search functionality with a sample query...")
results = search_movies("comedy about family")
print("Sample search results for 'comedy about family':")

if results and "ids" in results and results["ids"]:
    for i, (movie_id, distance) in enumerate(zip(results["ids"][0], results["distances"][0])):
        metadata = results["metadatas"][0][i]
        description = results["documents"][0][i]
        print(f"{i+1}. {metadata['title']} ({metadata['release_year']}) - {metadata['rating']}")
        print(f"   🔹 Similarity score: {distance:.4f}")
        print(f"   📝 Description: {description[:100]}...\n")
else:
    print("⚠ No relevant results found.")
