from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Simulation(Base):
    """Cost estimation simulation calculating patient and insurer responsibility based on coverage rules."""

    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    policy_id = Column(
        Integer,
        ForeignKey("policies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(String(100), nullable=True, index=True)
    treatment_id = Column(
        Integer,
        ForeignKey("treatments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    treatment_name = Column(String(255), nullable=True)
    hospital_quote = Column(Float, nullable=False)
    room_category = Column(String(100), nullable=True)
    deductible = Column(Float, nullable=True, default=0.0)
    copay = Column(Float, nullable=True, default=0.0)
    coverage_limit = Column(Float, nullable=True)
    estimated_insurance_share = Column(Float, nullable=False, default=0.0)
    estimated_patient_share = Column(Float, nullable=False, default=0.0)
    calculation_breakdown = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    policy = relationship("Policy", back_populates="simulations")
    treatment = relationship("Treatment", back_populates="simulations")

    def __repr__(self) -> str:
        return (
            f"<Simulation(id={self.id}, quote={self.hospital_quote}, "
            f"insurance={self.estimated_insurance_share}, patient={self.estimated_patient_share})>"
        )
