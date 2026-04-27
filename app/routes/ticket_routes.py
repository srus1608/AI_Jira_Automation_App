import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import logger
from app.db.mongo import get_tickets_collection
from app.models import (
    CommentAddRequest,
    CommentResponse,
    Priority,
    Status,
    TicketCreateRequest,
    TicketResponse,
    TicketStatusUpdate,
    TicketType,
)
from app.services.ai_engine import (
    analyze_ticket,
    auto_assign,
    check_duplicate,
    get_sla_hours,
    summarize_conversation,
)
from app.services.jira_service import create_jira_issue, transition_jira_issue

router = APIRouter(tags=["Tickets"])


def _doc_to_response(doc: dict) -> TicketResponse:
    comments_raw = doc.get("comments") or []
    comments = [
        CommentResponse(
            author=c["author"], text=c["text"], created_at=c["created_at"]
        )
        for c in comments_raw
    ]
    return TicketResponse(
        ticket_id=doc["ticket_id"],
        description=doc["description"],
        ai_type=doc["ai_type"],
        priority=doc["priority"],
        summary=doc["summary"],
        team=doc["team"],
        status=doc["status"],
        created_at=doc["created_at"],
        jira_key=doc.get("jira_key"),
        jira_url=doc.get("jira_url"),
        assigned_to=doc.get("assigned_to"),
        sla_hours=doc.get("sla_hours"),
        sla_deadline=doc.get("sla_deadline"),
        ai_fix_suggestion=doc.get("ai_fix_suggestion"),
        duplicate_of=doc.get("duplicate_of"),
        comments=comments if comments else None,
        conversation_summary=doc.get("conversation_summary"),
    )


@router.post("/create-ticket", response_model=TicketResponse, status_code=201)
def create_ticket(request: TicketCreateRequest):
    """Create a new ticket with AI classification, SLA, auto-assignment, and duplicate detection."""
    ticket_id = str(uuid.uuid4())
    logger.info("Creating ticket %s", ticket_id)

    collection = get_tickets_collection()

    existing = list(collection.find({"status": {"$ne": "CLOSED"}}, {"_id": 0}))
    duplicate_of = check_duplicate(request.description, existing)

    ai_result = analyze_ticket(request.description)

    sla_hours = get_sla_hours(ai_result["priority"])
    sla_deadline = (datetime.now(timezone.utc) + timedelta(hours=sla_hours)).isoformat()

    assigned_to = auto_assign(ai_result["team"], existing)

    ticket_doc = {
        "ticket_id": ticket_id,
        "description": request.description,
        "ai_type": ai_result["type"],
        "priority": ai_result["priority"],
        "summary": ai_result["summary"],
        "team": ai_result["team"],
        "status": Status.OPEN.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "jira_key": None,
        "jira_url": None,
        "assigned_to": assigned_to,
        "sla_hours": sla_hours,
        "sla_deadline": sla_deadline,
        "ai_fix_suggestion": ai_result.get("fix_suggestion"),
        "duplicate_of": duplicate_of,
        "comments": [],
        "conversation_summary": None,
    }

    jira_result = create_jira_issue(ticket_doc)
    if jira_result:
        ticket_doc["jira_key"] = jira_result["key"]
        ticket_doc["jira_url"] = jira_result["url"]

    collection.insert_one(ticket_doc)
    logger.info("Ticket %s saved (assigned=%s, sla=%dh, duplicate=%s)",
                ticket_id, assigned_to, sla_hours, duplicate_of)

    return _doc_to_response(ticket_doc)


@router.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    priority: Optional[str] = Query(None, description="Filter by priority (P0-P3)"),
    ticket_type: Optional[str] = Query(None, alias="type", description="Filter by type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    team: Optional[str] = Query(None, description="Filter by team"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
):
    """List all tickets with optional filtering."""
    query: dict = {}

    if priority:
        if priority not in [p.value for p in Priority]:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
        query["priority"] = priority

    if ticket_type:
        if ticket_type not in [t.value for t in TicketType]:
            raise HTTPException(status_code=400, detail=f"Invalid type: {ticket_type}")
        query["ai_type"] = ticket_type

    if status:
        if status not in [s.value for s in Status]:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        query["status"] = status

    if team:
        query["team"] = team

    if assigned_to:
        query["assigned_to"] = assigned_to

    collection = get_tickets_collection()
    docs = list(collection.find(query, {"_id": 0}).sort("created_at", -1))
    logger.info("Listing tickets (filter=%s, count=%d)", query, len(docs))
    return [_doc_to_response(doc) for doc in docs]


