from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Policy


class PolicyRepository:
    """Data access repository for policies."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, policy_id: int) -> Optional[Policy]:
        """Fetch policy by primary key ID."""
        return self.db.query(Policy).filter(Policy.id == policy_id).first()

    def create(
        self,
        filename: str,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        status: str = "uploaded",
        insurer_name: Optional[str] = None,
        plan_name: Optional[str] = None,
        policy_number: Optional[str] = None,
        raw_metadata: Optional[dict] = None,
    ) -> Policy:
        """Create and persist a new policy record."""
        policy = Policy(
            filename=filename,
            file_path=file_path,
            user_id=user_id,
            status=status,
            insurer_name=insurer_name,
            plan_name=plan_name,
            policy_number=policy_number,
            raw_metadata=raw_metadata,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def update_status(self, policy: Policy, status: str, error_message: Optional[str] = None) -> Policy:
        """Update policy processing status and optional error message."""
        policy.status = status
        if error_message is not None:
            policy.error_message = error_message
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def list(self, skip: int = 0, limit: int = 50) -> List[Policy]:
        """List policies ordered by creation timestamp."""
        return (
            self.db.query(Policy)
            .order_by(Policy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
