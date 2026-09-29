from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.coverage_rule import CoverageRule
from app.models.evidence_reference import EvidenceReference
from app.models.policy import Policy
from app.models.policy_analysis import PolicyAnalysis
from app.models.treatment import Treatment
from app.models.user import User
from app.api.deps import get_optional_current_user
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.policy_repository import PolicyRepository
from app.schemas.evidence_reference import EvidenceReferenceResponse
from app.schemas.policy_analysis import (
    AnalysisDetailResponse,
    AnalysisRequest,
    AnalysisResponse,
)
from app.services.policy_analysis_service import (
    PolicyAnalysisServiceInterface,
    get_policy_analysis_service,
)
from app.services.treatment_catalog_service import get_treatment_catalog_service

logger = get_logger("coverwise.api.analyses")

router = APIRouter(tags=["Coverage Analysis"])


def _to_analysis_detail(analysis: PolicyAnalysis) -> AnalysisDetailResponse:
    """Format PolicyAnalysis database model into granular AnalysisDetailResponse."""
    data = analysis.result_data or {}
    evidence_refs = list(analysis.evidence_references or [])
    if not evidence_refs and analysis.policy and analysis.policy.evidence_references:
        # Fall back to policy's verified evidence references so evidence count is never 0
        evidence_refs = list(analysis.policy.evidence_references)

    evidence_list = [
        EvidenceReferenceResponse(
            id=ref.id,
            policy_id=ref.policy_id,
            rule_id=ref.rule_id,
            analysis_id=ref.analysis_id,
            document_source=ref.document_source,
            page=ref.page,
            clause_section=ref.clause_section,
            extracted_text=ref.extracted_text,
            interpretation=ref.interpretation,
            confidence=ref.confidence,
            created_at=ref.created_at,
        )
        for ref in evidence_refs
    ]

    cov_pct = data.get("coverage_percentage")
    if cov_pct is None:
        cov_pct = data.get("coverage_limit_percentage_of_si")

    deductible_val = data.get("deductible")
    ded_status = data.get("deductible_status") or ("determined" if deductible_val is not None else "not_determined")
    if ded_status == "not_determined":
        deductible_val = None

    cov_limit = data.get("coverage_limit")

    return AnalysisDetailResponse(
        id=analysis.id,
        policy_id=analysis.policy_id,
        treatment_id=analysis.treatment_id,
        treatment_name=analysis.treatment_name or "Unknown Treatment",
        status=analysis.status,
        coverage_status=data.get("coverage_status", "not_determined"),
        coverage_information=data.get("coverage_information", "No coverage information available."),
        coverage_percentage=cov_pct,
        coverage_limit_percentage_of_si=cov_pct,
        policy_coverage_cap=cov_limit,
        deductible=deductible_val,
        deductible_status=ded_status,
        is_conditional_on_deductible=(ded_status == "not_determined"),
        copay=data.get("copay"),
        copay_percentage=data.get("copay_percentage"),
        coverage_limit=cov_limit,
        exclusions=data.get("exclusions") or [],
        waiting_periods=data.get("waiting_periods"),
        confidence=float(data.get("confidence", 0.0)),
        explanation=data.get("explanation", analysis.result_summary or ""),
        evidence_references=evidence_list,
        estimated_total_cost=data.get("estimated_total_cost"),
        estimated_insurer_share=data.get("estimated_insurer_share"),
        estimated_patient_share=data.get("estimated_patient_share"),
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
    )


