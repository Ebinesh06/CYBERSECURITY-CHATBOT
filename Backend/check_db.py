import chromadb
client = chromadb.PersistentClient(path="./chroma_db") # Use the path from your script
collection = client.get_collection(name="cyber_intelligence")
print(f"Total items in database: {collection.count()}")