from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalysisCreate,
    AnalysisResponse,
    CoverageRuleCreate,
    CoverageRuleResponse,
    EvidenceReferenceCreate,
    EvidenceReferenceResponse,
    PolicyCreate,
    PolicyResponse,
    PolicySummaryResponse,
    SimulationRequest,
    SimulationResponse,
    TreatmentCreate,
    TreatmentResponse,
)


def test_policy_schema_validation() -> None:
    """Verify PolicyCreate and PolicyResponse schemas."""
    # Valid creation payload
    create_data = {
        "filename": "hdfc_ergo_my_health.pdf",
        "user_id": "usr_99182",
        "insurer_name": "HDFC ERGO",
        "plan_name": "My:Health Suraksha",
        "policy_number": "POL-112233",
    }
    create_schema = PolicyCreate(**create_data)
    assert create_schema.filename == "hdfc_ergo_my_health.pdf"
    assert create_schema.status == "uploaded"

    # Missing filename should fail validation
    with pytest.raises(ValidationError):
        PolicyCreate(insurer_name="HDFC ERGO")

    # Valid response schema
    now = datetime.now(timezone.utc)
    response_data = {
        **create_data,
        "id": 1,
        "status": "analyzed",
        "created_at": now,
        "updated_at": now,
        "coverage_rules": [],
    }
    response_schema = PolicyResponse(**response_data)
    assert response_schema.id == 1
    assert response_schema.status == "analyzed"

    # Summary response
    summary_schema = PolicySummaryResponse(**response_data)
    assert summary_schema.id == 1
    assert summary_schema.filename == "hdfc_ergo_my_health.pdf"


def test_coverage_rule_schema_validation() -> None:
    """Verify CoverageRuleCreate and CoverageRuleResponse schemas."""
    rule_data = {
        "policy_id": 10,
        "coverage_status": "covered",
        "deductible": 2500.0,
        "copay_percentage": 10.0,
        "coverage_limit": 500000.0,
        "exclusions": ["Dental unless accidental", "Spectacles"],
        "room_category": "Twin Sharing",
    }
    create_schema = CoverageRuleCreate(**rule_data)
    assert create_schema.deductible == 2500.0

    # Negative deductible should fail
    with pytest.raises(ValidationError):
        CoverageRuleCreate(policy_id=1, deductible=-100.0)

    # Copay percentage > 100 should fail
    with pytest.raises(ValidationError):
        CoverageRuleCreate(policy_id=1, copay_percentage=150.0)

    now = datetime.now(timezone.utc)
    response_schema = CoverageRuleResponse(
        **rule_data,
        id=5,
        created_at=now,
        updated_at=now,
        evidence_references=[],
    )
    assert response_schema.id == 5


def test_treatment_schema_validation() -> None:
    """Verify TreatmentCreate and TreatmentResponse schemas."""
    treatment_data = {
        "name": "Appendectomy",
        "category": "General Surgery",
        "description": "Surgical removal of appendix",
        "typical_cost_min": 40000.0,
        "typical_cost_max": 90000.0,
    }
    treatment_schema = TreatmentCreate(**treatment_data)
    assert treatment_schema.name == "Appendectomy"

    # Empty name should fail
    with pytest.raises(ValidationError):
        TreatmentCreate(name="")

    now = datetime.now(timezone.utc)
    response = TreatmentResponse(**treatment_data, id=1, created_at=now)
    assert response.id == 1


def test_simulation_schema_validation() -> None:
    """Verify SimulationRequest and SimulationResponse schemas."""
    # Valid simulation request
    req = SimulationRequest(
        policy_id=1,
        treatment_name="Cardiac Stent",
        hospital_quote=120000.0,
        room_category="Deluxe",
    )
    assert req.hospital_quote == 120000.0

    # Non-positive hospital quote should fail
    with pytest.raises(ValidationError):
        SimulationRequest(hospital_quote=0.0)

    now = datetime.now(timezone.utc)
    res = SimulationResponse(
        id=1,
        policy_id=1,
        treatment_name="Cardiac Stent",
        hospital_quote=120000.0,
        room_category="Deluxe",
        deductible=5000.0,
        copay=0.0,
        estimated_insurance_share=115000.0,
        estimated_patient_share=5000.0,
        created_at=now,
    )
    assert res.estimated_insurance_share == 115000.0
    assert res.estimated_patient_share == 5000.0


def test_evidence_reference_schema_validation() -> None:
    """Verify EvidenceReferenceCreate and EvidenceReferenceResponse schemas."""
    ref_data = {
        "policy_id": 1,
        "document_source": "policy_wording.pdf",
        "page": 12,
        "clause_section": "Clause 3.1",
        "extracted_text": "Room rent limit is 1% of Sum Insured per day.",
        "interpretation": "Room charges exceeding limit will trigger proportionate deduction.",
        "confidence": 0.95,
    }
    create_schema = EvidenceReferenceCreate(**ref_data)
    assert create_schema.confidence == 0.95

    # Confidence outside 0-1 range should fail
    with pytest.raises(ValidationError):
        EvidenceReferenceCreate(**{**ref_data, "confidence": 1.5})

    now = datetime.now(timezone.utc)
    res_schema = EvidenceReferenceResponse(**ref_data, id=10, created_at=now)
    assert res_schema.id == 10


def test_analysis_schema_validation() -> None:
    """Verify AnalysisCreate and AnalysisResponse schemas."""
    analysis_data = {
        "policy_id": 2,
        "treatment_name": "Angioplasty",
        "status": "completed",
        "result_summary": "Covered up to Sum Insured with 10% co-pay.",
        "result_data": {"covered": True, "copay": 0.10},
    }
    create_schema = AnalysisCreate(**analysis_data)
    assert create_schema.status == "completed"

    now = datetime.now(timezone.utc)
    res_schema = AnalysisResponse(
        **analysis_data,
        id=7,
        created_at=now,
        updated_at=now,
        evidence_references=[],
    )
    assert res_schema.id == 7
    assert res_schema.result_data["covered"] is True
