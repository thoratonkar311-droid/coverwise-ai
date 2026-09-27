import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.policy import Policy
from app.repositories.policy_repository import PolicyRepository
from app.schemas.policy import (
    PolicyCreate,
    PolicyResponse,
    PolicySummaryResponse,
    PolicyUpdate,
    PolicyUploadResponse,
)

logger = get_logger("coverwise.api.policies")

router = APIRouter(prefix="/policies", tags=["Policies"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB max limit


@router.get("", response_model=List[PolicySummaryResponse])
def list_policies(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    db: Session = Depends(get_db),
) -> List[PolicySummaryResponse]:
    """Retrieve paginated list of registered insurance policy documents."""
    repo = PolicyRepository(db)
    return repo.list(skip=skip, limit=limit)


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Retrieve a detailed policy document record by ID."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )
    return policy


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Register a new policy document record with metadata."""
    repo = PolicyRepository(db)
    policy = repo.create(
        filename=payload.filename,
        file_path=payload.file_path,
        user_id=payload.user_id,
        status=payload.status,
        insurer_name=payload.insurer_name,
        plan_name=payload.plan_name,
        policy_number=payload.policy_number,
        raw_metadata=payload.raw_metadata,
    )
    logger.info(f"Registered policy record ID {policy.id} ({policy.filename})")
    return policy


@router.post("/upload", response_model=PolicyUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_policy(
    file: UploadFile = File(..., description="Insurance policy PDF or document file (.pdf, .png, .jpg, .jpeg)"),
    insurer_name: Optional[str] = Form(None, description="Optional insurer name"),
    plan_name: Optional[str] = Form(None, description="Optional plan name"),
    policy_number: Optional[str] = Form(None, description="Optional policy number"),
    user_id: Optional[str] = Form(None, description="Optional user identifier"),
    db: Session = Depends(get_db),
) -> PolicyUploadResponse:
    """
    Upload an insurance policy document (PDF/image) for analysis.

    Validates file extension (.pdf, .png, .jpg, .jpeg) and size (<= 25MB).
    Saves the file securely and initializes the policy processing lifecycle.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    # Validate file extension
    raw_name = os.path.basename(file.filename)
    _, ext = os.path.splitext(raw_name)
    ext_lower = ext.lower()
    if ext_lower not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file format '{ext}'. Allowed formats are: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
        )

    # Prepare upload directory
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Prefix with short random ID to avoid filename collisions while preserving clean name
    safe_filename = f"{uuid.uuid4().hex[:8]}_{raw_name}"
    saved_path = os.path.join(upload_dir, safe_filename)

    # Stream file to disk and enforce size limit
    total_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunks
    try:
        with open(saved_path, "wb") as buffer:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(saved_path):
                        os.remove(saved_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        logger.error(f"Failed to save uploaded file '{safe_filename}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store uploaded policy document.",
        )

    if total_size == 0:
        if os.path.exists(saved_path):
            os.remove(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    # Create policy in database
    repo = PolicyRepository(db)
    policy = repo.create(
        filename=raw_name,
        file_path=saved_path,
        user_id=user_id,
        status="uploaded",
        insurer_name=insurer_name,
        plan_name=plan_name,
        policy_number=policy_number,
        raw_metadata={
            "content_type": file.content_type,
            "size_bytes": total_size,
            "stored_filename": safe_filename,
        },
    )

    logger.info(f"Policy file '{raw_name}' ({total_size} bytes) uploaded successfully as ID {policy.id}")
    return PolicyUploadResponse(
        id=policy.id,
        filename=policy.filename,
        status=policy.status,
        message="Policy document uploaded successfully.",
    )


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    payload: PolicyUpdate = ...,
    db: Session = Depends(get_db),
) -> PolicyResponse:
    """Update metadata or processing status of a policy document."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field_name, value)

    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_200_OK)
def delete_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a policy document and its associated analyses and simulations."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    # Remove stored physical file if present
    if policy.file_path and os.path.exists(policy.file_path):
        try:
            os.remove(policy.file_path)
        except OSError as exc:
            logger.warning(f"Could not remove local file '{policy.file_path}': {exc}")

    db.delete(policy)
    db.commit()
    logger.info(f"Deleted policy ID {policy_id}")
    return {"message": "Policy deleted successfully", "id": policy_id}
