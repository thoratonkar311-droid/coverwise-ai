from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.models.simulation import Simulation


class SimulationRepository:
    """Data access repository for cost estimation simulations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, simulation_id: int) -> Optional[Simulation]:
        """Fetch simulation by primary key ID."""
        return self.db.query(Simulation).filter(Simulation.id == simulation_id).first()

    def create(
        self,
        hospital_quote: float,
        estimated_insurance_share: float,
        estimated_patient_share: float,
        policy_id: Optional[int] = None,
        treatment_id: Optional[int] = None,
        treatment_name: Optional[str] = None,
        room_category: Optional[str] = None,
        deductible: Optional[float] = None,
        copay: Optional[float] = None,
        coverage_limit: Optional[float] = None,
        calculation_breakdown: Optional[Any] = None,
    ) -> Simulation:
        """Persist a new simulation record."""
        sim = Simulation(
            policy_id=policy_id,
            treatment_id=treatment_id,
            treatment_name=treatment_name,
            hospital_quote=hospital_quote,
            room_category=room_category,
            deductible=deductible,
            copay=copay,
            coverage_limit=coverage_limit,
            estimated_insurance_share=estimated_insurance_share,
            estimated_patient_share=estimated_patient_share,
            calculation_breakdown=calculation_breakdown,
        )
        self.db.add(sim)
        self.db.commit()
        self.db.refresh(sim)
        return sim

    def list_by_policy(self, policy_id: int, skip: int = 0, limit: int = 50) -> List[Simulation]:
        """List simulations for a given policy ordered by newest first."""
        return (
            self.db.query(Simulation)
            .filter(Simulation.policy_id == policy_id)
            .order_by(Simulation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
