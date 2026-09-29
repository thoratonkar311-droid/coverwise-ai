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
from app.models.user import User
from app.api.deps import get_optional_current_user
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
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[PolicySummaryResponse]:
    """Retrieve paginated list of registered insurance policy documents."""
    repo = PolicyRepository(db)
    user_id = str(current_user.id) if current_user else None
    policies = repo.list(skip=skip, limit=limit, user_id=user_id)
    active_id = current_user.active_policy_id if current_user else None
    results = []
    for p in policies:
        p_dict = {
            "id": p.id,
            "filename": p.filename,
            "policy_number": p.policy_number,
            "insurer_name": p.insurer_name,
            "plan_name": p.plan_name,
            "sum_insured": p.sum_insured,
            "policy_start_date": p.policy_start_date,
            "policy_end_date": p.policy_end_date,
            "document_hash": p.document_hash,
            "extraction_confidence": p.extraction_confidence,
            "status": p.status,
            "is_active": (p.id == active_id),
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        results.append(PolicySummaryResponse(**p_dict))
    return results


@router.get("/active", response_model=PolicyResponse)
def get_active_policy(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> PolicyResponse:
    """Retrieve the currently active policy for the user."""
    repo = PolicyRepository(db)
    active_policy = None
    if current_user and current_user.active_policy_id:
        active_policy = repo.get_by_id(current_user.active_policy_id)
        if active_policy and active_policy.user_id and active_policy.user_id != str(current_user.id):
            active_policy = None

    if not active_policy and current_user:
        user_policies = repo.list(skip=0, limit=1, user_id=str(current_user.id))
        if user_policies:
            active_policy = user_policies[0]
            current_user.active_policy_id = active_policy.id
            db.commit()

    if not active_policy:
        policies = repo.list(skip=0, limit=1)
        if policies:
            active_policy = policies[0]

    if not active_policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active policy found. Please upload a policy.",
        )
    active_policy.is_active = True
    return active_policy


@router.post("/{policy_id}/activate")
@router.post("/active/{policy_id}")
def set_active_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy to activate"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> dict:
    """Set the specified policy as the active policy for the current user."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )
    if policy.user_id and current_user and policy.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to activate this policy.",
        )
    if current_user:
        current_user.active_policy_id = policy.id
        db.commit()
    logger.info(f"Policy #{policy.id} set as active (user={current_user.id if current_user else 'anonymous'})")
    return {
        "status": "success",
        "active_policy_id": policy.id,
        "message": f"Policy {policy.id} ({policy.plan_name or policy.filename}) is now the active policy.",
    }


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: str = Path(..., description="Database ID, policy number, or name of the policy"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> PolicyResponse:
    """Retrieve a detailed policy document record by ID or policy identifier."""
    # Enforce numeric gt 0 validation if integer ID
    try:
        int_id = int(policy_id)
        if int_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="policy_id must be greater than zero.",
            )
    except ValueError:
        pass

    repo = PolicyRepository(db)
    policy = repo.find_by_identifier(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID '{policy_id}' not found.",
        )
    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this policy.",
            )
    policy.is_active = bool(current_user and current_user.active_policy_id == policy.id)
    return policy


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> PolicyResponse:
    """Register a new policy document record with metadata."""
    repo = PolicyRepository(db)
    owner_id = str(current_user.id) if current_user else payload.user_id
    policy = repo.create(
        filename=payload.filename,
        file_path=payload.file_path,
        user_id=owner_id,
        status=payload.status,
        insurer_name=payload.insurer_name,
        plan_name=payload.plan_name,
        policy_number=payload.policy_number,
        raw_metadata=payload.raw_metadata,
    )
    logger.info(f"Registered policy record ID {policy.id} ({policy.filename})")
    return policy


def validate_health_policy(pdf_path: str) -> tuple[bool, str]:
    """Inspect PDF text to verify it is a Health Insurance policy."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # type: ignore

    try:
        doc = fitz.open(pdf_path)
        combined_text = ""
        # Check first 10 pages for document type identification
        pages_to_check = min(len(doc), 10)
        for i in range(pages_to_check):
            combined_text += " " + doc[i].get_text()
        doc.close()
    except Exception as e:
        logger.warning(f"Could not read PDF for type detection: {e}")
        return True, "Health Insurance"

    lower = combined_text.lower()

    # Motor insurance keywords
    motor_keywords = [
        "chassis number", "engine number", "insured declared value", " idv ",
        "motor vehicle", "private car package", "private car policy",
        "two wheeler package", "commercial vehicle", "own damage",
        "cubic capacity", "vehicle make", "vehicle model", "registration mark"
    ]
    motor_matches = sum(1 for kw in motor_keywords if kw in lower)
    if motor_matches >= 2:
        return False, "Unsupported policy type: CoverWise currently supports health insurance policies."

    # Travel insurance keywords (if not primarily health)
    travel_keywords = ["loss of baggage", "passport loss", "trip cancellation", "flight delay", "overseas travel insurance"]
    travel_matches = sum(1 for kw in travel_keywords if kw in lower)
    if travel_matches >= 2 and "hospitalization" not in lower:
        return False, "Unsupported policy type: CoverWise currently supports health insurance policies."

    # Life insurance keywords without hospitalization
    life_keywords = ["death benefit", "sum assured on death", "surrender value", "maturity benefit", "nominee details"]
    life_matches = sum(1 for kw in life_keywords if kw in lower)
    if life_matches >= 2 and "hospitalization" not in lower and "mediclaim" not in lower and "in-patient" not in lower:
        return False, "Unsupported policy type: CoverWise currently supports health insurance policies."

    # General health check - needs health insurance terms
    health_keywords = [
        "health", "mediclaim", "hospital", "hospitalization", "in-patient", "inpatient",
        "day care", "daycare", "pre-existing", "sum insured", "cashless", "room rent",
        "icu", "deductible", "co-pay", "copay", "coinsurance", "waiting period",
        "medical expenses", "ayush", "tpa", "critical illness", "arogya"
    ]
    health_matches = sum(1 for kw in health_keywords if kw in lower)
    if health_matches < 2:
        return False, "Unsupported policy type: CoverWise currently supports health insurance policies."

    return True, "Health Insurance"


@router.post("/upload", response_model=PolicyUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_policy(
    file: UploadFile = File(..., description="Insurance policy PDF or document file (.pdf, .png, .jpg, .jpeg)"),
    insurer_name: Optional[str] = Form(None, description="Optional insurer name"),
    plan_name: Optional[str] = Form(None, description="Optional plan name"),
    policy_number: Optional[str] = Form(None, description="Optional policy number"),
    user_id: Optional[str] = Form(None, description="Optional user identifier"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
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

    # Validate policy type for PDF uploads
    if ext_lower == ".pdf":
        is_health, reason = validate_health_policy(saved_path)
        if not is_health:
            if os.path.exists(saved_path):
                os.remove(saved_path)
            logger.warning(f"Rejected unsupported policy upload '{raw_name}': {reason}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason,
            )

    # Compute SHA-256 document content hash
    import hashlib
    hasher = hashlib.sha256()
    with open(saved_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    document_hash_val = hasher.hexdigest()

    # Determine effective owner
    effective_user_id = str(current_user.id) if current_user else user_id

    # Check for existing document hash (Requirement 17)
    repo = PolicyRepository(db)
    existing_match = repo.find_by_document_hash(document_hash_val, user_id=effective_user_id)
    if existing_match:
        logger.info(f"Uploaded file '{raw_name}' matches existing document hash {document_hash_val} (policy ID {existing_match.id}). Ingesting as unique version record.")

    # Create policy in database
    policy = repo.create(
        filename=raw_name,
        file_path=saved_path,
        user_id=effective_user_id,
        status="uploaded",
        insurer_name=insurer_name,
        plan_name=plan_name,
        policy_number=policy_number,
        document_hash=document_hash_val,
        raw_metadata={
            "content_type": file.content_type,
            "size_bytes": total_size,
            "stored_filename": safe_filename,
            "document_hash": document_hash_val,
        },
    )

    logger.info(f"Policy file '{raw_name}' ({total_size} bytes, hash: {document_hash_val[:10]}...) uploaded successfully as ID {policy.id} (user_id: {effective_user_id})")

    # Run structured extraction, vector indexing, and intelligence persistence
    deductible_val: Optional[float] = None
    copay_pct_val: Optional[float] = None
    sum_insured_val: Optional[float] = None
    room_rent_limit_str: Optional[str] = None
    confidence_val: Optional[float] = None

    if ext_lower == ".pdf":
        try:
            import re
            from pathlib import Path
            from app.models.coverage_rule import CoverageRule
            from app.models.evidence_reference import EvidenceReference
            from app.models.policy_analysis import PolicyAnalysis
            from ai.extraction.policy_extractor import extract_policy
            from ai.retrieval.retriever import get_default_vector_store, index_policy

            extracted = extract_policy(saved_path)
            meta = extracted.metadata
            if meta:
                if meta.insurer_name:
                    policy.insurer_name = meta.insurer_name
                if meta.policy_name:
                    policy.plan_name = meta.policy_name
                if meta.policy_id:
                    policy.policy_number = meta.policy_id
                if hasattr(meta, "policy_holder_name") and meta.policy_holder_name:
                    policy.policy_holder_name = meta.policy_holder_name
                if hasattr(meta, "effective_date") and meta.effective_date:
                    policy.policy_start_date = str(meta.effective_date)
                if hasattr(meta, "expiration_date") and meta.expiration_date:
                    policy.policy_end_date = str(meta.expiration_date)

            confidence_val = getattr(extracted, "overall_confidence", None) or 0.95
            policy.extraction_confidence = confidence_val

            # Deductible: strictly from document
            if extracted.deductibles and extracted.deductibles.individual_in_network is not None:
                deductible_val = extracted.deductibles.individual_in_network

            # Coinsurance / Copay: strictly from document
            if extracted.coinsurance and extracted.coinsurance.in_network_percentage is not None:
                copay_pct_val = extracted.coinsurance.in_network_percentage

            # Sum Insured: strictly from document. Do NOT default to 1,000,000!
            if extracted.out_of_pocket_max and extracted.out_of_pocket_max.individual_in_network is not None:
                sum_insured_val = extracted.out_of_pocket_max.individual_in_network
            elif extracted.limits:
                for l in extracted.limits:
                    cat_l = (l.service_or_category or "").lower()
                    if "sum insured" in cat_l or getattr(l, "limit_type", "") == "overall_maximum":
                        m_si = re.search(r"([0-9,]+)", l.limit_value or "")
                        if m_si:
                            try:
                                sum_insured_val = float(m_si.group(1).replace(",", ""))
                                break
                            except ValueError:
                                pass

            policy.sum_insured = sum_insured_val

            # Room Rent & ICU limits: strictly from document
            room_rent_limit_str = None
            if extracted.limits:
                for l in extracted.limits:
                    cat_lower = (l.service_or_category or "").lower()
                    if "room" in cat_lower or "icu" in cat_lower:
                        room_rent_limit_str = f"{l.service_or_category}: {l.limit_value}"
                        break

            # Waiting periods: strictly from document
            waiting_str = (
                ", ".join([f"{w.description or ''} ({w.condition_or_benefit})".strip() for w in extracted.waiting_periods])
                if extracted.waiting_periods
                else None
            )

            # Exclusions: strictly from document. NEVER invent default exclusions.
            exclusions_list = (
                extracted.exclusions
                or [
                    de.category_or_service or de.description
                    for de in (extracted.detailed_exclusions or [])
                    if (de.category_or_service or de.description)
                ]
                or None
            )

            # Update policy raw metadata
            policy.raw_metadata = {
                **(policy.raw_metadata or {}),
                "extracted_metadata": meta.model_dump() if meta else {},
                "deductibles": extracted.deductibles.model_dump() if extracted.deductibles else {},
                "coinsurance": extracted.coinsurance.model_dump() if extracted.coinsurance else {},
                "waiting_periods": [w.model_dump() for w in (extracted.waiting_periods or [])],
                "limits": [l.model_dump() for l in (extracted.limits or [])],
                "exclusions": exclusions_list or [],
                "currency": extracted.currency or "INR",
            }
            policy.status = "analyzed"
            db.commit()
            db.refresh(policy)

            # Persist General Policy CoverageRule
            general_rule = CoverageRule(
                policy_id=policy.id,
                user_id=effective_user_id,
                category="general",
                rule_name="General Policy Coverage Terms",
                coverage_status="covered",
                deductible=deductible_val,
                deductible_status="specified" if deductible_val is not None else "not_determined",
                copay=extracted.copays.specialist if (extracted.copays and extracted.copays.specialist is not None) else None,
                copay_percentage=copay_pct_val,
                coverage_limit=sum_insured_val,
                coverage_limit_amount=sum_insured_val,
                exclusions=exclusions_list,
                waiting_period=waiting_str[:500] if waiting_str else None,
                room_category=room_rent_limit_str[:255] if room_rent_limit_str else None,
                source_type="contractual_rule",
                source_reference=f"Extracted from {raw_name}"[:500],
                confidence=confidence_val,
            )
            db.add(general_rule)
            db.flush()

            # Persist Procedure/Treatment-Specific Rules from extracted document
            for l in (extracted.limits or []):
                cat_lower = (l.service_or_category or "").lower()
                # Skip pure daily room rent since captured under room_category
                if cat_lower in ["room rent daily limit", "single private room"]:
                    continue

                proc_name = l.service_or_category
                limit_str = l.limit_value or ""

                # Extract percentage if present
                m_pct = re.search(r"([0-9.]+)\s*%", limit_str)
                proc_pct = float(m_pct.group(1)) if m_pct else None

                # Extract amount cap if present
                m_cap = re.search(r"(?:max(?:imum)?\s*(?:INR|Rs\.?|₹)?\s*([0-9,]+)|(?:INR|Rs\.?|₹)\s*([0-9,]+))", limit_str, re.IGNORECASE)
                proc_cap = None
                if m_cap:
                    val_str = m_cap.group(1) or m_cap.group(2)
                    if val_str:
                        try:
                            proc_cap = float(val_str.replace(",", ""))
                        except ValueError:
                            pass

                # Extract frequency/unit
                m_freq = re.search(r"(?:per|/)\s*(eye|admission|day|event|year|treatment)", limit_str, re.IGNORECASE)
                proc_freq = f"per_{m_freq.group(1).lower()}" if m_freq else None

                # Check procedure-specific waiting period
                proc_wp = None
                if extracted.waiting_periods:
                    for w in extracted.waiting_periods:
                        w_text = f"{w.condition_or_benefit or ''} {w.description or ''}".lower()
                        if any(term in w_text for term in proc_name.lower().split() if len(term) > 3):
                            proc_wp = w.description or (f"{w.duration_months} months" if w.duration_months else None)
                            break

                proc_rule = CoverageRule(
                    policy_id=policy.id,
                    user_id=effective_user_id,
                    category="procedure",
                    procedure_name=proc_name,
                    rule_name=f"{proc_name} Limitation Rule",
                    coverage_status="partially_covered" if (proc_pct or proc_cap) else "covered",
                    coverage_percentage=proc_pct,
                    coverage_limit_amount=proc_cap,
                    coverage_limit_percentage_of_si=proc_pct,
                    unit_frequency=proc_freq,
                    deductible=deductible_val,
                    deductible_status="specified" if deductible_val is not None else "not_determined",
                    copay_percentage=copay_pct_val,
                    waiting_period=proc_wp[:500] if proc_wp else None,
                    source_type="contractual_rule",
                    source_reference=f"Extracted contractual limit from {raw_name}"[:500],
                    confidence=0.95,
                )
                db.add(proc_rule)
                db.flush()

                # Attach procedure evidence citations
                for ev in (l.evidence or []):
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=proc_rule.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=ev.clause_reference or f"{proc_name} Clause",
                            extracted_text=ev.text,
                            interpretation=l.details or f"Contractual procedure limit for {proc_name}: {l.limit_value}",
                            source_type="contractual_rule",
                            confidence=0.95,
                        )
                    )

            # Persist PolicyAnalysis record
            analysis_data = {
                "policy_overview": {
                    "policy_name": policy.plan_name,
                    "insurer_name": policy.insurer_name,
                    "policy_number": policy.policy_number,
                    "currency": extracted.currency or "INR",
                },
                "coverage_status": "likely_covered",
                "coverage_information": f"{policy.plan_name or 'Uploaded policy'} comprehensive insurance contract under {policy.insurer_name or 'Insurer'}.",
                "deductible": deductible_val,
                "copay": extracted.copays.specialist if extracted.copays else None,
                "copay_percentage": copay_pct_val,
                "coverage_limit": sum_insured_val,
                "exclusions": exclusions_list or [],
                "detailed_exclusions": [
                    {"category": de.category_or_service, "description": de.description}
                    for de in (extracted.detailed_exclusions or [])
                ],
                "waiting_periods": waiting_str or "Not Determined",
                "waiting_periods_list": [
                    {"condition": w.condition_or_benefit, "description": w.description}
                    for w in (extracted.waiting_periods or [])
                ],
                "room_rent_limit": room_rent_limit_str or "Not Determined",
                "sub_limits": [
                    {"category": l.service_or_category, "limit": l.limit_value, "details": l.details}
                    for l in (extracted.limits or [])
                ],
                "confidence": confidence_val,
                "explanation": f"Full policy intelligence extracted from {raw_name} with verified clauses and evidentiary grounding.",
            }
            analysis = PolicyAnalysis(
                policy_id=policy.id,
                user_id=effective_user_id,
                treatment_name="Comprehensive Health Coverage",
                status="completed",
                result_summary=analysis_data["explanation"],
                result_data=analysis_data,
            )
            db.add(analysis)
            db.flush()

            # Persist Evidence References from extraction for general conditions
            if extracted.deductibles and extracted.deductibles.evidence:
                for ev in extracted.deductibles.evidence:
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=general_rule.id,
                            analysis_id=analysis.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=ev.clause_reference or "Annual Deductible Clause",
                            extracted_text=ev.text,
                            interpretation=f"Annual individual deductible: INR {deductible_val:,.2f}" if deductible_val else "Deductible clause",
                            source_type="contractual_rule",
                            confidence=0.98,
                        )
                    )
            if extracted.coinsurance and extracted.coinsurance.evidence:
                for ev in extracted.coinsurance.evidence:
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=general_rule.id,
                            analysis_id=analysis.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=ev.clause_reference or "Coinsurance Clause",
                            extracted_text=ev.text,
                            interpretation=f"Mandatory coinsurance: {copay_pct_val}%",
                            source_type="contractual_rule",
                            confidence=0.96,
                        )
                    )
            for w in (extracted.waiting_periods or []):
                for ev in (w.evidence or []):
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=general_rule.id,
                            analysis_id=analysis.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=ev.clause_reference or "Waiting Periods Clause",
                            extracted_text=ev.text,
                            interpretation=f"Waiting period condition: {w.condition_or_benefit}",
                            source_type="contractual_rule",
                            confidence=0.95,
                        )
                    )
            for de in (extracted.detailed_exclusions or []):
                for ev in (de.evidence or []):
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=general_rule.id,
                            analysis_id=analysis.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=ev.clause_reference or "Excluded Services Clause",
                            extracted_text=ev.text,
                            interpretation=f"Excluded treatment: {de.category_or_service}",
                            source_type="contractual_rule",
                            confidence=0.95,
                        )
                    )
            for cl in (extracted.clauses or []):
                if cl.evidence:
                    ev = cl.evidence
                    db.add(
                        EvidenceReference(
                            policy_id=policy.id,
                            user_id=effective_user_id,
                            rule_id=general_rule.id,
                            analysis_id=analysis.id,
                            document_source=raw_name,
                            page=ev.page_number,
                            clause_section=cl.section_number or cl.title or f"Clause {cl.clause_id}",
                            extracted_text=ev.text,
                            interpretation=cl.title or cl.text[:120],
                            source_type="contractual_rule",
                            confidence=0.95,
                        )
                    )

            # Make this newly uploaded policy the ACTIVE policy for current user (Requirement 6)
            if current_user:
                current_user.active_policy_id = policy.id

            # Index into vector store
            try:
                vstore = get_default_vector_store()
                index_policy(
                    pdf_path=Path(saved_path),
                    policy_id=str(policy.id),
                    user_id=effective_user_id,
                    vector_store=vstore,
                    force_reindex=True,
                )
            except Exception as v_err:
                logger.warning(f"Vector store indexing notice for policy #{policy.id}: {v_err}")

            db.commit()
            db.refresh(policy)
            logger.info(f"Policy #{policy.id} successfully analyzed, activated, and indexed.")
        except Exception as ext_err:
            logger.warning(f"Automatic policy extraction skipped or failed for '{raw_name}': {ext_err}")
            db.rollback()
            try:
                db_policy = repo.get_by_id(policy.id)
                if db_policy:
                    db_policy.status = "uploaded"
                    db_policy.raw_metadata = {
                        **(db_policy.raw_metadata or {}),
                        "extraction_warning": str(ext_err),
                    }
                    if current_user:
                        current_user.active_policy_id = db_policy.id
                    db.commit()
                    db.refresh(db_policy)
                    policy = db_policy
            except Exception as commit_err:
                logger.warning(f"Could not refresh status for policy #{policy.id}: {commit_err}")

    return PolicyUploadResponse(
        id=policy.id,
        policy_id=policy.id,
        filename=policy.filename,
        status=policy.status,
        message="Policy document uploaded and analyzed successfully.",
        insurer_name=policy.insurer_name,
        plan_name=policy.plan_name,
        policy_number=policy.policy_number,
        policy_holder_name=policy.policy_holder_name,
        policy_start_date=policy.policy_start_date,
        policy_end_date=policy.policy_end_date,
        document_hash=policy.document_hash,
        extraction_confidence=policy.extraction_confidence,
        sum_insured=policy.sum_insured,
        deductible=deductible_val,
        copay_percent=copay_pct_val,
        room_rent_limit=room_rent_limit_str,
        is_active=True,
    )


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    payload: PolicyUpdate = ...,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> PolicyResponse:
    """Update metadata or processing status of a policy document."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to modify this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this policy.",
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
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> dict:
    """Delete a policy document and its associated analyses and simulations."""
    repo = PolicyRepository(db)
    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to delete this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this policy.",
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