@router.post(
    "/analyses",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze treatment coverage against an insurance policy",
)
@router.post(
    "/analysis",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/analyze",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze treatment coverage (Member 1 frontend alias)",
)
def run_analysis(
    payload: AnalysisRequest,
    db: Session = Depends(get_db),
    analysis_service: PolicyAnalysisServiceInterface = Depends(get_policy_analysis_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> AnalysisDetailResponse:
    """
    Run AI / Rules-based coverage analysis for a specific medical treatment.

    Extracts coverage status, applicable sub-limits, deductibles, co-pays, exclusions,
    and returns verified evidence clauses citing document sources.
    Idempotent by default: repeated requests for the same policy and treatment return the cached result
    unless force_refresh is True.
    """
    policy_repo = PolicyRepository(db)
    resolved_policy_id = payload.policy_id
    if (not resolved_policy_id or resolved_policy_id <= 0) and current_user and current_user.active_policy_id:
        resolved_policy_id = current_user.active_policy_id

    policy = policy_repo.get_by_id(resolved_policy_id) if resolved_policy_id else None
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {resolved_policy_id or payload.policy_id} not found.",
        )

    effective_user_id = str(current_user.id) if current_user else policy.user_id
    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to analyze this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to analyze this policy.",
            )

    analysis_repo = AnalysisRepository(db)
    # Check for existing completed analysis (Idempotency)
    if not payload.force_refresh:
        existing_analysis = analysis_repo.find_recent_by_policy_and_treatment(
            policy_id=policy.id,
            treatment_name=payload.treatment_name,
        )
        if existing_analysis:
            logger.info(
                f"Returning cached analysis #{existing_analysis.id} for policy #{policy.id}, treatment '{payload.treatment_name}'"
            )
            return _to_analysis_detail(existing_analysis)

    # Optional treatment linkage
    treatment_id = payload.treatment_id
    if not treatment_id:
        existing_treatment = (
            db.query(Treatment)
            .filter(Treatment.name.ilike(payload.treatment_name.strip()))
            .first()
        )
        if existing_treatment:
            treatment_id = existing_treatment.id

    # Execute policy intelligence analysis
    analysis_output = analysis_service.analyze_coverage(
        policy=policy,
        treatment_name=payload.treatment_name,
        db=db,
    )

    # Derive deterministic financial estimates via authoritative CalculationService
    catalog = get_treatment_catalog_service()
    matched_treatment = catalog.find_treatment(payload.treatment_name)
    typical_cost = float(matched_treatment["typical_cost"]) if matched_treatment else None

    # Benchmark vs Actual Hospital Quote (Requirement 12):
    # Benchmark typical cost is NEVER automatically fed into claim calculation.
    # Claim calculation requires an actual quote.
    quoted_cost = getattr(payload, "hospital_quote", None)
    est_total_cost = float(quoted_cost) if (quoted_cost is not None and quoted_cost > 0) else None
    est_insurer_share = None
    est_patient_share = None

    if est_total_cost is not None and analysis_output.coverage_status in ("covered", "likely_covered", "partially_covered"):
        from app.services.calculation_service import CalculationInput, CalculationService, PolicyRulesInput
        calc_res = CalculationService.calculate(
            calc_input=CalculationInput(
                hospital_quote=est_total_cost,
                is_network_hospital=True,
                procedure_name=payload.treatment_name,
            ),
            rules=PolicyRulesInput(
                deductible=analysis_output.deductible,
                deductible_status=analysis_output.deductible_status or ("determined" if analysis_output.deductible is not None else "not_determined"),
                copay_percentage=analysis_output.copay_percentage,
                network_copay_percentage=analysis_output.copay_percentage,
                coverage_limit=analysis_output.coverage_limit,
                coverage_limit_percentage_of_si=analysis_output.coverage_percentage or analysis_output.coverage_limit_percentage_of_si,
                sum_insured=policy.sum_insured,
                absolute_cap=analysis_output.coverage_limit,
                coverage_status=analysis_output.coverage_status,
                has_policy_rules=True,
            ),
        )
        est_insurer_share = calc_res.estimated_insurance_share
        est_patient_share = calc_res.estimated_patient_share
    elif analysis_output.coverage_status == "not_covered" and est_total_cost is not None:
        est_insurer_share = 0.0
        est_patient_share = est_total_cost

    result_data = {
        "coverage_status": analysis_output.coverage_status,
        "coverage_information": analysis_output.coverage_information,
        "coverage_percentage": analysis_output.coverage_percentage,
        "coverage_limit_percentage_of_si": analysis_output.coverage_limit_percentage_of_si or analysis_output.coverage_percentage,
        "deductible": analysis_output.deductible,
        "deductible_status": analysis_output.deductible_status or ("determined" if analysis_output.deductible is not None else "not_determined"),
        "copay": analysis_output.copay,
        "copay_percentage": analysis_output.copay_percentage,
        "coverage_limit": analysis_output.coverage_limit,
        "exclusions": analysis_output.exclusions,
        "waiting_periods": analysis_output.waiting_periods,
        "confidence": analysis_output.confidence,
        "explanation": analysis_output.explanation,
        "raw_ai_metadata": analysis_output.raw_ai_metadata,
        "benchmark_typical_cost": typical_cost,
        "estimated_total_cost": est_total_cost,
        "estimated_insurer_share": est_insurer_share,
        "estimated_patient_share": est_patient_share,
    }

    # Persist PolicyAnalysis record
    analysis = PolicyAnalysis(
        policy_id=policy.id,
        user_id=effective_user_id,
        treatment_id=treatment_id,
        treatment_name=payload.treatment_name,
        status="completed",
        result_summary=analysis_output.explanation,
        result_data=result_data,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Persist Evidence References
    for item in analysis_output.evidence_references:
        evidence = EvidenceReference(
            policy_id=policy.id,
            user_id=effective_user_id,
            analysis_id=analysis.id,
            document_source=item.document_source,
            page=item.page,
            clause_section=item.clause_section,
            extracted_text=item.extracted_text,
            interpretation=item.interpretation,
            confidence=item.confidence,
            source_type=getattr(item, "source_type", "contractual_rule") or "contractual_rule",
        )
        db.add(evidence)

    # Persist/update CoverageRule if definitive parameters were derived
    if analysis_output.coverage_status in ("covered", "likely_covered", "partially_covered"):
        rule = CoverageRule(
            policy_id=policy.id,
            coverage_status=analysis_output.coverage_status,
            deductible=analysis_output.deductible,
            copay=analysis_output.copay,
            copay_percentage=analysis_output.copay_percentage,
            coverage_limit=analysis_output.coverage_limit,
            exclusions=analysis_output.exclusions,
            waiting_period=analysis_output.waiting_periods,
            source_reference=f"Analysis #{analysis.id}: {payload.treatment_name}",
        )
        db.add(rule)

    db.commit()
    db.refresh(analysis)

    logger.info(
        f"Completed coverage analysis #{analysis.id} for policy #{policy.id}, treatment '{payload.treatment_name}' "
        f"[status: {analysis_output.coverage_status}, confidence: {analysis_output.confidence}]"
    )

    return _to_analysis_detail(analysis)


@router.get(
    "/analyses/recent",
    response_model=List[AnalysisDetailResponse],
    summary="List most recent coverage analyses",
)
def get_recent_analyses(
    limit: int = Query(10, ge=1, le=50, description="Max recent items to return"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[AnalysisDetailResponse]:
    """Retrieve recent coverage analyses across all policies."""
    repo = AnalysisRepository(db)
    user_id = str(current_user.id) if current_user else None
    recent = repo.list_recent(limit=limit, user_id=user_id)
    return [_to_analysis_detail(item) for item in recent]


@router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Get analysis details by ID",
)
def get_analysis(
    analysis_id: int = Path(..., gt=0, description="Database ID of the analysis"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> AnalysisDetailResponse:
    """Retrieve an existing policy analysis record by its primary ID."""
    repo = AnalysisRepository(db)
    analysis = repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found.",
        )
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(analysis.policy_id)
    if policy and policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this analysis.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this analysis.",
            )
    return _to_analysis_detail(analysis)


@router.get(
    "/policies/{policy_id}/analyses",
    response_model=List[AnalysisDetailResponse],
    summary="List all analyses for a policy",
)
@router.get(
    "/analyses/policy/{policy_id}",
    response_model=List[AnalysisDetailResponse],
    summary="List all analyses for a policy (alias)",
    include_in_schema=False,
)
@router.get(
    "/policy/{policy_id}/analyses",
    response_model=List[AnalysisDetailResponse],
    summary="List all analyses for a policy (singular alias)",
    include_in_schema=False,
)
def list_analyses_for_policy(
    policy_id: str = Path(..., description="Database ID or identifier of the policy"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[AnalysisDetailResponse]:
    """Retrieve all historical analyses generated for a specific policy."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.find_by_identifier(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID '{policy_id}' not found.",
        )

    if policy.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view analyses for this policy.",
            )
        if policy.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view analyses for this policy.",
            )

    analysis_repo = AnalysisRepository(db)
    analyses = analysis_repo.list_by_policy(policy.id)
    return [_to_analysis_detail(item) for item in analyses]

