from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse

logger = get_logger("coverwise.api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create a new local user account with hashed password and return JWT access token."""
    repo = UserRepository(db)
    existing_user = repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed_pw = hash_password(payload.password)
    user = repo.create(
        email=payload.email,
        password_hash=hashed_pw,
        full_name=payload.full_name,
    )
    logger.info(f"Registered new user ID {user.id} ({user.email})")

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT token",
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Verify user credentials and generate a signed session token."""
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    logger.info(f"User ID {user.id} ({user.email}) authenticated successfully")
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile details for the currently authenticated session."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    summary="Terminate authenticated session",
)
def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Acknowledge session termination on client request."""
    logger.info(f"User ID {current_user.id} logged out")
    return {"message": "Logged out successfully", "status": "ok"}
