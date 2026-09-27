from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Policy(Base):
    """Represents an uploaded insurance policy document and its extracted metadata."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(100), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    policy_number = Column(String(100), nullable=True, index=True)
    insurer_name = Column(String(255), nullable=True, index=True)
    plan_name = Column(String(255), nullable=True)
    policy_holder_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="uploaded", index=True)
    raw_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

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
    analyses = relationship(
        "PolicyAnalysis",
        back_populates="policy",
        cascade="all, delete-orphan",
        order_by="PolicyAnalysis.created_at.desc()",
    )
    coverage_rules = relationship(
        "CoverageRule",
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    simulations = relationship(
        "Simulation",
        back_populates="policy",
        cascade="all, delete-orphan",
    )
    evidence_references = relationship(
        "EvidenceReference",
        back_populates="policy",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Policy(id={self.id}, insurer='{self.insurer_name}', number='{self.policy_number}', status='{self.status}')>"
