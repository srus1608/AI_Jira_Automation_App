import requests
from requests.auth import HTTPBasicAuth

from app.config import (
    JIRA_BASE_URL,
    JIRA_EMAIL,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
    logger,
)

PRIORITY_MAP = {
    "P0": "Highest",
    "P1": "High",
    "P2": "Medium",
    "P3": "Low",
}

ISSUE_TYPE_MAP = {
    "Bug": "Task",
    "Feature": "Task",
    "Incident": "Task",
}


def is_jira_configured() -> bool:
    return all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY])


def _get_auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def _get_headers() -> dict:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def create_jira_issue(ticket: dict) -> dict | None:
    """Create a Jira issue from an AI-analyzed ticket.

    Returns a dict with 'key' and 'url' on success, or None if Jira
    is not configured or the request fails.
    """
    if not is_jira_configured():
        logger.warning("Jira is not configured — skipping issue creation")
        return None

    jira_priority = PRIORITY_MAP.get(ticket.get("priority", "P2"), "Medium")
    jira_issue_type = ISSUE_TYPE_MAP.get(ticket.get("ai_type", "Bug"), "Task")

    description_adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ticket.get("description", "")}],
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": f"AI Suggested Team: {ticket.get('team', 'N/A')}",
                        "marks": [{"type": "strong"}],
                    }
                ],
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": f"Internal Ticket ID: {ticket.get('ticket_id', 'N/A')}",
                    }
                ],
            },
        ],
    }

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": ticket.get("summary", "AI-generated ticket"),
            "description": description_adf,
            "issuetype": {"name": jira_issue_type},
            "priority": {"name": jira_priority},
        }
    }

    api_url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"

    try:
        logger.info("Creating Jira issue in project %s", JIRA_PROJECT_KEY)
        response = requests.post(
            api_url,
            headers=_get_headers(),
            auth=_get_auth(),
            json=payload,
            timeout=15,
        )

        if response.status_code >= 400:
            logger.error("Jira API error %s: %s", response.status_code, response.text)
            payload["fields"]["issuetype"] = {"name": "Task"}
            payload["fields"].pop("priority", None)
            logger.info("Retrying with fallback issue type 'Task' and no priority")
            response = requests.post(
                api_url,
                headers=_get_headers(),
                auth=_get_auth(),
                json=payload,
                timeout=15,
            )

        response.raise_for_status()

        data = response.json()
        issue_key = data["key"]
        issue_url = f"{JIRA_BASE_URL.rstrip('/')}/browse/{issue_key}"

        logger.info("Jira issue created: %s (%s)", issue_key, issue_url)
        return {"key": issue_key, "url": issue_url}

    except requests.exceptions.RequestException:
        logger.exception("Failed to create Jira issue")
        return None


def transition_jira_issue(issue_key: str, status: str) -> bool:
    """Transition a Jira issue to match our internal status."""
    if not is_jira_configured() or not issue_key:
        return False

    status_name_map = {
        "OPEN": "To Do",
        "IN_PROGRESS": "In Progress",
        "CLOSED": "Done",
    }

    target_status = status_name_map.get(status)
    if not target_status:
        return False

    api_url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{issue_key}/transitions"

    try:
        response = requests.get(
            api_url,
            headers=_get_headers(),
            auth=_get_auth(),
            timeout=10,
        )
        response.raise_for_status()
        transitions = response.json().get("transitions", [])

        transition_id = None
        for t in transitions:
            if t["name"].lower() == target_status.lower():
                transition_id = t["id"]
                break

        if not transition_id:
            logger.warning("No matching Jira transition for status '%s'", status)
            return False

        response = requests.post(
            api_url,
            headers=_get_headers(),
            auth=_get_auth(),
            json={"transition": {"id": transition_id}},
            timeout=10,
        )
        response.raise_for_status()

        logger.info("Jira issue %s transitioned to '%s'", issue_key, target_status)
        return True

    except requests.exceptions.RequestException:
        logger.exception("Failed to transition Jira issue %s", issue_key)
        return False
