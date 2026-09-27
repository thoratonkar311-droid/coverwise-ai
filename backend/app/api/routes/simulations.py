from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.coverage_rule import CoverageRule
from app.models.policy import Policy
from app.models.simulation import Simulation
from app.repositories.policy_repository import PolicyRepository
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services.calculation_service import (
    CalculationInput,
    CalculationResult,
    CalculationService,
    PolicyRulesInput,
)

logger = get_logger("coverwise.api.simulations")

router = APIRouter(tags=["Cost Simulation"])


def _to_simulation_response(
    sim: Simulation,
    calc_result: Optional[CalculationResult] = None,
) -> SimulationResponse:
    """Format Simulation model into SimulationResponse."""
    breakdown = sim.calculation_breakdown or {}
    assumptions = (
        calc_result.assumptions
        if calc_result
        else breakdown.get(
            "assumptions",
            [
                "Calculation assumes treatment is conducted at an authorized in-network hospital.",
                "Assumes policy is in active status with no premium default.",
            ],
        )
    )
    warnings = calc_result.warnings if calc_result else breakdown.get("warnings", [])

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
        assumptions=assumptions,
        warnings=warnings,
        calculation_breakdown=breakdown,
        created_at=sim.created_at,
    )


@router.post(
    "/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate treatment cost distribution between insurer and patient",
)
@router.post(
    "/simulations/calculate",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/simulator",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate treatment cost (Member 1 frontend alias)",
)
def run_simulation(
    payload: SimulationRequest,
    db: Session = Depends(get_db),
) -> SimulationResponse:
    """
    Execute deterministic cost estimation for a hospital quote.

    Combines policy coverage rules (deductible, co-pay, coverage limit) with quote parameters
    to calculate precise patient responsibility vs insurance payout.
    Never lets arbitrary model text override deterministic mathematical formulas.
    """
    has_policy_rules = False
    deductible = payload.deductible
    copay_fixed = payload.copay
    copay_pct = payload.copay_percentage
    coverage_limit = payload.coverage_limit

    # If policy_id provided, verify policy and pull active coverage rules as baseline
    if payload.policy_id is not None:
        policy = db.query(Policy).filter(Policy.id == payload.policy_id).first()
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy with ID {payload.policy_id} not found.",
            )

        # Check for matching coverage rules on this policy
        rule = (
            db.query(CoverageRule)
            .filter(CoverageRule.policy_id == payload.policy_id)
            .order_by(CoverageRule.id.desc())
            .first()
        )
        if rule:
            has_policy_rules = True
            if deductible is None:
                deductible = rule.deductible
            if copay_fixed is None:
                copay_fixed = rule.copay
            if copay_pct is None:
                copay_pct = rule.copay_percentage
            if coverage_limit is None:
                coverage_limit = rule.coverage_limit
    elif deductible is not None or copay_fixed is not None or copay_pct is not None or coverage_limit is not None:
        has_policy_rules = True

    calc_input = CalculationInput(
        hospital_quote=payload.hospital_quote,
        room_category=payload.room_category,
        non_payable_items=payload.non_payable_items,
    )
    rules_input = PolicyRulesInput(
        deductible=deductible,
        copay_fixed=copay_fixed,
        copay_percentage=copay_pct,
        coverage_limit=coverage_limit,
        has_policy_rules=has_policy_rules,
    )

    try:
        calc_result = CalculationService.calculate(calc_input, rules_input)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Persist simulation in database
    sim_repo = SimulationRepository(db)
    sim = sim_repo.create(
        policy_id=payload.policy_id,
        treatment_id=payload.treatment_id,
        treatment_name=payload.treatment_name or payload.treatment,
        hospital_quote=payload.hospital_quote,
        room_category=payload.room_category,
        deductible=calc_result.deductible_applied,
        copay=calc_result.copay_applied,
        coverage_limit=coverage_limit,
        estimated_insurance_share=calc_result.estimated_insurance_share,
        estimated_patient_share=calc_result.estimated_patient_share,
        calculation_breakdown=calc_result.breakdown,
    )

    logger.info(
        f"Simulated quote {payload.hospital_quote:,.2f} -> Insurer: {calc_result.estimated_insurance_share:,.2f}, "
        f"Patient: {calc_result.estimated_patient_share:,.2f} (Simulation #{sim.id})"
    )

    return _to_simulation_response(sim, calc_result)


@router.get(
    "/simulations/{simulation_id}",
    response_model=SimulationResponse,
    summary="Get simulation by ID",
)
def get_simulation(
    simulation_id: int = Path(..., gt=0, description="Database ID of the simulation"),
    db: Session = Depends(get_db),
) -> SimulationResponse:
    """Retrieve saved simulation breakdown by primary ID."""
    sim_repo = SimulationRepository(db)
    sim = sim_repo.get_by_id(simulation_id)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation with ID {simulation_id} not found.",
        )
    return _to_simulation_response(sim)


@router.get(
    "/policies/{policy_id}/simulations",
    response_model=List[SimulationResponse],
    summary="List simulations for a policy",
)
def list_simulations_for_policy(
    policy_id: int = Path(..., gt=0, description="Database ID of the policy"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[SimulationResponse]:
    """Retrieve historical simulations run for a specific policy."""
    policy_repo = PolicyRepository(db)
    if not policy_repo.get_by_id(policy_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with ID {policy_id} not found.",
        )

    sim_repo = SimulationRepository(db)
    sims = sim_repo.list_by_policy(policy_id, skip=skip, limit=limit)
    return [_to_simulation_response(s) for s in sims]
