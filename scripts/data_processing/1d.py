import chromadb
import json
import pprint

# Connect to the ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Get all collections (in v0.6.0, this returns a list of strings)
collection_names = chroma_client.list_collections()
print(f"\n=== ChromaDB Collections ===")
for idx, name in enumerate(collection_names):
    print(f"{idx+1}. {name}")

# Try to get the Netflix movies collection
try:
    collection = chroma_client.get_collection("netflix_movies")
    print(f"\n=== 'netflix_movies' Collection Stats ===")
    print(f"Total items: {collection.count()}")
    
    # Peek at the data (first 5 items)
    print(f"\n=== Sample Data (First 5 Items) ===")
    results = collection.peek(limit=5)
    
    # Print IDs
    print("\n--- IDs ---")
    print(results['ids'])
    
    # Print metadata for each item
    print("\n--- Metadata ---")
    for i, metadata in enumerate(results['metadatas']):
        print(f"\nItem {i+1} ({results['ids'][i]}):")
        pprint.pprint(metadata)
    
    # Print documents (movie descriptions)
    print("\n--- Documents ---")
    for i, doc in enumerate(results['documents']):
        print(f"\nDocument {i+1} ({results['ids'][i]}):")
        # Print first 200 chars of each document
        print(f"{doc[:200]}..." if len(doc) > 200 else doc)
    
    # Print embedding dimensions
    print("\n--- Embeddings ---")
    embeddings = results['embeddings']
    if embeddings:
        print(f"Embedding dimensions: {len(embeddings[0])}")
        print(f"First few values of first embedding: {embeddings[0][:5]}...")
    
    # Optional: Save a complete dump of one item to a file for inspection
    first_item = {
        'id': results['ids'][0],
        'metadata': results['metadatas'][0],
        'document': results['documents'][0],
        'embedding': results['embeddings'][0]
    }
    
    with open('chromadb_sample_item.json', 'w') as f:
        # Convert float32 values to regular floats for JSON serialization
        first_item['embedding'] = [float(x) for x in first_item['embedding']]
        json.dump(first_item, f, indent=2)
    
    print(f"\nSaved complete first item to 'chromadb_sample_item.json' for detailed inspection")
    
except ValueError as e:
    print(f"\nError accessing 'netflix_movies' collection: {str(e)}")
    print("The collection might not exist yet. Run the 1c script first.")
    
    # If the netflix_movies collection doesn't exist, but other collections do
    if collection_names:
        try:
            other_name = collection_names[0]
            print(f"\nTrying to display information from '{other_name}' collection instead:")
            other_collection = chroma_client.get_collection(other_name)
            peek_results = other_collection.peek(limit=3)
            print(f"Sample IDs: {peek_results['ids']}")
        except Exception as e:
            print(f"Error accessing other collection: {str(e)}")