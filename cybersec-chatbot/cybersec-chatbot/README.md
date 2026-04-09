# CyberGuard — AI Cybersecurity Awareness Chatbot

An AI-powered chatbot that helps users identify phishing, malware, and social
engineering threats. Built with FastAPI, OpenAI, and MongoDB.

## Quick Start

```bash
# 1. Copy and fill in environment variables
cp .env.example .env

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start MongoDB (Docker)
docker run -d -p 27017:27017 --name mongo mongo:7

# 4. Start the API
uvicorn backend.main:app --reload --port 8000

# 5. Open the frontend
open frontend/index.html
# or: python -m http.server 8080 --directory frontend
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/` | Chat with CyberGuard AI |
| GET | `/chat/history/{id}` | Get session history |
| DELETE | `/chat/history/{id}` | Clear session |
| POST | `/analyze/` | Analyse text for threats |
| POST | `/analyze/password` | Check password strength |
| GET | `/health` | Liveness check |

Interactive docs: http://localhost:8000/docs

## Running Tests

```bash
pytest backend/tests/ -v
```

## Architecture

```
Frontend (HTML/CSS/JS)
        │ REST
FastAPI Gateway  (main.py + routers/)
        │
   ┌────┴─────────┐
Chat      Threat     Password
Service   Service    Service
   │         │
OpenAI     Keywords
GPT API    + GPT       MongoDB
```

## Production Checklist

- [ ] Set strong `SECRET_KEY` in `.env`
- [ ] Set `APP_ENV=production`
- [ ] Enable MongoDB authentication
- [ ] Put API behind Nginx reverse proxy
- [ ] Add JWT authentication to routes
- [ ] Set up log aggregation (Datadog / CloudWatch)
- [ ] Configure Redis for caching repeat threat lookups
- [ ] Add rate limiting per user (not just IP)
