from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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