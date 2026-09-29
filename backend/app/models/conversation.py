from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class PolicyConversation(Base):
    """Persistent conversational assistant session tied to an uploaded policy."""

    __tablename__ = "policy_conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    context_metadata = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    policy = relationship("Policy", back_populates="conversations")
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<PolicyConversation(id={self.id}, policy_id={self.policy_id}, title='{self.title}')>"


class ConversationMessage(Base):
    """Individual conversational turn within a policy Q&A session."""

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey("policy_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    confidence = Column(String(50), nullable=True)  # "High", "Medium", "Low", "Insufficient evidence"
    is_grounded = Column(Boolean, default=True, nullable=False)
    uncertainty_reason = Column(Text, nullable=True)
    missing_information = Column(JSON, nullable=True)  # List[str] of missing items
    treatment_scenario = Column(JSON, nullable=True)  # Structured scenario state
    cost_estimate = Column(JSON, nullable=True)  # Associated deterministic cost estimate

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation = relationship("PolicyConversation", back_populates="messages")
    evidence_references = relationship(
        "ConversationEvidenceReference",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ConversationEvidenceReference.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, role='{self.role}', confidence='{self.confidence}')>"


class ConversationEvidenceReference(Base):
    """Direct policy citations backing conversational answers."""

    __tablename__ = "conversation_evidence_references"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(
        Integer,
        ForeignKey("conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_source = Column(String(255), nullable=False)
    page = Column(Integer, nullable=True)
    clause_section = Column(String(255), nullable=True)
    extracted_text = Column(Text, nullable=True)
    interpretation = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    message = relationship("ConversationMessage", back_populates="evidence_references")

    def __repr__(self) -> str:
        return f"<ConversationEvidenceReference(id={self.id}, page={self.page}, clause='{self.clause_section}')>"
