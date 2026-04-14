import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Setup the mathematical model (Must match what your AI teammate uses)
# This model turns words into numbers so the computer can 'understand' them
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

async def get_ai_response(user_query: str):
    db_path = "./vector_db"
    
    # 2. Safety Check: If the library folder is missing
    if not os.path.exists(db_path) or not os.listdir(db_path):
        return f"Backend received: '{user_query}'. (Status: Waiting for AI Team to hand over the Vector Database folder)."

    # 3. REAL BRAIN LOGIC: Search the library
    try:
        # Connect to the database folder
        db = Chroma(persist_directory=db_path, embedding_function=embeddings)
        
        # Search for the most similar answer in the library
        docs = db.similarity_search(user_query, k=1)
        
        if docs:
            return docs[0].page_content
        else:
            return "I searched my database but couldn't find an answer to that."
            
    except Exception as e:
        return f"Error connecting to the brain: {str(e)}"