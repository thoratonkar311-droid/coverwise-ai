from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.db.session import Base


class Treatment(Base):
    """Catalog of medical procedures, treatments, and benchmark costs."""

    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    typical_cost_min = Column(Float, nullable=True)
    typical_cost_max = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    analyses = relationship(
        "PolicyAnalysis",
        back_populates="treatment",
    )
    simulations = relationship(
        "Simulation",
        back_populates="treatment",
    )

    def __repr__(self) -> str:
        return f"<Treatment(id={self.id}, name='{self.name}', category='{self.category}')>"
