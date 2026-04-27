from app.config import logger
from app.services.groq_service import generate_ai_response

ANALYSIS_PROMPT_TEMPLATE = """Analyze the following support ticket description and return a JSON object with exactly these fields:

1. "type"     — one of: "Bug", "Feature", "Incident"
2. "priority" — one of: "P0", "P1", "P2", "P3"
   P0 = Critical/outage, P1 = High impact, P2 = Medium, P3 = Low/cosmetic
3. "summary"  — a concise one-line summary (max 120 characters)
4. "team"     — the most appropriate team from: "Backend", "Frontend", "DevOps", "Security", "QA", "Database", "Platform"
5. "fix_suggestion" — a brief actionable suggestion for resolving this issue (2-3 sentences max)

Ticket description:
\"\"\"
{description}
\"\"\"

Respond with ONLY valid JSON. No explanations, no markdown fences."""

DUPLICATE_CHECK_PROMPT = """Compare the NEW ticket with the EXISTING tickets below.
If the new ticket is describing the same issue as any existing ticket, return the ticket_id of the duplicate.
If no duplicate exists, return null.

NEW ticket description:
\"\"\"{new_description}\"\"\"

EXISTING tickets:
{existing_tickets}

Respond with ONLY valid JSON: {{"duplicate_of": "ticket_id_here"}} or {{"duplicate_of": null}}"""

CONVERSATION_SUMMARY_PROMPT = """Summarize the following ticket conversation in 2-3 concise sentences.
Focus on the key decisions, findings, and current status.

Ticket summary: {summary}
Ticket description: {description}

Comments:
{comments}

Respond with ONLY valid JSON: {{"conversation_summary": "your summary here"}}"""

FALLBACK_ANALYSIS = {
    "type": "Bug",
    "priority": "P2",
    "summary": "Ticket pending manual review — AI analysis unavailable",
    "team": "Backend",
    "fix_suggestion": "Manual review required — AI suggestion unavailable.",
}

VALID_TYPES = {"Bug", "Feature", "Incident"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_TEAMS = {"Backend", "Frontend", "DevOps", "Security", "QA", "Database", "Platform"}

SLA_HOURS_MAP = {
    "P0": 4,
    "P1": 24,
    "P2": 72,
    "P3": 168,
}

TEAM_MEMBERS = {
    "Backend": ["Alice Johnson", "Bob Smith", "Charlie Lee"],
    "Frontend": ["Diana Chen", "Eve Martinez"],
    "DevOps": ["Frank Wilson", "Grace Kim"],
    "Security": ["Hank Brown", "Ivy Patel"],
    "QA": ["Jack Taylor", "Karen White"],
    "Database": ["Leo Garcia", "Maya Singh"],
    "Platform": ["Nathan Clark", "Olivia Davis"],
}


def _validate_analysis(result: dict) -> dict:
    """Normalize and validate the AI response fields."""
    if result.get("type") not in VALID_TYPES:
        result["type"] = "Bug"
    if result.get("priority") not in VALID_PRIORITIES:
        result["priority"] = "P2"
    if not isinstance(result.get("summary"), str) or len(result["summary"]) < 5:
        result["summary"] = "AI-generated summary unavailable"
    if result.get("team") not in VALID_TEAMS:
        result["team"] = "Backend"
    if not isinstance(result.get("fix_suggestion"), str) or len(result["fix_suggestion"]) < 5:
        result["fix_suggestion"] = "Manual review required — AI suggestion unavailable."
    return result


def get_sla_hours(priority: str) -> int:
    return SLA_HOURS_MAP.get(priority, 72)


def auto_assign(team: str, existing_tickets: list) -> str:
    """Assign to the team member with the fewest open tickets."""
    members = TEAM_MEMBERS.get(team, ["Unassigned"])
    workload = {m: 0 for m in members}
    for ticket in existing_tickets:
        assignee = ticket.get("assigned_to")
        if assignee in workload and ticket.get("status") != "CLOSED":
            workload[assignee] += 1
    return min(workload, key=workload.get)


def analyze_ticket(description: str) -> dict:
    """Run AI analysis on a ticket description and return structured result."""
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(description=description)

    try:
        raw_result = generate_ai_response(prompt)
        result = _validate_analysis(raw_result)
        logger.info(
            "AI analysis complete — type=%s priority=%s team=%s",
            result["type"],
            result["priority"],
            result["team"],
        )
        return result

    except Exception:
        logger.exception("AI analysis failed — returning fallback")
        return FALLBACK_ANALYSIS.copy()


def check_duplicate(new_description: str, existing_tickets: list) -> str | None:
    """Check if a similar ticket already exists using AI."""
    if not existing_tickets:
        return None

    tickets_text = "\n".join(
        f"- ticket_id: {t['ticket_id']} | summary: {t.get('summary', '')} | description: {t.get('description', '')[:200]}"
        for t in existing_tickets[:20]
    )

    prompt = DUPLICATE_CHECK_PROMPT.format(
        new_description=new_description,
        existing_tickets=tickets_text,
    )

    try:
        result = generate_ai_response(prompt)
        dup_id = result.get("duplicate_of")
        if dup_id and dup_id != "null":
            logger.info("Duplicate detected: %s", dup_id)
            return dup_id
        return None
    except Exception:
        logger.exception("Duplicate check failed")
        return None


def summarize_conversation(summary: str, description: str, comments: list) -> str:
    """Generate an AI summary of the ticket conversation."""
    if not comments:
        return "No comments yet."

    comments_text = "\n".join(
        f"- {c['author']} ({c['created_at']}): {c['text']}"
        for c in comments
    )

    prompt = CONVERSATION_SUMMARY_PROMPT.format(
        summary=summary,
        description=description,
        comments=comments_text,
    )

    try:
        result = generate_ai_response(prompt)
        return result.get("conversation_summary", "Summary unavailable.")
    except Exception:
        logger.exception("Conversation summary failed")
        return "Summary unavailable."
