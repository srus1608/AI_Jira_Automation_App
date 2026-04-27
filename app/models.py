from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketType(str, Enum):
    BUG = "Bug"
    FEATURE = "Feature"
    INCIDENT = "Incident"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Status(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class TicketCreateRequest(BaseModel):
    description: str = Field(
        ..., min_length=10, max_length=5000, description="Ticket description"
    )


class TicketStatusUpdate(BaseModel):
    status: Status


class CommentAddRequest(BaseModel):
    author: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    author: str
    text: str
    created_at: str


class TicketResponse(BaseModel):
    ticket_id: str
    description: str
    ai_type: str
    priority: str
    summary: str
    team: str
    status: str
    created_at: str
    jira_key: Optional[str] = None
    jira_url: Optional[str] = None
    assigned_to: Optional[str] = None
    sla_hours: Optional[int] = None
    sla_deadline: Optional[str] = None
    ai_fix_suggestion: Optional[str] = None
    duplicate_of: Optional[str] = None
    comments: Optional[list[CommentResponse]] = None
    conversation_summary: Optional[str] = None
