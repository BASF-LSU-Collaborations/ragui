import chromadb
from chromadb.config import Settings

# Path to your ChromaDB directory
CHROMA_DB_PATH = "/shared_folders/team_1/austin/chroma_db"

# Connect to the ChromaDB client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# List and print all collection names
collections = client.list_collections()
print(f"\n🔍 Found {len(collections)} collection(s):\n")

for col_name in collections:
    print(f"📁 Collection: {col_name}")

    # Access the collection
    collection = client.get_collection(name=col_name)

    # Query the first few documents (n_results can be changed)
    try:
        results = collection.query(query_texts=["Show me documents"], n_results=5)

        docs = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if docs:
            print("📝 Sample documents:\n")
            for idx, doc in enumerate(docs):
                print(f"  {idx + 1}. 🆔 ID: {ids[idx]}")
                print(f"     📎 Metadata: {metadatas[idx] if idx < len(metadatas) else 'None'}")
                print(f"     📄 Content: {doc[:500]}{'...' if len(doc) > 500 else ''}\n")
        else:
            print("⚠️  No documents found in this collection.")

    except Exception as e:
        print(f"❌ Error querying collection '{col_name}': {e}")

    print("\n" + "-" * 60 + "\n")
