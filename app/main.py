from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import logger
from app.db.mongo import close_connection, get_tickets_collection
from app.routes.ticket_routes import router as ticket_router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Ticket Automation System")
    get_tickets_collection().create_index("ticket_id", unique=True)
    logger.info("MongoDB indexes ensured")
    yield
    close_connection()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Ticket Automation System",
    description=(
        "Automatically classify, prioritize, summarize, and assign "
        "support tickets using Groq AI. Jira-ready architecture."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ticket_router)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["System"], include_in_schema=False)
def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "ai-ticket-automation"}