@router.get("/ticket/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: str):
    """Retrieve a single ticket by ID."""
    collection = get_tickets_collection()
    doc = collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _doc_to_response(doc)


@router.patch("/ticket/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(ticket_id: str, body: TicketStatusUpdate):
    """Update a ticket's status (OPEN / IN_PROGRESS / CLOSED)."""
    collection = get_tickets_collection()
    result = collection.find_one_and_update(
        {"ticket_id": ticket_id},
        {"$set": {"status": body.status.value}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Ticket not found")
    result.pop("_id", None)

    jira_key = result.get("jira_key")
    if jira_key:
        transition_jira_issue(jira_key, body.status.value)

    logger.info("Ticket %s status updated to %s", ticket_id, body.status.value)
    return _doc_to_response(result)


@router.post("/ticket/{ticket_id}/comment", response_model=TicketResponse)
def add_comment(ticket_id: str, body: CommentAddRequest):
    """Add a comment to a ticket and regenerate AI conversation summary."""
    collection = get_tickets_collection()
    doc = collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = {
        "author": body.author,
        "text": body.text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    comments = doc.get("comments", [])
    comments.append(comment)

    conv_summary = summarize_conversation(
        doc.get("summary", ""),
        doc.get("description", ""),
        comments,
    )

    collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"comments": comments, "conversation_summary": conv_summary}},
    )

    doc["comments"] = comments
    doc["conversation_summary"] = conv_summary
    logger.info("Comment added to %s by %s", ticket_id, body.author)
    return _doc_to_response(doc)


@router.get("/ticket/{ticket_id}/comments", response_model=list[CommentResponse])
def get_comments(ticket_id: str):
    """Get all comments for a ticket."""
    collection = get_tickets_collection()
    doc = collection.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    comments = doc.get("comments", [])
    return [CommentResponse(**c) for c in comments]


@router.get("/analytics/summary", tags=["Analytics"])
def analytics_summary():
    """Get ticket analytics: counts by priority, type, status, team, and SLA breaches."""
    collection = get_tickets_collection()
    all_tickets = list(collection.find({}, {"_id": 0}))

    now = datetime.now(timezone.utc)
    sla_breached = 0
    for t in all_tickets:
        if t.get("status") != "CLOSED" and t.get("sla_deadline"):
            try:
                deadline = datetime.fromisoformat(t["sla_deadline"])
                if now > deadline:
                    sla_breached += 1
            except (ValueError, TypeError):
                pass

    by_priority = {}
    by_type = {}
    by_status = {}
    by_team = {}
    by_assignee = {}

    for t in all_tickets:
        p = t.get("priority", "Unknown")
        by_priority[p] = by_priority.get(p, 0) + 1

        tp = t.get("ai_type", "Unknown")
        by_type[tp] = by_type.get(tp, 0) + 1

        s = t.get("status", "Unknown")
        by_status[s] = by_status.get(s, 0) + 1

        tm = t.get("team", "Unknown")
        by_team[tm] = by_team.get(tm, 0) + 1

        a = t.get("assigned_to", "Unassigned")
        by_assignee[a] = by_assignee.get(a, 0) + 1

    return {
        "total_tickets": len(all_tickets),
        "sla_breached": sla_breached,
        "by_priority": by_priority,
        "by_type": by_type,
        "by_status": by_status,
        "by_team": by_team,
        "by_assignee": by_assignee,
    }


@router.get("/jira/status", tags=["Jira"])
def jira_status():
    """Check if Jira integration is configured and reachable."""
    from app.services.jira_service import is_jira_configured
    if not is_jira_configured():
        return {"connected": False, "message": "Jira is not configured. Set JIRA_* variables in .env"}
    return {"connected": True, "message": "Jira integration is active"}


@router.delete("/ticket/{ticket_id}", status_code=200)
def delete_ticket(ticket_id: str):
    """Delete a ticket by ID."""
    collection = get_tickets_collection()
    result = collection.delete_one({"ticket_id": ticket_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    logger.info("Ticket %s deleted", ticket_id)
    return {"message": f"Ticket {ticket_id} deleted successfully"}
