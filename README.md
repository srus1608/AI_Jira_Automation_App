# AI Ticket Automation System

An intelligent support ticket management system that uses **Groq AI (LLaMA 3)** to automatically classify, prioritize, and assign tickets — with **real-time Jira integration** and a **Streamlit analytics dashboard**.

> **End-to-end flow:** User describes an issue → AI classifies it → Jira issue auto-created → Stored in MongoDB → Dashboard visualizes everything

---

## Key Features

| Feature | Description |
|---------|-------------|
| **AI Classification** | Automatically categorizes tickets as Bug / Feature / Incident |
| **Smart Prioritization** | Assigns P0 (Critical) through P3 (Low) based on description |
| **AI Fix Suggestions** | Generates actionable fix recommendations for each ticket |
| **Duplicate Detection** | AI compares new tickets against existing ones to flag duplicates |
| **SLA Prediction** | Auto-calculates deadlines: P0=4h, P1=24h, P2=72h, P3=168h |
| **Auto-Assignment** | Assigns to team member with the lowest workload |
| **Ticket Comments** | Add comments with AI-powered conversation summaries |
| **Jira Integration** | Auto-creates Jira issues and syncs status updates |
| **Streamlit Dashboard** | Visual analytics with charts, filters, and ticket management |
| **Analytics API** | Stats by priority, type, status, team, SLA breaches |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | FastAPI |
| AI Provider | Groq (LLaMA 3 / Gemma 2 / Mixtral) |
| Database | MongoDB |
| Issue Tracker | Jira Cloud (REST API v3) |
| Dashboard | Streamlit |
| Language | Python 3.12+ |

---

## Architecture

```
                         ┌─────────────────────┐
                         │   Streamlit Dashboard │
                         │   (localhost:8501)    │
                         └──────────┬───────────┘
                                    │ HTTP
                                    ▼
┌──────────┐  POST   ┌──────────────────────┐  API Call  ┌──────────┐
│  User /  │────────▶│   FastAPI Server      │──────────▶│ Groq AI  │
│  Client  │         │   (localhost:8000)    │◀──────────│ (LLaMA3) │
└──────────┘         └──────────┬───────────┘  JSON      └──────────┘
                          │           │
                    Save  │           │  Create Issue
                          ▼           ▼
                   ┌──────────┐  ┌──────────┐
                   │ MongoDB  │  │  Jira    │
                   │ Database │  │  Cloud   │
                   └──────────┘  └──────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- MongoDB running locally or on Atlas
- Free [Groq API key](https://console.groq.com/)
- (Optional) Free [Jira Cloud account](https://www.atlassian.com/software/jira/free)

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-jira-automation.git
cd ai-jira-automation

python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=gsk_your_key_here
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=ai_ticket_db
LOG_LEVEL=INFO

# Optional — Jira Integration
JIRA_BASE_URL=https://your-workspace.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=PROJ
```

> Jira variables are optional. Without them, the system works standalone with MongoDB.

### 3. Start the API Server

```bash
uvicorn app.main:app --reload
```

API live at **http://localhost:8000** | Swagger docs at **http://localhost:8000/docs**

### 4. Start the Dashboard (new terminal)

```bash
streamlit run dashboard.py
```

Dashboard at **http://localhost:8501**

---

## API Endpoints

### Tickets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/create-ticket` | Create ticket with AI classification |
| `GET` | `/tickets` | List all tickets (with filters) |
| `GET` | `/ticket/{id}` | Get single ticket |
| `PATCH` | `/ticket/{id}/status` | Update status (syncs to Jira) |
| `DELETE` | `/ticket/{id}` | Delete ticket |
| `POST` | `/ticket/{id}/comment` | Add comment (AI summarizes) |
| `GET` | `/ticket/{id}/comments` | Get all comments |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/summary` | Ticket analytics and SLA stats |
| `GET` | `/jira/status` | Check Jira connection |
| `GET` | `/health` | Health check |

### Example: Create a Ticket

```bash
curl -X POST http://localhost:8000/create-ticket \
  -H "Content-Type: application/json" \
  -d '{"description": "Payment gateway rejecting all credit card transactions since this morning. Revenue impact is significant."}'
