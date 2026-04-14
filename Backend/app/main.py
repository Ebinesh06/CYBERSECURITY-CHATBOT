from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.ai_logic import get_ai_response
from pydantic import BaseModel

app = FastAPI(
    title="CyberAware AI Bot API",
    description="The backend engine for our Cybersecurity Awareness Chatbot",
    version="1.0.0"
)

# Enable CORS so the Angular laptop can talk to this FastAPI laptop
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, we allow all connections
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the CyberAware API",
        "status": "Online",
        "team_lead": "Backend is active!"
    }

# This defines the structure of the data the frontend will send you
class ChatRequest(BaseModel):
    text: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # This calls the AI logic you imported at the top of the file
    response = await get_ai_response(request.text)
    return {"reply": response}
