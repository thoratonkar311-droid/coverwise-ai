import pytest
from sqlalchemy.orm import Session

from app.db.session import (
    get_db_context,
    ping_db,
    validate_database_url,
)
from app.models import (
    CoverageRule,
    EvidenceReference,
    Policy,
    PolicyAnalysis,
    Simulation,
    Treatment,
)


def test_validate_database_url() -> None:
    """Verify DATABASE_URL validation logic."""
    # Test valid PostgreSQL URL normalization
    normalized = validate_database_url("postgresql://user:pass@localhost:5432/testdb")
    assert normalized == "postgresql+psycopg2://user:pass@localhost:5432/testdb"

    # Test valid sqlite URL
    sqlite_url = validate_database_url("sqlite:///:memory:")
    assert sqlite_url == "sqlite:///:memory:"

    # Test empty URL raises ValueError
    with pytest.raises(ValueError, match="missing or empty"):
        validate_database_url("")

    # Test unsupported dialect raises ValueError
    with pytest.raises(ValueError, match="Unsupported database scheme"):
        validate_database_url("mysql://user:pass@localhost/db")


def test_ping_db(db_session: Session) -> None:
    """Verify database ping succeeds against active session."""
    assert ping_db(db_session) is True


def test_create_policy_and_nullable_fields(db_session: Session) -> None:
    """Verify Policy model creation and optional/nullable fields handling."""
    policy = Policy(
        filename="health_policy_2026.pdf",
        status="uploaded",
    )
    db_session.add(policy)
    db_session.flush()

    assert policy.id is not None
    assert policy.filename == "health_policy_2026.pdf"
    assert policy.status == "uploaded"
    assert policy.policy_number is None
    assert policy.insurer_name is None
    assert policy.user_id is None
    assert policy.created_at is not None
    assert policy.updated_at is not None


def test_create_treatment_catalog(db_session: Session) -> None:
    """Verify Treatment catalog entry creation and constraints."""
    treatment = Treatment(
        name="Total Knee Replacement",
        category="Orthopedics",
        description="Surgical replacement of knee joint with prosthetic implant",
        typical_cost_min=180000.0,
        typical_cost_max=350000.0,
    )
    db_session.add(treatment)
    db_session.flush()

    assert treatment.id is not None
    assert treatment.name == "Total Knee Replacement"
    assert treatment.typical_cost_min == 180000.0


def test_policy_relationships_and_cascade_delete(db_session: Session) -> None:
    """Verify relationships across models and cascading deletion upon policy removal."""
    # 1. Create Policy
    policy = Policy(
        filename="star_health_optima.pdf",
        policy_number="POL-99210",
        insurer_name="Star Health",
        plan_name="Comprehensive Optima",
        status="analyzed",
    )
    db_session.add(policy)
    db_session.flush()

    # 2. Create Treatment
    treatment = Treatment(
        name="Cataract Surgery",
        category="Ophthalmology",
        typical_cost_min=25000.0,
        typical_cost_max=60000.0,
    )
    db_session.add(treatment)
    db_session.flush()

    # 3. Create CoverageRule
    rule = CoverageRule(
        policy_id=policy.id,
        coverage_status="partially_covered",
        deductible=5000.0,
        copay_percentage=10.0,
        coverage_limit=40000.0,
        exclusions=["Cosmetic implants", "Premium multifocal lenses"],
        room_category="Single Private Room",
    )
    db_session.add(rule)
    db_session.flush()

    # 4. Create PolicyAnalysis
    analysis = PolicyAnalysis(
        policy_id=policy.id,
        treatment_id=treatment.id,
        treatment_name="Cataract Surgery",
        status="completed",
        result_summary="Cataract surgery is capped at 40,000 INR per eye.",
        result_data={"capped": True, "max_amount": 40000.0},
    )
    db_session.add(analysis)
    db_session.flush()

    # 5. Create EvidenceReference
    evidence = EvidenceReference(
        policy_id=policy.id,
        rule_id=rule.id,
        analysis_id=analysis.id,
        document_source="star_health_optima.pdf",
        page=14,
        clause_section="Section 4.B - Specific Ailment Sub-limits",
        extracted_text="Cataract surgery coverage is limited to Rs 40,000 per eye.",
        interpretation="Insurer covers up to 40k only; remaining balance is patient responsibility.",
        confidence=0.96,
    )
    db_session.add(evidence)
    db_session.flush()

    # 6. Create Simulation
    simulation = Simulation(
        policy_id=policy.id,
        treatment_id=treatment.id,
        treatment_name="Cataract Surgery",
        hospital_quote=55000.0,
        room_category="Single Private Room",
        deductible=5000.0,
        copay=0.0,
        coverage_limit=40000.0,
        estimated_insurance_share=35000.0,
        estimated_patient_share=20000.0,
        calculation_breakdown={"sublimit_excess": 15000.0, "deductible_applied": 5000.0},
    )
    db_session.add(simulation)
    db_session.flush()

    # Verify relationships populated
    assert len(policy.coverage_rules) == 1
    assert len(policy.analyses) == 1
    assert len(policy.simulations) == 1
    assert len(policy.evidence_references) == 1
    assert policy.coverage_rules[0].coverage_limit == 40000.0
    assert policy.analyses[0].treatment.name == "Cataract Surgery"

    # Test cascade delete
    policy_id = policy.id
    db_session.delete(policy)
    db_session.flush()

    # Associated child entities should be removed
    assert db_session.query(CoverageRule).filter_by(policy_id=policy_id).first() is None
    assert db_session.query(PolicyAnalysis).filter_by(policy_id=policy_id).first() is None
    assert db_session.query(Simulation).filter_by(policy_id=policy_id).first() is None
    assert db_session.query(EvidenceReference).filter_by(policy_id=policy_id).first() is None

    # Catalog treatment remains intact
    assert db_session.query(Treatment).filter_by(id=treatment.id).first() is not None


def test_session_rollback_behavior() -> None:
    """Verify get_db_context rolls back on exception without persisting corrupted data."""
    try:
        with get_db_context() as session:
            policy = Policy(filename="will_fail.pdf")
            session.add(policy)
            session.flush()
            raise RuntimeError("Simulated transaction failure")
    except RuntimeError:
        pass

    with get_db_context() as session:
        queried = session.query(Policy).filter_by(filename="will_fail.pdf").first()
        assert queried is None
