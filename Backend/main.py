from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest
import ollama
import chromadb
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
# --- PHASE 3: CONVERSATIONAL MEMORY ---
# This dictionary will store history. Key = session_id, Value = list of messages
chat_history = {}
# 1. Initialize FastAPI app
app = FastAPI()

# 2. Enable CORS so your Frontend can talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Connect to the Native ChromaDB (Phase 1 Upgrade)
# This points to the new folder created by your ingestion script
chroma_client = chromadb.PersistentClient(path="./chroma_db")
intelligence_collection = chroma_client.get_collection(name="cyber_intelligence")
# --- PHASE 2 STARTUP: KEYWORD INDEXING ---

# 1. Pull all existing data from your Native ChromaDB
all_data = intelligence_collection.get()
documents = all_data['documents']
metadatas = all_data['metadatas']

# 2. Build the BM25 Index (The Keyword Brain)
# We lowercase and split the text so it can match exact words like CVE IDs
tokenized_corpus = [doc.lower().split(" ") for doc in documents]
bm25 = BM25Okapi(tokenized_corpus)

# 3. Load the Re-ranker (The Quality Control)
ranker = Ranker()

print(f"SUCCESS: Indexed {len(documents)} vulnerabilities for Precision Search.")
# 4. Define the request structure
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user"  # We added this field
def hybrid_search(query, top_k=10):
    # 1. Vector Search (Semantic)
    vector_results = intelligence_collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    # 2. Keyword Search (BM25)
    tokenized_query = query.lower().split(" ")
    bm25_scores = bm25.get_scores(tokenized_query)
    
    # Create a unified list of results using RRF (Reciprocal Rank Fusion)
    fusion_results = {}
    
    # Process Vector Results (Assign scores based on rank)
    if vector_results['documents'] and vector_results['documents'][0]:
        for i, doc in enumerate(vector_results['documents'][0]):
            fusion_results[doc] = 1 / (i + 60) # RRF constant k=60

    # Process BM25 Results (Merge with Vector scores)
    top_n_bm25 = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    for i, idx in enumerate(top_n_bm25):
        doc = documents[idx]
        score = 1 / (i + 60)
        fusion_results[doc] = fusion_results.get(doc, 0) + score

    # Sort everything by final fusion score
    ranked_docs = sorted(fusion_results.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, score in ranked_docs[:top_k]]
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    sid = request.session_id

    # 1. Initialize session history if it doesn't exist
    if sid not in chat_history:
        chat_history[sid] = []

    # --- PHASE 3: SEARCH BLENDING (The Fix for Context Loss) ---
    # We combine the current question with the last message to keep the CVE context
    search_query = user_message
    if len(chat_history[sid]) > 0:
        last_context = chat_history[sid][-1]["content"]
        search_query = f"{last_context} {user_message}"
    
    # 2. Run Hybrid Search with the blended query
    hybrid_docs = hybrid_search(search_query)

    # 3. Apply FlashRank Re-ranking
    ranker_input = [{"id": i, "text": doc} for i, doc in enumerate(hybrid_docs)]
    rerank_request = RerankRequest(query=search_query, passages=ranker_input)
    reranked_results = ranker.rerank(rerank_request)

    # 4. Build the Context (Top 3 results)
    final_context_list = [res['text'] for res in reranked_results[:3]]
    context = "\n\n".join(final_context_list)

    # 5. Enhanced System Prompt (Forces AI to use provided context)
    system_prompt = (
        "You are an Elite Cybersecurity Analyst. "
        "STRICT RULE: Use the 'Retrieved Intelligence' AND the 'Chat History' to answer. "
        "If the user asks how to fix or remediate, refer to the CVE in history. "
        f"\n\nRetrieved Intelligence:\n{context}"
    )

    # 6. Assemble the Message History for Llama 3
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[sid][-4:]) # Last 2 exchanges
    messages.append({"role": "user", "content": user_message})

    # 7. Call LLaMA 3
    response = ollama.chat(model="llama3", messages=messages)
    bot_response = response['message']['content']

    # 8. Store Interaction in Memory
    chat_history[sid].append({"role": "user", "content": user_message})
    chat_history[sid].append({"role": "assistant", "content": bot_response})

    return {"response": bot_response}