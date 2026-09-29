from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.policy import Policy
from app.models.simulation import Simulation
from app.models.user import User
from app.repositories.policy_repository import PolicyRepository
from app.schemas.treatment_estimate import (
    TreatmentEstimateRequest,
    TreatmentEstimateResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from app.services.treatment_catalog_service import (
    TreatmentCatalogService,
    get_treatment_catalog_service,
)
from app.services.treatment_estimation_service import (
    TreatmentCostEstimationService,
    get_treatment_estimation_service,
)

logger = get_logger("coverwise.api.treatment_estimates")

router = APIRouter(prefix="/treatment-estimates", tags=["Treatment Cost Intelligence"])


@router.post(
    "",
    response_model=TreatmentEstimateResponse,
    summary="Estimate treatment cost and insurance coverage breakdown",
)
def estimate_treatment_cost(
    payload: TreatmentEstimateRequest,
    db: Session = Depends(get_db),
    est_service: TreatmentCostEstimationService = Depends(get_treatment_estimation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> TreatmentEstimateResponse:
    """
    Calculate deterministic treatment expense, eligible claim amount, insurer share, and patient liability.
    Combines policy conditions, user scenario parameters, and synthetic benchmark cost catalog.
    """
    policy = None
    if payload.policy_id:
        policy_repo = PolicyRepository(db)
        policy = policy_repo.get_by_id(payload.policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy with ID {payload.policy_id} not found.",
            )
        if policy.user_id:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required to estimate for this policy.",
                )
            if policy.user_id != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this policy.",
                )

    res = est_service.estimate(
        scenario=payload.scenario,
        policy=policy,
    )

    # Persist simulation in database if policy is present
    if policy:
        try:
            breakdown = {
                "total_estimated_cost": res.estimated_total_cost,
                "potentially_eligible_amount": res.potentially_eligible_amount,
                "deductible_deduction": res.deductible_applied,
                "copay_deduction": res.copay_applied,
                "room_rent_deduction": res.room_rent_penalty,
                "non_payable_deduction": res.non_payable_excluded,
                "excess_over_limit": res.excess_over_limit,
                "assumptions": res.assumptions,
                "warnings": res.uncertainty_notes,
                "currency": res.currency,
            }
            sim = Simulation(
                policy_id=policy.id,
                treatment_name=payload.scenario.treatment_name,
                hospital_quote=res.estimated_total_cost,
                room_category=payload.scenario.room_category or "Single Private Room",
                deductible=res.deductible_applied,
                copay=res.copay_applied,
                coverage_limit=res.potentially_eligible_amount + res.excess_over_limit,
                estimated_insurance_share=res.estimated_insurer_contribution,
                estimated_patient_share=res.estimated_patient_responsibility,
                calculation_breakdown=breakdown,
            )
            db.add(sim)
            db.commit()
            db.refresh(sim)
        except Exception as sim_err:
            logger.warning(f"Could not persist simulation record for estimate: {sim_err}")

    return TreatmentEstimateResponse(**res.model_dump())


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="Perform What-If comparison across two scenario states",
)
def evaluate_what_if_scenario(
    payload: WhatIfRequest,
    db: Session = Depends(get_db),
    est_service: TreatmentCostEstimationService = Depends(get_treatment_estimation_service),
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> WhatIfResponse:
    """
    Analyze how cost estimates, insurance shares, and patient liabilities change when
    additional or altered scenario parameters are supplied.
    """
    policy = None
    if payload.policy_id:
        policy_repo = PolicyRepository(db)
        policy = policy_repo.get_by_id(payload.policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy with ID {payload.policy_id} not found.",
            )
        if policy.user_id:
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required to perform What-If for this policy.",
                )
            if policy.user_id != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this policy.",
                )

    res = est_service.compare_what_if(
        prev_scenario=payload.previous_scenario,
        new_scenario=payload.updated_scenario,
        policy=policy,
    )
    return WhatIfResponse(
        previous_scenario=res.previous_scenario,
        updated_scenario=res.updated_scenario,
        previous_estimate=TreatmentEstimateResponse(**res.previous_estimate.model_dump()),
        updated_estimate=TreatmentEstimateResponse(**res.updated_estimate.model_dump()),
        changes_detected=res.changes_detected,
        total_cost_delta=res.total_cost_delta,
        insurer_contribution_delta=res.insurer_contribution_delta,
        patient_responsibility_delta=res.patient_responsibility_delta,
        explanation_of_changes=res.explanation_of_changes,
    )


@router.get(
    "/benchmarks",
    summary="Retrieve synthetic treatment benchmark catalog",
)
def list_benchmark_treatments(
    catalog_service: TreatmentCatalogService = Depends(get_treatment_catalog_service),
) -> Dict[str, Any]:
    """Retrieve catalog of standard benchmark procedures, cost ranges, and expected length of stay."""
    treatments = catalog_service.list_benchmark_treatments()
    return {
        "dataset_version": "1.0.0",
        "data_source_type": "synthetic_demo_data",
        "total_treatments": len(treatments),
        "disclaimer": "Synthetic benchmark figures for demonstration and estimation only.",
        "treatments": treatments,
    }
