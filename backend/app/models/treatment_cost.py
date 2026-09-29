from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class TreatmentCost(Base):
    """Structured benchmark dataset of medical procedure costs across categories, cities, and tiers."""

    __tablename__ = "treatment_costs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    treatment_id = Column(String(100), nullable=False, unique=True, index=True)
    treatment_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    city = Column(String(100), nullable=True, index=True)
    hospital_type = Column(String(100), nullable=True)  # e.g., "Tier 1 Multi-Specialty", "Tier 2 Network"
    inpatient_outpatient = Column(String(50), nullable=False, default="inpatient")  # "inpatient" | "outpatient"
    min_cost = Column(Float, nullable=False)
    typical_cost = Column(Float, nullable=False)
    max_cost = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    length_of_stay_days = Column(Integer, nullable=False, default=1)
    data_source_type = Column(String(100), nullable=False, default="synthetic_benchmark")
    dataset_version = Column(String(50), nullable=False, default="1.0.0")
    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TreatmentCost(id='{self.treatment_id}', name='{self.treatment_name}', typical={self.typical_cost} {self.currency})>"


class TreatmentScenario(Base):
    """User-supplied treatment scenario linking policy, procedure parameters, and estimate results."""

    __tablename__ = "treatment_scenarios"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(100), nullable=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("policy_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    treatment_name = Column(String(255), nullable=False)
    diagnosis = Column(String(255), nullable=True)
    hospital_name = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    hospital_type = Column(String(100), nullable=True)
    inpatient_outpatient = Column(String(50), nullable=True, default="inpatient")
    length_of_stay_days = Column(Integer, nullable=True)
    patient_age = Column(Integer, nullable=True)
    quoted_cost = Column(Float, nullable=False)
    non_payable_items = Column(Float, nullable=True, default=0.0)
    scenario_metadata = Column(JSON, nullable=True)

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
    policy = relationship("Policy", back_populates="treatment_scenarios")

    def __repr__(self) -> str:
        return f"<TreatmentScenario(id={self.id}, treatment='{self.treatment_name}', quote={self.quoted_cost})>"
