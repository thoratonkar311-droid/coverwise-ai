import pytest
from pydantic import ValidationError

from app.models.policy import Policy
from app.schemas.ai_contract import (
    DocumentExtractionInput,
    EvidenceItem,
    EvidenceQueryInput,
    EvidenceRetrievalOutput,
    ExtractedPolicyInfo,
    StructuredAIAnalysisResult,
    StructuredPolicyRules,
)
from app.services.policy_analysis_service import (
    ExtractedAnalysisOutput,
    MockPolicyAnalysisService,
)


def test_ai_contract_extraction_service() -> None:
    """Verify document extraction handles various insurer formats."""
    service = MockPolicyAnalysisService()

    # Star Health extraction
    star_input = DocumentExtractionInput(
        filename="star_health_policy.pdf",
        raw_text=(
            "Insurer: Star Health & Allied Insurance Company Limited\n"
            "Plan Name: Star Comprehensive Health Insurance Plan\n"
            "Policy Number: STAR-POLICY-101\n"
            "Sum Insured: 1,000,000\n"
            "Policy Period: 01-Apr-2024 to 31-Mar-2025"
        ),
    )
    star_info = service.extract_policy_information(star_input)
    assert "Star Health" in star_info.insurer_name
    assert star_info.sum_insured == 1000000.0
    assert star_info.confidence > 0.0

    # Bajaj extraction
    bajaj_input = DocumentExtractionInput(
        filename="bajaj_allianz_doc.pdf",
        raw_text=(
            "Insurer: Bajaj Allianz General Insurance Company Limited\n"
            "Plan Name: Health Guard Gold Plan\n"
            "Policy Number: BAJAJ-POLICY-202"
        ),
    )
    bajaj_info = service.extract_policy_information(bajaj_input)
    assert "Bajaj Allianz" in bajaj_info.insurer_name
    assert bajaj_info.sum_insured is None

    # Care extraction
    care_input = DocumentExtractionInput(
        filename="care_advantage.pdf",
        raw_text=(
            "Insurer: Care Health Insurance Limited\n"
            "Plan Name: Care Advantage Elite\n"
            "Policy Number: CARE-POLICY-303"
        ),
    )
    care_info = service.extract_policy_information(care_input)
    assert "Care Health" in care_info.insurer_name
    assert care_info.sum_insured is None

    # Fallback default extraction: unestablished document returns nulls rather than inventing values
    default_input = DocumentExtractionInput(filename="generic_scan.pdf")
    default_info = service.extract_policy_information(default_input)
    assert default_info.insurer_name is None
    assert default_info.sum_insured is None
    assert default_info.confidence == 0.0


def test_ai_contract_evidence_retrieval() -> None:
    """Verify semantic evidence retrieval for different medical procedure queries."""
    service = MockPolicyAnalysisService()

    # Query for optical / cataract clauses
    res = service.retrieve_evidence(
        EvidenceQueryInput(query="Cataract procedure sub-limit", max_results=3)
    )
    assert isinstance(res, EvidenceRetrievalOutput)
    assert len(res.evidence_items) >= 1
    assert "Section 4.B" in res.evidence_items[0].clause_section
    assert res.evidence_items[0].confidence >= 0.9

    # Query for co-pay and joint surgery
    knee_res = service.retrieve_evidence(
        EvidenceQueryInput(query="knee joint replacement copay", max_results=2)
    )
    assert len(knee_res.evidence_items) >= 1
    assert "Section 6.3" in knee_res.evidence_items[0].clause_section

    # Query for unmentioned procedure
    unmatched_res = service.retrieve_evidence(
        EvidenceQueryInput(query="hyperbaric ozone chamber therapy", max_results=5)
    )
    assert len(unmatched_res.evidence_items) == 0
    assert "No specific clauses found" in unmatched_res.summary


def test_ai_contract_not_determined_validation() -> None:
    """
    Enforce core principle:
    'Do not invent policy facts. If no reliable policy rule is available, return not_determined.'
    - Must require an explanation.
    - Confidence must be capped at 0.5.
    """
    # 1. Missing explanation on not_determined raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        StructuredAIAnalysisResult(
            coverage_status="not_determined",
            coverage_information="Cannot determine coverage.",
            explanation="",  # Empty explanation invalid!
            confidence=0.4,
        )
    assert "An explanation is required" in str(exc_info.value)

    # 2. Confidence higher than 0.5 automatically capped to 0.5
    result = StructuredAIAnalysisResult(
        coverage_status="not_determined",
        coverage_information="Ambiguous treatment.",
        explanation="Procedure not recognized in policy documents.",
        confidence=0.95,  # Exceeds 0.5 cap
    )
    assert result.confidence == 0.5

    # 3. Invalid coverage_status raises ValidationError
    with pytest.raises(ValidationError):
        StructuredAIAnalysisResult(
            coverage_status="unknown_status",
            coverage_information="Test",
            explanation="Test",
            confidence=0.5,
        )


def test_ai_contract_structured_policy_rules() -> None:
    """Verify numeric rules validation: bounds on copay percentage, non-negative amounts."""
    # Valid rules
    rules = StructuredPolicyRules(
        deductible=5000.0,
        copay_fixed=1000.0,
        copay_percentage=15.0,
        coverage_limit=200000.0,
    )
    assert rules.copay_percentage == 15.0

    # Negative deductible rejected
    with pytest.raises(ValidationError):
        StructuredPolicyRules(deductible=-100.0)

    # Copay percentage > 100 rejected
    with pytest.raises(ValidationError):
        StructuredPolicyRules(copay_percentage=105.0)


def test_extracted_analysis_output_conversion() -> None:
    """Verify bidirectional conversion between ExtractedAnalysisOutput and StructuredAIAnalysisResult."""
    output = ExtractedAnalysisOutput(
        coverage_status="partially_covered",
        coverage_information="Covered with sublimit",
        deductible=2000.0,
        copay=500.0,
        copay_percentage=10.0,
        coverage_limit=50000.0,
        exclusions=["Cosmetic items"],
        waiting_periods="12 months",
        confidence=0.92,
        explanation="Detailed explanation",
        evidence_references=[
            EvidenceItem(
                document_source="doc.pdf",
                page=3,
                clause_section="Section 1.1",
                extracted_text="Clause text",
                interpretation="AI interpretation",
                confidence=0.95,
            )
        ],
    )

    structured = output.to_structured_result()
    assert isinstance(structured, StructuredAIAnalysisResult)
    assert structured.coverage_status == "partially_covered"
    assert structured.rules.coverage_limit == 50000.0
    assert structured.rules.copay_percentage == 10.0
    assert len(structured.evidence) == 1

    # Round trip conversion
    roundtrip = ExtractedAnalysisOutput.from_structured_result(structured)
    assert roundtrip.coverage_status == output.coverage_status
    assert roundtrip.coverage_limit == output.coverage_limit
    assert roundtrip.copay_percentage == output.copay_percentage
    assert roundtrip.deductible == output.deductible
