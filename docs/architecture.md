# Restaurant Reservation Agent — Architecture

## Overview
AI-powered reservation agent for restaurant bookings. Customers interact via WhatsApp/SMS, staff manage via web dashboard.

## Tech Stack
- **LLM:** MiniMax M2.7
- **Agent Framework:** LangGraph
- **API Server:** FastAPI
- **Customer Channel:** WhatsApp/SMS via Twilio
- **Voice Transcription:** OpenAI Whisper
- **Knowledge Base:** LangChain + FAISS (RAG)
- **Database:** SQLite
- **Admin Dashboard:** Streamlit
- **Container:** Docker (OrbStack runtime)

## Agent Flow
1. Customer sends message (text or voice note) via WhatsApp
2. Twilio webhook hits FastAPI server
3. Voice notes transcribed via Whisper
4. Input sanitized and rate-checked
5. LangGraph agent processes message:
   - Router classifies intent (reservation, FAQ, cancel, out-of-scope)
   - Appropriate node handles the request
   - RAG retrieves menu/hours/policy info as needed
6. Response sent back through Twilio to WhatsApp

## Security
- Intent router restricts agent to reservation-related tasks only
- Input sanitization strips prompt injection attempts
- Rate limiting per phone number
- Output filtering blocks system info leakage
- Container runs with read-only knowledge mount
- Dashboard protected by password auth
