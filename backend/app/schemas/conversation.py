from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConversationEvidenceResponse(BaseModel):
    """Grounded evidence citation supporting a conversational message."""

    id: Optional[int] = None
    document_source: str
    page: Optional[int] = None
    clause_section: Optional[str] = None
    extracted_text: Optional[str] = None
    interpretation: Optional[str] = None
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Payload for submitting a user message to an active conversation."""

    content: str = Field(..., min_length=1, description="User question or treatment scenario details")
    treatment_scenario: Optional[Dict[str, Any]] = Field(None, description="Optional structured treatment scenario")


class ConversationMessageResponse(BaseModel):
    """Complete representation of a conversation turn."""

    id: int
    conversation_id: int
    role: str  # "user", "assistant", "system"
    content: str
    confidence: Optional[str] = None  # "High", "Medium", "Low", "Insufficient evidence"
    is_grounded: bool = True
    uncertainty_reason: Optional[str] = None
    missing_information: Optional[List[str]] = None
    treatment_scenario: Optional[Dict[str, Any]] = None
    cost_estimate: Optional[Dict[str, Any]] = None
    evidence_references: List[ConversationEvidenceResponse] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Payload for initializing a new policy conversation."""

    policy_id: int = Field(..., gt=0, description="Database ID of the target policy")
    title: Optional[str] = Field(None, description="Optional human-readable title for the session")
    initial_message: Optional[str] = Field(None, description="Optional first user question")


class ConversationSummaryResponse(BaseModel):
    """Compact summary of a conversation session."""

    id: int
    policy_id: int
    title: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Full conversational session with complete chronological message history."""

    id: int
    policy_id: int
    title: Optional[str] = None
    context_metadata: Optional[Dict[str, Any]] = None
    messages: List[ConversationMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
