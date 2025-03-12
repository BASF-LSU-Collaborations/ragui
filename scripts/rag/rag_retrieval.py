import os
import openai
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="netflix_movies")

### 🔹 STEP 1: Rephrase the Question Using Chat History
def rephrase_question(user_question: str, chat_history: list[str]) -> str:
    """Rephrase the question to make it self-contained, using chat history."""
    
    # Convert chat history into a text block, but keep only relevant exchanges
    relevant_history = "\n".join(chat_history)  # Use full history instead of just last 3

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that ensures questions are rephrased clearly with full context."},
            {"role": "user", "content": f"Conversation history:\n{relevant_history}\n\nRephrase this question so that it fully references any missing subjects: '{user_question}'"}
        ],
        temperature=0.3,
        max_tokens=50
    )

    return response.choices[0].message.content.strip()


### 🔹 STEP 2: Retrieve Relevant Movies from ChromaDB
def get_embedding(text: str) -> list[float]:
    """Generate embedding using OpenAI's latest embedding model."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[text]
    )
    return response.data[0].embedding

def retrieve_movies(query: str, top_n: int = 5, filter_params: dict = None) -> list[dict]:
    """Get top N relevant movies from ChromaDB.
    
    Args:
        query: The user's movie request/preference
        top_n: Number of movies to retrieve
        filter_params: Optional filters like {'rating': 'PG-13', 'release_year': {'gt': 2015}}
    """
    q_embedding = get_embedding(query)
    
    # ChromaDB requires a specific filter structure
    # The correct format is {"$and": [{"field1": value1}, {"field2": {"$gt": value2}}]}
    where_clause = None
    if filter_params:
        conditions = []
        for key, value in filter_params.items():
            if isinstance(value, dict) and key == 'release_year':
                # Handle range comparisons for release_year
                for op, val in value.items():
                    if op == 'gt':
                        conditions.append({key: {"$gt": val}})
                    elif op == 'lt':
                        conditions.append({key: {"$lt": val}})
                    elif op == 'gte':
                        conditions.append({key: {"$gte": val}})
                    elif op == 'lte':
                        conditions.append({key: {"$lte": val}})
            else:
                conditions.append({key: value})
        
        # Use $and to combine multiple conditions
        if len(conditions) > 1:
            where_clause = {"$and": conditions}
        elif len(conditions) == 1:
            where_clause = conditions[0]
    
    # Query the database
    try:
        results = collection.query(
            query_embeddings=[q_embedding],
            where=where_clause,
            n_results=top_n,
            include=["metadatas", "documents", "distances"]
        )
    except Exception as e:
        print(f"Error querying database: {str(e)}")
        # Try without filters as fallback
        if where_clause:
            print("Trying query without filters...")
            results = collection.query(
                query_embeddings=[q_embedding],
                n_results=top_n,
                include=["metadatas", "documents", "distances"]
            )
        else:
            raise e
    
    # Format results into a more usable structure
    movies = []
    for i, movie_id in enumerate(results["ids"][0]):
        movies.append({
            "id": movie_id,
            "title": results["metadatas"][0][i]["title"],
            "type": results["metadatas"][0][i]["type"],
            "release_year": results["metadatas"][0][i]["release_year"],
            "rating": results["metadatas"][0][i]["rating"],
            "description": results["documents"][0][i],
            "similarity_score": results["distances"][0][i]
        })
    
    return movies

### 🔹 STEP 3: Generate Movie Recommendations Using OpenAI
def generate_movie_recommendations(query: str, movies: list[dict], purpose: str = "recommendation") -> str:
    """Generate personalized movie recommendations based on retrieved movies.
    
    Args:
        query: The user's original or rephrased query
        movies: List of retrieved movie dictionaries
        purpose: 'recommendation' or 'search' to adjust response format
    """
    
    # Format movies as text for GPT
    movie_block = ""
    for i, movie in enumerate(movies, 1):
        movie_block += f"{i}. {movie['title']} ({movie['release_year']}) - {movie['rating']} - {movie['type']}\n"
        movie_block += f"   Description: {movie['description']}\n"
        movie_block += f"   Similarity score: {movie['similarity_score']}\n\n"
    
    system_message = """You are a helpful movie recommendation assistant. 
Provide personalized, thoughtful recommendations explaining why each movie matches the user's preferences.
Focus on content, themes, and mood rather than just genre matches."""

    prompt = f"""
Based on the user's request: "{query}"

I've found these potentially relevant movies:

{movie_block}

"""
    
    if purpose == "recommendation":
        prompt += "Please recommend 2-3 of these movies that best match the user's preferences. Explain why each recommendation fits what they're looking for."
    else:  # search
        prompt += "Please analyze these search results and help the user understand which movies best match their query and why."
    
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

### 🔹 STEP 4: Full Movie RAG Function
def movie_rag(user_request: str, chat_history: list[str], filters: dict = None, purpose: str = "recommendation") -> str:
    """
    1. Rephrases the user's movie request using chat history.
    2. Retrieves relevant movies from ChromaDB.
    3. Generates personalized recommendations.
    """
    
    # 1️⃣ Rephrase request to include chat history context
    rephrased = rephrase_question(user_request, chat_history)
    print(f"Rephrased query: {rephrased}")

    # 2️⃣ Retrieve top matching movies from ChromaDB
    matching_movies = retrieve_movies(rephrased, top_n=5, filter_params=filters)
    
    if not matching_movies:
        return "I couldn't find any movies matching your criteria. Can you try with different preferences or fewer restrictions?"

    # 3️⃣ Generate personalized recommendations
    recommendations = generate_movie_recommendations(rephrased, matching_movies, purpose)

    return recommendations

### 🔹 TESTING THE MOVIE RAG SYSTEM
if __name__ == "__main__":
    conversation_history = [
        "Hello, I'd like to find a movie to watch tonight.",
        "What kind of movies do you enjoy?",
        "I usually like action movies."
    ]
    
    # Example 1: Basic recommendation
    user_request = "Something with a lot of suspense"
    
    print("\n🎬 User Request:", user_request)
    recommendation = movie_rag(user_request, conversation_history)
    print("🎬 Recommendations:", recommendation)
    
    # Example 2: With filters - FIXED
    user_request = "A family-friendly movie"
    filters = {
        "rating": "PG",
        "release_year": {"gt": 2015}
    }
    
    print("\n🎬 User Request:", user_request)
    print("🎬 Filters:", filters)
    recommendation = movie_rag(user_request, conversation_history, filters)
    print("🎬 Recommendations:", recommendation)