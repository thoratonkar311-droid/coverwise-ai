from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class CoverageRule(Base):
    """Structured insurance coverage parameters, limitations, deductibles, and exclusions."""

    __tablename__ = "coverage_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coverage_status = Column(String(50), nullable=False, default="covered", index=True)
    deductible = Column(Float, nullable=True)
    copay = Column(Float, nullable=True)
    copay_percentage = Column(Float, nullable=True)
    coverage_limit = Column(Float, nullable=True)
    exclusions = Column(JSON, nullable=True)
    waiting_period = Column(String(100), nullable=True)
    room_category = Column(String(100), nullable=True)
    source_reference = Column(String(255), nullable=True)

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
    policy = relationship("Policy", back_populates="coverage_rules")
    evidence_references = relationship(
        "EvidenceReference",
        back_populates="rule",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CoverageRule(id={self.id}, policy_id={self.policy_id}, status='{self.coverage_status}', limit={self.coverage_limit})>"
