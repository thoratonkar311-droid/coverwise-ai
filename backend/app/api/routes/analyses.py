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

logger = get_logger("coverwise.api.analyses")

router = APIRouter(tags=["Coverage Analysis"])


def _to_analysis_detail(analysis: PolicyAnalysis) -> AnalysisDetailResponse:
    """Format PolicyAnalysis database model into granular AnalysisDetailResponse."""
    data = analysis.result_data or {}
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
        for ref in (analysis.evidence_references or [])
    ]

    return AnalysisDetailResponse(
        id=analysis.id,
        policy_id=analysis.policy_id,
        treatment_id=analysis.treatment_id,
        treatment_name=analysis.treatment_name or "Unknown Treatment",
        status=analysis.status,
        coverage_status=data.get("coverage_status", "not_determined"),
        coverage_information=data.get("coverage_information", "No coverage information available."),
        deductible=data.get("deductible"),
        copay=data.get("copay"),
        copay_percentage=data.get("copay_percentage"),
        coverage_limit=data.get("coverage_limit"),
        exclusions=data.get("exclusions") or [],
        waiting_periods=data.get("waiting_periods"),
        confidence=float(data.get("confidence", 0.0)),
        explanation=data.get("explanation", analysis.result_summary or ""),
        evidence_references=evidence_list,
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
) -> AnalysisDetailResponse:
    """
    Run AI / Rules-based coverage analysis for a specific medical treatment.

    Extracts coverage status, applicable sub-limits, deductibles, co-pays, exclusions,
    and returns verified evidence clauses citing document sources.
    Idempotent by default: repeated requests for the same policy and treatment return the cached result
    unless force_refresh is True.
    """
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(payload.policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {payload.policy_id} not found.",
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

    result_data = {
        "coverage_status": analysis_output.coverage_status,
        "coverage_information": analysis_output.coverage_information,
        "deductible": analysis_output.deductible,
        "copay": analysis_output.copay,
        "copay_percentage": analysis_output.copay_percentage,
        "coverage_limit": analysis_output.coverage_limit,
        "exclusions": analysis_output.exclusions,
        "waiting_periods": analysis_output.waiting_periods,
        "confidence": analysis_output.confidence,
        "explanation": analysis_output.explanation,
        "raw_ai_metadata": analysis_output.raw_ai_metadata,
    }

    # Persist PolicyAnalysis record
    analysis = PolicyAnalysis(
        policy_id=policy.id,
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
            analysis_id=analysis.id,
            document_source=item.document_source,
            page=item.page,
            clause_section=item.clause_section,
            extracted_text=item.extracted_text,
            interpretation=item.interpretation,
            confidence=item.confidence,
        )
        db.add(evidence)

    # Persist/update CoverageRule if definitive parameters were derived
    if analysis_output.coverage_status in ("likely_covered", "partially_covered"):
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
    "/analyses/{analysis_id}",
    response_model=AnalysisDetailResponse,
    summary="Get analysis details by ID",
)
def get_analysis(
    analysis_id: int = Path(..., gt=0, description="Database ID of the analysis"),
    db: Session = Depends(get_db),
) -> AnalysisDetailResponse:
    """Retrieve an existing policy analysis record by its primary ID."""
    repo = AnalysisRepository(db)
    analysis = repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found.",
        )
    return _to_analysis_detail(analysis)


@router.get(
    "/policies/{policy_id}/analyses",
    response_model=List[AnalysisDetailResponse],
    summary="List all analyses for a policy",
)
def list_analyses_for_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    db: Session = Depends(get_db),
) -> List[AnalysisDetailResponse]:
    """Retrieve all historical analyses generated for a specific policy."""
    policy_repo = PolicyRepository(db)
    if not policy_repo.get_by_id(policy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    analysis_repo = AnalysisRepository(db)
    analyses = analysis_repo.list_by_policy(policy_id)
    return [_to_analysis_detail(item) for item in analyses]
