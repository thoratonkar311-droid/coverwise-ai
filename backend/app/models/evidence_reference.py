from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class EvidenceReference(Base):
    """Direct policy citations, clauses, and extracted evidence backing AI interpretations and calculations."""

    __tablename__ = "evidence_references"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        Integer,
        ForeignKey("coverage_rules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("policy_analyses.id", ondelete="CASCADE"),
        nullable=True,
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
    policy = relationship("Policy", back_populates="evidence_references")
    rule = relationship("CoverageRule", back_populates="evidence_references")
    analysis = relationship("PolicyAnalysis", back_populates="evidence_references")

    def __repr__(self) -> str:
        return f"<EvidenceReference(id={self.id}, page={self.page}, clause='{self.clause_section}', confidence={self.confidence})>"
