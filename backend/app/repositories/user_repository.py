from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Repository handling database operations for User entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by database primary key ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by normalized lowercase email address."""
        return self.db.query(User).filter(User.email == email.strip().lower()).first()

    def create(
        self,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
    ) -> User:
        """Create and persist a new user record."""
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name.strip() if full_name else None,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
