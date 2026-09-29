from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_optional_current_user
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.policy_repository import PolicyRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationSummaryResponse,
    MessageCreate,
)
from app.services.conversation_service import (
    ConversationService,
    get_conversation_service,
)

logger = get_logger("coverwise.api.conversations")

router = APIRouter(prefix="/conversations", tags=["Policy Conversational Assistant"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new policy conversation session",
)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    conv_service: ConversationService = Depends(get_conversation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> ConversationResponse:
    """Initialize a persistent conversational session grounded in an uploaded policy."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(payload.policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy #{payload.policy_id} not found.",
        )

    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to start a conversation for this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this policy.",
            )

    try:
        user_id = str(current_user.id) if current_user else None
        conv = conv_service.create_conversation(
            db=db,
            policy_id=payload.policy_id,
            user_id=user_id,
            title=payload.title,
            initial_message=payload.initial_message,
        )
        return conv_service.format_conversation_response(conv)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation session with message history",
)
def get_conversation(
    conversation_id: int = Path(..., gt=0, description="Database ID of the conversation"),
    db: Session = Depends(get_db),
    conv_service: ConversationService = Depends(get_conversation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> ConversationResponse:
    """Retrieve an existing conversation session along with its message turns and evidence citations."""
    repo = ConversationRepository(db)
    conv = repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation #{conversation_id} not found.",
        )

    owner_id = conv.user_id or (conv.policy.user_id if conv.policy else None)
    if owner_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this conversation.",
            )
        if owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this conversation.",
            )

    return conv_service.format_conversation_response(conv)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to the policy assistant",
)
def send_message(
    conversation_id: int = Path(..., gt=0, description="Database ID of the conversation"),
    payload: MessageCreate = ...,
    db: Session = Depends(get_db),
    conv_service: ConversationService = Depends(get_conversation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> ConversationMessageResponse:
    """Submit a question or treatment scenario to the conversational policy assistant."""
    repo = ConversationRepository(db)
    conv = repo.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation #{conversation_id} not found.",
        )

    owner_id = conv.user_id or (conv.policy.user_id if conv.policy else None)
    if owner_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to post messages to this conversation.",
            )
        if owner_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this conversation.",
            )

    try:
        assistant_msg = conv_service.post_message(
            db=db,
            conversation_id=conversation_id,
            content=payload.content,
            treatment_scenario=payload.treatment_scenario,
        )
        # Convert to response schema
        conv = repo.get_by_id(conversation_id)
        if conv:
            full_resp = conv_service.format_conversation_response(conv)
            for m in full_resp.messages:
                if m.id == assistant_msg.id:
                    return m

        return ConversationMessageResponse(
            id=assistant_msg.id,
            conversation_id=assistant_msg.conversation_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            confidence=assistant_msg.confidence,
            is_grounded=assistant_msg.is_grounded,
            uncertainty_reason=assistant_msg.uncertainty_reason,
            missing_information=assistant_msg.missing_information,
            treatment_scenario=assistant_msg.treatment_scenario,
            cost_estimate=assistant_msg.cost_estimate,
            evidence_references=[],
            created_at=assistant_msg.created_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/policy/{policy_id}",
    response_model=List[ConversationSummaryResponse],
    summary="List all conversations for a specific policy",
)
def list_conversations_for_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[ConversationSummaryResponse]:
    """Retrieve all conversations initiated for a given policy."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy #{policy_id} not found.",
        )

    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view conversations for this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view conversations for this policy.",
            )

    repo = ConversationRepository(db)
    convs = repo.list_by_policy(policy_id=policy_id, skip=skip, limit=limit)
    return [
        ConversationSummaryResponse(
            id=c.id,
            policy_id=c.policy_id,
            title=c.title,
            message_count=len(c.messages) if c.messages else 0,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in convs
    ]
