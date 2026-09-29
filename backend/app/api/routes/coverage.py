from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.coverage_rule import CoverageRule
from app.models.policy import Policy
from app.models.user import User
from app.schemas.ai_contract import EvidenceQueryInput, EvidenceRetrievalOutput
from app.schemas.coverage_rule import CoverageRuleResponse
from app.schemas.evidence_reference import EvidenceReferenceResponse
from app.services.policy_analysis_service import (
    PolicyAnalysisServiceInterface,
    get_policy_analysis_service,
)

logger = get_logger("coverwise.api.coverage")

router = APIRouter(tags=["Coverage Intelligence"])


def _to_coverage_rule_response(rule: CoverageRule) -> CoverageRuleResponse:
    """Format CoverageRule model with evidence references."""
    evidence_list = [
        EvidenceReferenceResponse(
            id=ref.id,
            user_id=ref.user_id,
            policy_id=ref.policy_id,
            rule_id=ref.rule_id,
            analysis_id=ref.analysis_id,
            document_source=ref.document_source,
            page=ref.page,
            clause_section=ref.clause_section,
            extracted_text=ref.extracted_text,
            interpretation=ref.interpretation,
            confidence=ref.confidence,
            source_type=ref.source_type,
            created_at=ref.created_at,
        )
        for ref in (rule.evidence_references or [])
    ]

    return CoverageRuleResponse(
        id=rule.id,
        user_id=rule.user_id,
        policy_id=rule.policy_id,
        category=rule.category,
        procedure_name=rule.procedure_name,
        rule_name=rule.rule_name,
        coverage_status=rule.coverage_status,
        coverage_percentage=rule.coverage_percentage,
        coverage_limit_amount=rule.coverage_limit_amount,
        coverage_limit_percentage_of_si=rule.coverage_limit_percentage_of_si,
        unit_frequency=rule.unit_frequency,
        deductible=rule.deductible,
        deductible_status=rule.deductible_status,
        copay=rule.copay,
        copay_percentage=rule.copay_percentage,
        network_condition=rule.network_condition,
        waiting_period=rule.waiting_period,
        waiting_period_type=rule.waiting_period_type,
        coverage_limit=rule.coverage_limit or rule.coverage_limit_amount,
        exclusions=rule.exclusions,
        conditions=rule.conditions,
        room_category=rule.room_category,
        source_reference=rule.source_reference,
        source_type=rule.source_type,
        confidence=rule.confidence,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        evidence_references=evidence_list,
    )


@router.get(
    "/coverage",
    response_model=List[CoverageRuleResponse],
    summary="List coverage rules for a policy (Member 1 frontend route)",
)
@router.get(
    "/coverage/rules",
    response_model=List[CoverageRuleResponse],
    summary="List coverage rules alias",
    include_in_schema=False,
)
def list_coverage_rules(
    policy_id: Optional[int] = Query(None, gt=0, description="Optional policy ID to filter rules"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> List[CoverageRuleResponse]:
    """
    Retrieve structured coverage rules and policy restrictions for the active policy.
    """
    target_policy_id = policy_id
    if target_policy_id is None and current_user and current_user.active_policy_id:
        target_policy_id = current_user.active_policy_id

    if target_policy_id is None:
        return []

    policy = db.query(Policy).filter(Policy.id == target_policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {target_policy_id} not found.",
        )

    if current_user and policy.user_id and policy.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this policy's coverage rules.",
        )

    query = db.query(CoverageRule).filter(CoverageRule.policy_id == target_policy_id)
    rules = query.order_by(CoverageRule.created_at.desc()).offset(skip).limit(limit).all()
    return [_to_coverage_rule_response(r) for r in rules]


@router.get(
    "/coverage/{rule_id}",
    response_model=CoverageRuleResponse,
    summary="Get coverage rule details by ID",
)
def get_coverage_rule(
    rule_id: int = Path(..., gt=0, description="Database ID of the coverage rule"),
    db: Session = Depends(get_db),
) -> CoverageRuleResponse:
    """Retrieve an individual coverage rule and its verified evidence citations."""
    rule = db.query(CoverageRule).filter(CoverageRule.id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coverage rule with ID {rule_id} not found.",
        )
    return _to_coverage_rule_response(rule)


@router.post(
    "/coverage/query",
    response_model=EvidenceRetrievalOutput,
    summary="Query policy clauses and evidence citations via AI contract",
)
@router.post(
    "/coverage/evidence",
    response_model=EvidenceRetrievalOutput,
    include_in_schema=False,
)
def query_coverage_evidence(
    payload: EvidenceQueryInput,
    db: Session = Depends(get_db),
    analysis_service: PolicyAnalysisServiceInterface = Depends(get_policy_analysis_service),
) -> EvidenceRetrievalOutput:
    """
    Retrieve traceable clauses and citation snippets from indexed policy documents.

    Member 3 RAG search contract endpoint.
    """
    if payload.policy_id is not None:
        policy = db.query(Policy).filter(Policy.id == payload.policy_id).first()
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy with ID {payload.policy_id} not found.",
            )
        if not payload.document_source and policy.filename:
            payload.document_source = policy.filename

    return analysis_service.retrieve_evidence(payload)
