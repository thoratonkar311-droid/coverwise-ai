from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.policy import Policy
from app.models.policy_analysis import PolicyAnalysis
from app.models.simulation import Simulation
from app.models.treatment import Treatment
from app.repositories.policy_repository import PolicyRepository
from app.schemas.dashboard import DashboardResponse, DashboardStats
from app.schemas.evidence_reference import EvidenceReferenceResponse
from app.schemas.policy_analysis import AnalysisDetailResponse
from app.schemas.simulation import SimulationResponse

logger = get_logger("coverwise.api.dashboard")

router = APIRouter(tags=["Dashboard"])


def _format_analysis(analysis: PolicyAnalysis) -> AnalysisDetailResponse:
    """Helper to format a PolicyAnalysis model."""
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


def _format_simulation(sim: Simulation) -> SimulationResponse:
    """Helper to format a Simulation model."""
    breakdown = sim.calculation_breakdown or {}
    return SimulationResponse(
        id=sim.id,
        policy_id=sim.policy_id,
        treatment=sim.treatment_name,
        treatment_name=sim.treatment_name,
        hospital_quote=sim.hospital_quote,
        total_treatment_cost=sim.hospital_quote,
        room_category=sim.room_category,
        estimated_insurance_share=sim.estimated_insurance_share,
        estimated_patient_share=sim.estimated_patient_share,
        deductible=sim.deductible or 0.0,
        copay=sim.copay or 0.0,
        coverage_applied=breakdown.get("capped_eligible_amount", sim.hospital_quote),
        excluded_amount=breakdown.get("non_payable_deduction", 0.0) + breakdown.get("excess_over_limit", 0.0),
        assumptions=breakdown.get("assumptions", []),
        warnings=breakdown.get("warnings", []),
        calculation_breakdown=breakdown,
        created_at=sim.created_at,
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get operational metrics and recent activities for dashboard",
)
def get_dashboard_data(db: Session = Depends(get_db)) -> DashboardResponse:
    """
    Retrieve aggregated metrics, high-level intelligence stats, and recent activities.

    Serves Member 1's frontend dashboard route (/dashboard).
    """
    total_policies = db.query(func.count(Policy.id)).scalar() or 0
    total_analyses = db.query(func.count(PolicyAnalysis.id)).scalar() or 0
    total_simulations = db.query(func.count(Simulation.id)).scalar() or 0
    total_treatments = db.query(func.count(Treatment.id)).scalar() or 0

    # Aggregate simulation numbers
    totals = (
        db.query(
            func.sum(Simulation.hospital_quote).label("total_quotes"),
            func.sum(Simulation.estimated_insurance_share).label("total_insurance"),
        ).first()
    )

    total_quote_sum = float(totals.total_quotes or 0.0) if totals else 0.0
    total_insurance_sum = float(totals.total_insurance or 0.0) if totals else 0.0

    avg_coverage_pct = 0.0
    if total_quote_sum > 0:
        avg_coverage_pct = round((total_insurance_sum / total_quote_sum) * 100.0, 2)

    # Fetch recent items
    policy_repo = PolicyRepository(db)
    recent_policies = policy_repo.list(skip=0, limit=5)

    recent_analyses_raw = (
        db.query(PolicyAnalysis)
        .order_by(PolicyAnalysis.created_at.desc())
        .limit(5)
        .all()
    )
    recent_analyses = [_format_analysis(a) for a in recent_analyses_raw]

    recent_sims_raw = (
        db.query(Simulation)
        .order_by(Simulation.created_at.desc())
        .limit(5)
        .all()
    )
    recent_simulations = [_format_simulation(s) for s in recent_sims_raw]

    stats = DashboardStats(
        total_policies=total_policies,
        total_analyses=total_analyses,
        total_simulations=total_simulations,
        total_treatments=total_treatments,
        average_insurance_coverage_pct=avg_coverage_pct,
        total_claim_amount_simulated=round(total_quote_sum, 2),
        total_estimated_savings=round(total_insurance_sum, 2),
    )

    return DashboardResponse(
        stats=stats,
        recent_policies=recent_policies,
        recent_analyses=recent_analyses,
        recent_simulations=recent_simulations,
        system_status="operational",
    )
