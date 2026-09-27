from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class PolicyAnalysis(Base):
    """Analysis results for a policy covering specific treatments or general coverage intelligence."""

    __tablename__ = "policy_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    treatment_id = Column(
        Integer,
        ForeignKey("treatments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    treatment_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    result_summary = Column(Text, nullable=True)
    result_data = Column(JSON, nullable=True)

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
    policy = relationship("Policy", back_populates="analyses")
    treatment = relationship("Treatment", back_populates="analyses")
    evidence_references = relationship(
        "EvidenceReference",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PolicyAnalysis(id={self.id}, policy_id={self.policy_id}, status='{self.status}')>"