```

**Response:**

```json
{
  "ticket_id": "a1b2c3d4-...",
  "ai_type": "Incident",
  "priority": "P0",
  "summary": "Payment gateway rejecting credit card transactions",
  "team": "Backend",
  "assigned_to": "Alice Johnson",
  "sla_hours": 4,
  "sla_deadline": "2026-04-27T16:30:00+00:00",
  "ai_fix_suggestion": "Investigate payment provider API connectivity...",
  "duplicate_of": null,
  "jira_key": "SCRUM-7",
  "jira_url": "https://workspace.atlassian.net/browse/SCRUM-7",
  "status": "OPEN"
}
```

### Filter Tickets

```bash
# By priority
curl "http://localhost:8000/tickets?priority=P0"

# By type
curl "http://localhost:8000/tickets?type=Bug"

# By status and team
curl "http://localhost:8000/tickets?status=OPEN&team=Backend"

# By assignee
curl "http://localhost:8000/tickets?assigned_to=Alice+Johnson"
```

### Add a Comment

```bash
curl -X POST http://localhost:8000/ticket/{ticket_id}/comment \
  -H "Content-Type: application/json" \
  -d '{"author": "Alice", "text": "Root cause identified. Fix in progress."}'
```

---

## Dashboard Features

The Streamlit dashboard provides four main views:

| Tab | What It Shows |
|-----|---------------|
| **Analytics** | Total tickets, SLA breaches, charts by priority/type/status/team/assignee |
| **All Tickets** | Filterable ticket list with status update, delete, AI fix suggestions |
| **Create Ticket** | Submit new tickets with instant AI analysis results |
| **Comments** | View ticket conversation with AI-generated summary |

---

## Jira Integration

### Setup

1. Sign up at [atlassian.com/software/jira/free](https://www.atlassian.com/software/jira/free)
2. Create a Scrum/Kanban project and note the **project key**
3. Generate API token at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
4. Add credentials to `.env`

### What Happens Automatically

| Step | Action |
|------|--------|
| 1 | User submits ticket description |
| 2 | AI classifies type, priority, summary, team, and fix suggestion |
| 3 | Duplicate check runs against existing tickets |
| 4 | SLA deadline calculated and team member assigned |
| 5 | Jira issue created with all AI-enriched fields |
| 6 | Ticket saved to MongoDB with Jira issue key |
| 7 | Status updates sync to Jira transitions |

### Without Jira

The system works fully standalone. Tickets are classified and stored in MongoDB. Jira fields return `null`.

---

## Project Structure

```
ai-jira-automation/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app + lifespan hooks
│   ├── config.py              # Environment config + logging
│   ├── models.py              # Pydantic models and enums
│   ├── services/
│   │   ├── groq_service.py    # Groq API client (multi-model fallback)
│   │   ├── ai_engine.py       # Classification, duplicates, SLA, assignment
│   │   └── jira_service.py    # Jira Cloud REST API integration
│   ├── db/
│   │   └── mongo.py           # MongoDB connection manager
│   └── routes/
│       └── ticket_routes.py   # REST endpoints + analytics
├── dashboard.py               # Streamlit analytics dashboard
├── requirements.txt
├── .env                       # Environment variables (not in repo)
├── .gitignore
└── README.md
```

---

## How the AI Works

The system uses **Groq** (ultra-fast LLM inference) with automatic model fallback:

1. **llama-3.1-8b-instant** (primary)
2. **llama3-8b-8192** (fallback)
3. **gemma2-9b-it** (fallback)
4. **mixtral-8x7b-32768** (fallback)

Each ticket description is sent with a structured prompt that extracts:
- **Type** — Bug / Feature / Incident
- **Priority** — P0 through P3 based on impact severity
- **Summary** — Concise one-liner
- **Team** — Best-fit team (Backend, Frontend, DevOps, Security, QA, Database, Platform)
- **Fix Suggestion** — Actionable recommendation

If the AI fails entirely, a fallback analysis is used so ticket creation never breaks.

---

## SLA Policy

| Priority | SLA (hours) | Description |
|----------|------------|-------------|
| P0 | 4 hours | Critical outage / revenue impact |
| P1 | 24 hours | High impact, significant users affected |
| P2 | 72 hours | Medium impact, workaround available |
| P3 | 168 hours | Low / cosmetic issues |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a Pull Request

---

## License

MIT License — free to use, modify, and distribute.
