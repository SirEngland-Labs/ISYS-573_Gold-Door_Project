"""FastAPI server — Twilio webhook, Whisper transcription, agent routing."""

import os
import logging
import httpx
import tempfile
from contextlib import asynccontextmanager
from datetime import date as date_type
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

from app.agent import process_message
from app.database import init_db, get_reservations_by_date, get_all_tables, cancel_reservation
from app.security import check_rate_limit, sanitize_input, filter_output

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("restaurant-agent")

# In-memory session store: phone -> {history: [], reservation_state: {}}
sessions: dict[str, dict] = {}

# Max history per session
MAX_HISTORY = 20


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(
    title="Restaurant Reservation Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount chat directory for static files
chat_dir = os.path.join(os.path.dirname(__file__), "..", "chat")
if os.path.exists(chat_dir):
    app.mount("/chat", StaticFiles(directory=chat_dir, html=True), name="chat")


async def transcribe_audio(media_url: str) -> str:
    """Download and transcribe a voice note using OpenAI Whisper API.

    Uses the MiniMax or OpenAI Whisper endpoint for transcription.
    Falls back to empty string if transcription fails.
    """
    try:
        # Download the audio file from Twilio
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                auth=(twilio_sid, twilio_token),
                follow_redirects=True,
            )
            response.raise_for_status()
            audio_bytes = response.content

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Transcribe using OpenAI Whisper API
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )

        # Clean up temp file
        os.unlink(tmp_path)

        return transcript.text.strip()
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""


def get_or_create_session(phone: str) -> dict:
    """Get or create a session for a phone number."""
    if phone not in sessions:
        sessions[phone] = {
            "history": [],
            "reservation_state": {},
        }
    return sessions[phone]


@app.get("/")
async def root():
    """Serve the chat interface."""
    chat_file = os.path.join(os.path.dirname(__file__), "..", "chat", "index.html")
    if os.path.exists(chat_file):
        return FileResponse(chat_file)
    return {"message": "Chat interface not found"}


@app.get("/admin")
async def admin():
    """Serve the admin dashboard."""
    admin_file = os.path.join(os.path.dirname(__file__), "..", "chat", "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    return {"message": "Admin dashboard not found"}


@app.post("/webhook/twilio")
async def twilio_webhook(request: Request):
    """Handle incoming WhatsApp/SMS messages from Twilio.

    Twilio sends form data with:
    - Body: text message content
    - From: sender phone number
    - To: your Twilio number
    - NumMedia: number of media attachments
    - MediaUrl0, MediaContentType0: first media attachment
    """
    form_data = await request.form()

    # Extract message details
    body = form_data.get("Body", "").strip()
    from_number = form_data.get("From", "")
    num_media = int(form_data.get("NumMedia", 0))

    logger.info(f"Incoming from {from_number}: {body[:100]}{'...' if len(body) > 100 else ''}")

    # Handle voice notes / audio
    if num_media > 0:
        media_type = form_data.get("MediaContentType0", "")
        if media_type.startswith("audio/"):
            media_url = form_data.get("MediaUrl0", "")
            transcription = await transcribe_audio(media_url)
            if transcription:
                body = transcription
                logger.info(f"Transcribed voice note: {body[:100]}")
            else:
                # Transcription failed — ask them to type
                twiml = MessagingResponse()
                twiml.message("Sorry, I couldn't understand that voice message. Could you type your message instead?")
                return Response(content=str(twiml), media_type="application/xml")

    # No message content
    if not body:
        twiml = MessagingResponse()
        twiml.message("Hi! I'm the restaurant reservation assistant. I can help you book a table, answer menu questions, or manage your reservations. How can I help?")
        return Response(content=str(twiml), media_type="application/xml")

    # Rate limiting
    if not check_rate_limit(from_number):
        twiml = MessagingResponse()
        twiml.message("You've sent too many messages. Please try again in a few minutes.")
        return Response(content=str(twiml), media_type="application/xml")

    # Sanitize input
    clean_body = sanitize_input(body)

    # Get session
    session = get_or_create_session(from_number)

    # Process through agent
    try:
        response = process_message(
            message=clean_body,
            phone=from_number,
            history=session["history"],
            reservation_state=session["reservation_state"],
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        response = "Sorry, something went wrong. Please try again."

    # Filter output
    response = filter_output(response)

    # Update session history
    session["history"].append(f"Customer: {clean_body}")
    session["history"].append(f"Agent: {response}")

    # Trim history
    if len(session["history"]) > MAX_HISTORY * 2:
        session["history"] = session["history"][-MAX_HISTORY * 2:]

    # Send response via Twilio
    twiml = MessagingResponse()
    twiml.message(response)

    logger.info(f"Response to {from_number}: {response[:100]}{'...' if len(response) > 100 else ''}")

    return Response(content=str(twiml), media_type="application/xml")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "restaurant-reservation-agent"}


@app.post("/api/message")
async def api_message(request: Request):
    """Direct API endpoint for testing (no Twilio).

    Accepts JSON: {"message": "...", "phone": "+1234567890"}
    Returns JSON: {"response": "..."}
    """
    data = await request.json()
    message = data.get("message", "")
    phone = data.get("phone", "test-user")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    clean = sanitize_input(message)
    session = get_or_create_session(phone)

    try:
        response = process_message(
            message=clean,
            phone=phone,
            history=session["history"],
            reservation_state=session["reservation_state"],
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        response = "Sorry, something went wrong. Please try again."

    response = filter_output(response)

    session["history"].append(f"Customer: {clean}")
    session["history"].append(f"Agent: {response}")

    if len(session["history"]) > MAX_HISTORY * 2:
        session["history"] = session["history"][-MAX_HISTORY * 2:]

    return {"response": response}


# Admin API endpoints
def verify_admin_password(request: Request) -> bool:
    """Verify admin password from request header."""
    admin_password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not admin_password:
        logger.warning("DASHBOARD_PASSWORD not set - admin endpoints disabled")
        return False

    password = request.headers.get("X-Admin-Password", "")
    return password == admin_password


@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Verify admin password."""
    data = await request.json()
    password = data.get("password", "")
    admin_password = os.environ.get("DASHBOARD_PASSWORD", "")

    if not admin_password:
        logger.warning("DASHBOARD_PASSWORD not set")
        raise HTTPException(status_code=503, detail="Admin not configured")

    if password == admin_password:
        return {"ok": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


@app.get("/api/admin/reservations")
async def admin_reservations(request: Request, date: str):
    """Get reservations for a specific date."""
    if not verify_admin_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Parse the date string (format: YYYY-MM-DD)
        date_str = date.split("T")[0] if "T" in date else date
        query_date = date_type.fromisoformat(date_str)
        reservations = get_reservations_by_date(query_date)
        return reservations
    except Exception as e:
        logger.error(f"Error fetching reservations: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")


@app.get("/api/admin/tables")
async def admin_tables(request: Request):
    """Get all restaurant tables."""
    if not verify_admin_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        tables = get_all_tables()
        return tables
    except Exception as e:
        logger.error(f"Error fetching tables: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tables")


@app.post("/api/admin/cancel")
async def admin_cancel(request: Request):
    """Cancel a reservation."""
    if not verify_admin_password(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = await request.json()
    reservation_id = data.get("reservation_id")

    if not reservation_id:
        raise HTTPException(status_code=400, detail="reservation_id required")

    try:
        result = cancel_reservation(reservation_id=reservation_id)
        logger.info(f"Admin cancelled reservation {reservation_id}")
        return {"ok": True, "reservation": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling reservation: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel reservation")
