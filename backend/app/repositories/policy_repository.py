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
        policy_holder_name: Optional[str] = None,
        sum_insured: Optional[float] = None,
        policy_start_date: Optional[str] = None,
        policy_end_date: Optional[str] = None,
        document_hash: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
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
            policy_holder_name=policy_holder_name,
            sum_insured=sum_insured,
            policy_start_date=policy_start_date,
            policy_end_date=policy_end_date,
            document_hash=document_hash,
            extraction_confidence=extraction_confidence,
            raw_metadata=raw_metadata,
        )
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def find_by_document_hash(self, document_hash: str, user_id: Optional[str] = None) -> Optional[Policy]:
        """Find an existing policy matching document content hash and optional user_id."""
        query = self.db.query(Policy).filter(Policy.document_hash == document_hash)
        if user_id is not None:
            query = query.filter(Policy.user_id == str(user_id))
        return query.order_by(Policy.created_at.desc()).first()

    def update_status(self, policy: Policy, status: str, error_message: Optional[str] = None) -> Policy:
        """Update policy processing status and optional error message."""
        policy.status = status
        if error_message is not None:
            policy.error_message = error_message
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def list(self, skip: int = 0, limit: int = 50, user_id: Optional[str] = None) -> List[Policy]:
        """List policies ordered by creation timestamp, optionally filtered by user_id."""
        query = self.db.query(Policy)
        if user_id is not None:
            query = query.filter(Policy.user_id == str(user_id))
        return (
            query.order_by(Policy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def find_by_identifier(self, identifier: str) -> Optional[Policy]:
        """Find policy by primary key ID or policy number or name."""
        try:
            if str(identifier).isdigit():
                pol = self.get_by_id(int(identifier))
                if pol:
                    return pol
        except (ValueError, TypeError):
            pass

        pol = self.db.query(Policy).filter(Policy.policy_number == identifier).first()
        if pol:
            return pol

        return (
            self.db.query(Policy)
            .filter(
                (Policy.filename.ilike(f"%{identifier}%"))
                | (Policy.plan_name.ilike(f"%{identifier}%"))
            )
            .first()
        )
