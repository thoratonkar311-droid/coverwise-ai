from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.treatment import Treatment


class TreatmentRepository:
    """Data access repository for treatments catalog."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, treatment_id: int) -> Optional[Treatment]:
        """Fetch treatment by primary key ID."""
        return self.db.query(Treatment).filter(Treatment.id == treatment_id).first()

    def get_by_name(self, name: str) -> Optional[Treatment]:
        """Fetch treatment by exact or case-insensitive name match."""
        return self.db.query(Treatment).filter(Treatment.name.ilike(name.strip())).first()

    def create(
        self,
        name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        typical_cost_min: Optional[float] = None,
        typical_cost_max: Optional[float] = None,
    ) -> Treatment:
        """Create and persist a new treatment catalog entry."""
        treatment = Treatment(
            name=name,
            category=category,
            description=description,
            typical_cost_min=typical_cost_min,
            typical_cost_max=typical_cost_max,
        )
        self.db.add(treatment)
        self.db.commit()
        self.db.refresh(treatment)
        return treatment

    def list(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Treatment]:
        """List treatments with optional search and category filters."""
        query = self.db.query(Treatment)
        if q and q.strip():
            search = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    Treatment.name.ilike(search),
                    Treatment.description.ilike(search),
                )
            )
        if category and category.strip():
            query = query.filter(Treatment.category.ilike(category.strip()))
        return query.order_by(Treatment.name.asc()).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Count total treatments in catalog."""
        return self.db.query(Treatment).count()
