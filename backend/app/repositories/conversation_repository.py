from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import (
    ConversationEvidenceReference,
    ConversationMessage,
    PolicyConversation,
)


class ConversationRepository:
    """Repository handling persistence and queries for conversational sessions and messages."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        policy_id: int,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyConversation:
        """Create a new policy conversation session."""
        conv = PolicyConversation(
            policy_id=policy_id,
            user_id=user_id,
            title=title or "Policy Inquiry",
            context_metadata=context_metadata or {},
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_by_id(self, conversation_id: int) -> Optional[PolicyConversation]:
        """Fetch conversation with eager loaded messages and evidence references."""
        return (
            self.db.query(PolicyConversation)
            .options(
                joinedload(PolicyConversation.messages).joinedload(
                    ConversationMessage.evidence_references
                )
            )
            .filter(PolicyConversation.id == conversation_id)
            .first()
        )

    def list_by_policy(
        self, policy_id: int, skip: int = 0, limit: int = 50
    ) -> List[PolicyConversation]:
        """List historical conversations for a policy."""
        return (
            self.db.query(PolicyConversation)
            .filter(PolicyConversation.policy_id == policy_id)
            .order_by(PolicyConversation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        confidence: Optional[str] = None,
        is_grounded: bool = True,
        uncertainty_reason: Optional[str] = None,
        missing_information: Optional[List[str]] = None,
        treatment_scenario: Optional[Dict[str, Any]] = None,
        cost_estimate: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Append an individual message to an ongoing conversation."""
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            confidence=confidence,
            is_grounded=is_grounded,
            uncertainty_reason=uncertainty_reason,
            missing_information=missing_information,
            treatment_scenario=treatment_scenario,
            cost_estimate=cost_estimate,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def add_evidence_reference(
        self,
        message_id: int,
        policy_id: int,
        document_source: str,
        page: Optional[int] = None,
        clause_section: Optional[str] = None,
        extracted_text: Optional[str] = None,
        interpretation: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> ConversationEvidenceReference:
        """Attach supporting evidence reference to an assistant message."""
        evidence = ConversationEvidenceReference(
            message_id=message_id,
            policy_id=policy_id,
            document_source=document_source,
            page=page,
            clause_section=clause_section,
            extracted_text=extracted_text,
            interpretation=interpretation,
            confidence=confidence,
        )
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def update_context_metadata(
        self, conversation_id: int, context_metadata: Dict[str, Any]
    ) -> None:
        """Update session context metadata (active scenario, topics)."""
        conv = self.db.query(PolicyConversation).filter(PolicyConversation.id == conversation_id).first()
        if conv:
            merged = {**(conv.context_metadata or {}), **context_metadata}
            conv.context_metadata = merged
            self.db.commit()
