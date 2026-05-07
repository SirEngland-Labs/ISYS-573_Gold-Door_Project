# 🚪 Gold Door Restaurant Reservation Agent

**"Goldie"** An AI-powered conversational agent for restaurant reservations, FAQ, and booking management.

Built for **ISYS 573 · Agentic AI · Track A (Single Agent)**

---

## 📌 What Is This?

Gold Door is a fully containerized AI chatbot that handles restaurant reservations 24/7, with no phone calls required.

Customers can:
- Book tables through a chat interface
- Ask about menu, hours, and policies
- Cancel or look up reservations

Restaurant staff get:
- A password-protected admin dashboard
- Ability to manage bookings by date

---

## ⚙️ Core Features

- 🗣️ Multi-turn reservation booking flow  
- 📚 RAG-powered FAQ system  
- ❌ Reservation cancellation & lookup  
- 📊 Admin dashboard for booking management  

---

## 🧠 Tech Stack

| Layer | Technology |
|------|----------|
| Agent Framework | LangGraph |
| LLM (Primary) | MiniMax M2.7 |
| LLM (Fallback) | Google Gemini Flash |
| Backend | FastAPI |
| RAG | FAISS + sentence-transformers |
| Database | SQLite |
| Frontend | HTML + Vanilla JS |
| Containerization | Docker + docker-compose |

---

## 📁 Project Structure

```
restaurant-agent/
├── app/
│   ├── main.py
│   ├── agent.py
│   ├── database.py
│   ├── models.py
│   ├── security.py
│   ├── nodes/
│   └── tools/
├── chat/
├── knowledge/
├── docs/
├── scripts/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🚀 Quickstart

### 1. Clone the repo
```bash
git clone <repo-url>
cd restaurant-agent
```

### 2. Set up environment variables
```bash
cp .env.example .env
```

Fill in:
```
MINIMAX_API_KEY=your_key
GEMINI_API_KEY=your_key
DASHBOARD_PASSWORD=your_password
```

---

### 3. Run the app
```bash
docker-compose up --build
```

Or:
```bash
bash scripts/start.sh
```

---

### 4. Open in browser

- Customer Chat: http://localhost:8000/
- Admin Dashboard: http://localhost:8000/admin
- Health Check: http://localhost:8000/health

---

## 🌐 Optional: Make It Public

```bash
cloudflared tunnel --url http://localhost:8000
```

---

## ✏️ Updating Restaurant Content

Edit files in the `knowledge/` folder:

| File | Purpose |
|-----|--------|
| menu.md | Menu items |
| hours.md | Operating hours |
| policies.md | Rules & policies |

Then restart:
```bash
docker-compose restart
```

---

## 🧩 Architecture

- Intent-based routing using LangGraph:
  - Reserve Node
  - FAQ Node (RAG)
  - Cancel Node
  - Off-topic handler

---

## 🔒 Security Features

- Input sanitization (prevents prompt injection)
- Rate limiting
- Output filtering (no API key leaks)
- Password-protected admin dashboard
- Docker container isolation

---

## 🧪 Running Tests

```bash
bash scripts/test.sh
```

---

## ⚠️ Troubleshooting

**Agent not responding?**
- Check API keys
- Ensure services are running

**No tables available?**
- Restart the container:
```bash
docker-compose restart
```

**Dashboard password error?**
- Make sure `.env` has:
```
DASHBOARD_PASSWORD=yourpassword
```

---

## 👥 Team

ISYS 573
Gregory England, Parneet Kaur, Alexander Davila, Luis Aguilar

---

## 📜 License

For academic use only.
