# /home/jonathan_morse/ragui/scripts/rag/rag_BASF.py
import os
import json
import openai
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import urllib.parse

# Set up the embedding function with a 384-dim model.
MODEL_NAME = "all-MiniLM-L6-v2"
embedding_function = SentenceTransformer(MODEL_NAME)

# Load API keys from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Use the absolute path to your ChromaDB directory
CHROMA_DB_PATH = "/shared_folders/team_1/austin/chroma_db"

# Initialize ChromaDB; point to your markdown_documents collection
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_collection(name="markdown_documents")

# Load the JSON mapping file that contains file_path -> real_path mappings.
STORE_JSON_PATH = "/shared_folders/team_1/colton_bruni/store_clean_test.json"
with open(STORE_JSON_PATH, "r") as f:
    store_data = json.load(f)


### 🔹 STEP 1: Rephrase the Technical Query Using Chat History
def rephrase_question(user_question: str, chat_history: list[str]) -> str:
    """
    Rephrase the question to make it self-contained, incorporating the chat history.
    This ensures the technical query fully references any missing context.
    """
    relevant_history = "\n".join(chat_history)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that rephrases technical queries to include all necessary context, especially for chemical engineering and BASF documentation."},
            {"role": "user", "content": f"Conversation history:\n{relevant_history}\n\nRephrase this technical question so that it fully references any missing subjects: '{user_question}'"}
        ],
        temperature=0.3,
        max_tokens=50
    )
    return response.choices[0].message.content.strip()


### 🔹 STEP 2: Retrieve Relevant Document Chunks from ChromaDB
def get_embedding(text: str) -> list[float]:
    # Use the SentenceTransformer to encode the text
    embedding = embedding_function.encode(text)
    return embedding.tolist()  # Ensure it's a list


def retrieve_documents(query: str, top_n: int = 5, filter_params: dict = None) -> list[dict]:
    """
    Retrieve the top N relevant document chunks from the markdown_documents collection.
    
    Each returned entry represents a chunk from a BASF/chemical engineering document,
    and includes the associated source file reference along with its actual location.
    """
    q_embedding = get_embedding(query)
    
    # Optionally filter by metadata (e.g., by source_file)
    where_clause = None
    if filter_params:
        conditions = []
        for key, value in filter_params.items():
            conditions.append({key: value})
        if len(conditions) == 1:
            where_clause = conditions[0]
        elif conditions:
            where_clause = {"$and": conditions}
    
    try:
        results = collection.query(
            query_embeddings=[q_embedding],
            where=where_clause,
            n_results=top_n,
            include=["metadatas", "documents", "distances"]
        )
    except Exception as e:
        print(f"Error querying database: {str(e)}")
        if where_clause:
            print("Trying query without filters...")
            results = collection.query(
                query_embeddings=[q_embedding],
                n_results=top_n,
                include=["metadatas", "documents", "distances"]
            )
        else:
            raise e
    
    # Format results: Each document chunk is referenced by its source file (from metadata)
    documents = []
    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        source_file = meta.get("source_file", "Unknown")
        
        # Attempt to find a matching entry in the JSON mapping file.
        real_path = None
        if source_file != "Unknown":
            for entry in store_data.values():
                # If the 'file_path' ends with the source_file name, we consider it a match.
                if "file_path" in entry and entry["file_path"].endswith(source_file):
                    real_path = entry.get("real_path")
                    break
        
        documents.append({
            "id": doc_id,
            "source_file": source_file,
            "real_path": real_path,
            "chunk_text": results["documents"][0][i],
            "similarity_score": results["distances"][0][i]
        })
    
    return documents


### 🔹 STEP 3: Generate a Technical Response Using OpenAI
def generate_document_response(query: str, documents: list[dict], purpose: str = "summary") -> str:
    """
    Generate a response based on the retrieved document chunks.
    The response will include only the source file references (without clickable links)
    along with a brief excerpt of the document chunk and the similarity score.
    """
    doc_block = ""
    for i, doc in enumerate(documents, 1):
        # Only include the source file without clickable link formatting.
        doc_block += f"{i}. Source File: {doc['source_file']}\n"
        doc_block += f"   Chunk Text: {doc['chunk_text'][:300]}{'...' if len(doc['chunk_text']) > 300 else ''}\n"
        doc_block += f"   Similarity Score: {doc['similarity_score']}\n\n"
    
    system_message = (
        "You are an expert assistant in BASF and chemical engineering documentation. "
        "When providing answers, reference the source files. "
        "Focus on technical accuracy and clarity."
    )
    
    prompt = f"""
User Query: "{query}"

I have retrieved the following document chunks from our BASF/chemical engineering collection:
{doc_block}

Based on the above documents, please provide a concise and accurate technical response that references the source files.
"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content.strip()


### 🔹 STEP 4: Full Document RAG Function
def document_rag(user_request: str, chat_history: list[str], filters: dict = None, purpose: str = "summary") -> tuple[str, dict]:
    """
    1. Rephrase the user's technical query using chat history.
    2. Retrieve relevant document chunks from the markdown_documents collection.
    3. Generate a technical response that references the source files and their actual file paths.
    4. Return the response along with a dictionary of unique source files and their real paths.
    """
    rephrased = rephrase_question(user_request, chat_history)
    print(f"Rephrased query: {rephrased}")
    
    matching_documents = retrieve_documents(rephrased, top_n=5, filter_params=filters)
    
    if not matching_documents:
        return ("I couldn't find any relevant information. Please try rephrasing your query or broadening the search.", {})
    
    response = generate_document_response(rephrased, matching_documents, purpose)
    
    # --- New Block: Collect Unique Source Files and Their Real Paths ---
    unique_sources = {}
    for doc in matching_documents:
        source_file = doc.get("source_file", "Unknown")
        real_path = doc.get("real_path", "Not Available")
        if source_file not in unique_sources:
            # Ensure the real path has a leading slash
            if real_path != "Not Available" and not real_path.startswith("/"):
                real_path = "/" + real_path
            unique_sources[source_file] = real_path
    # ----------------------------------------------------------------
    
    return response, unique_sources



### 🔹 TESTING THE DOCUMENT RAG SYSTEM
if __name__ == "__main__":
    conversation_history = [
        "Hi, I'm reviewing our chemical engineering documentation for BASF.",
        "I'm particularly interested in how our latest reactor design uses catalysts."
    ]
    
    # Example: A technical query
    user_request = "Explain the catalytic process used in our latest reactor design."
    
    print("\n🧪 User Request:", user_request)
    answer = document_rag(user_request, conversation_history)
    print("\n🧪 Generated Response:\n", answer)
