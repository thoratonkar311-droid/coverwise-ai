"""Tests for CoverWise AI Pydantic v2 domain schemas.

Verifies strict requirement: Unknown policy fields must default to None (null in JSON).
Verifies preservation of 1-indexed page numbers and evidence spans.
"""

import json
import pytest
from pydantic import ValidationError

from ai.schemas.evidence import (
    BoundingBox,
    Citation,
    EvidenceSpan,
    ExtractedDocument,
    ExtractedPage,
)
from ai.schemas.policy import (
    CoinsuranceDetails,
    CopayDetails,
    CoverageCategory,
    CoverageStatus,
    DeductibleDetails,
    OutOfPocketMaxDetails,
    PolicyAnalysis,
    PolicyBenefitItem,
    PolicyClause,
    PolicyDocumentMetadata,
)
from ai.schemas.cost import TreatmentCostEstimate


class TestSchemaNullability:
    """Verifies that unknown or unspecified policy fields strictly default to None."""

    def test_deductible_defaults_to_none(self):
        deductibles = DeductibleDetails()
        assert deductibles.individual_in_network is None
        assert deductibles.individual_out_of_network is None
        assert deductibles.family_in_network is None
        assert deductibles.family_out_of_network is None
        assert deductibles.evidence == []

        # Ensure JSON serialization emits null
        data = json.loads(deductibles.model_dump_json())
        assert data["individual_in_network"] is None
        assert data["individual_out_of_network"] is None

    def test_copays_default_to_none(self):
        copays = CopayDetails()
        assert copays.primary_care is None
        assert copays.specialist is None
        assert copays.urgent_care is None
        assert copays.emergency_room is None
        assert copays.generic_prescription is None

        data = json.loads(copays.model_dump_json())
        assert data["primary_care"] is None
        assert data["specialist"] is None

    def test_coinsurance_defaults_to_none(self):
        coins = CoinsuranceDetails()
        assert coins.in_network_percentage is None
        assert coins.out_of_network_percentage is None

    def test_out_of_pocket_max_defaults_to_none(self):
        oop = OutOfPocketMaxDetails()
        assert oop.individual_in_network is None
        assert oop.family_in_network is None

    def test_metadata_defaults_to_none(self):
        meta = PolicyDocumentMetadata()
        assert meta.policy_id is None
        assert meta.insurer_name is None
        assert meta.plan_type is None
        assert meta.plan_year is None

    def test_cost_estimate_defaults_to_none(self):
        est = TreatmentCostEstimate(treatment_name="Knee Arthroscopy")
        assert est.estimated_total_cost is None
        assert est.estimated_insurer_responsibility is None
        assert est.estimated_patient_responsibility is None
        assert est.estimated_deductible_applied is None
        assert est.estimated_copay_applied is None
        assert est.estimated_coinsurance_applied is None
        assert est.requires_prior_authorization is None


class TestEvidencePreservation:
    """Verifies page numbering and evidence span integrity."""

    def test_evidence_span_page_number_ge_one(self):
        span = EvidenceSpan(
            text="Copay for PCP is $25",
            page_number=1,
            clause_reference="Section 2.1",
        )
        assert span.page_number == 1
        assert span.text == "Copay for PCP is $25"

        # Invalid page number (< 1) must raise ValidationError
        with pytest.raises(ValidationError):
            EvidenceSpan(text="Invalid", page_number=0)

    def test_citation_preserves_page_and_quote(self):
        citation = Citation(
            document_name="sample_policy.pdf",
            page_number=2,
            clause_title="Office Visits",
            clause_reference="2.1",
            verbatim_text="Specialist copay is $50.00",
        )
        assert citation.page_number == 2
        assert citation.verbatim_text == "Specialist copay is $50.00"

    def test_extracted_document_page_retrieval(self):
        pages = [
            ExtractedPage(page_number=1, text="Page 1 text", char_count=11, word_count=3),
            ExtractedPage(page_number=2, text="Page 2 text", char_count=11, word_count=3),
        ]
        doc = ExtractedDocument(
            document_id="doc-test-1",
            filename="policy.pdf",
            total_pages=2,
            pages=pages,
        )
        assert doc.get_page(1) == pages[0]
        assert doc.get_page(2) == pages[1]
        assert doc.get_page(3) is None
        assert "Page 1 text" in doc.get_full_text()
        assert "Page 2 text" in doc.get_full_text()


class TestSchemaValidationConstraints:
    """Verifies that out-of-range numeric values and invalid types are rejected."""

    def test_rejects_negative_deductibles(self):
        with pytest.raises(ValidationError):
            DeductibleDetails(individual_in_network=-100.0)

    def test_rejects_coinsurance_above_100(self):
        with pytest.raises(ValidationError):
            CoinsuranceDetails(in_network_percentage=120.0)

    def test_policy_clause_requires_positive_page(self):
        with pytest.raises(ValidationError):
            PolicyClause(
                clause_id="c1",
                text="Clause text",
                page_number=0,  # Invalid: must be >= 1
            )

    def test_complete_policy_analysis_roundtrip(self, sample_policy_analysis):
        json_str = sample_policy_analysis.model_dump_json()
        restored = PolicyAnalysis.model_validate_json(json_str)
        assert restored.metadata.policy_id == "POL-9921"
        assert restored.deductibles.individual_in_network == 1000.0
        assert len(restored.benefits) == 1
        assert restored.benefits[0].evidence[0].page_number == 3
