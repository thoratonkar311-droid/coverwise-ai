from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.models import PolicyAnalysis


class AnalysisRepository:
    """Data access repository for policy analyses."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, analysis_id: int) -> Optional[PolicyAnalysis]:
        """Fetch policy analysis by primary key ID."""
        return self.db.query(PolicyAnalysis).filter(PolicyAnalysis.id == analysis_id).first()

    def find_recent_by_policy_and_treatment(
        self, policy_id: int, treatment_name: str
    ) -> Optional[PolicyAnalysis]:
        """Find recent completed analysis for a policy and treatment to support idempotency."""
        clean = treatment_name.strip()
        return (
            self.db.query(PolicyAnalysis)
            .filter(
                PolicyAnalysis.policy_id == policy_id,
                PolicyAnalysis.treatment_name.ilike(clean),
                PolicyAnalysis.status == "completed",
            )
            .order_by(PolicyAnalysis.created_at.desc())
            .first()
        )

    def create(
        self,
        policy_id: int,
        treatment_name: str,
        status: str = "completed",
        treatment_id: Optional[int] = None,
        result_summary: Optional[str] = None,
        result_data: Optional[Any] = None,
    ) -> PolicyAnalysis:
        """Create and persist a new policy analysis record."""
        analysis = PolicyAnalysis(
            policy_id=policy_id,
            treatment_id=treatment_id,
            treatment_name=treatment_name,
            status=status,
            result_summary=result_summary,
            result_data=result_data,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def list_by_policy(self, policy_id: int) -> List[PolicyAnalysis]:
        """Fetch all analyses associated with a policy."""
        return (
            self.db.query(PolicyAnalysis)
            .filter(PolicyAnalysis.policy_id == policy_id)
            .order_by(PolicyAnalysis.created_at.desc())
            .all()
        )
