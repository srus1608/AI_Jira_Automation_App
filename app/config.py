import os
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "ai_ticket_db")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

JIRA_BASE_URL: str = os.getenv("JIRA_BASE_URL", "")
JIRA_EMAIL: str = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN: str = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY: str = os.getenv("JIRA_PROJECT_KEY", "")

GROQ_MODEL: str = "llama3-8b-8192"
GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

COLLECTION_TICKETS: str = "tickets"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("ai_ticket_automation")
