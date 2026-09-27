"""Tests for Phase 2A PolicyExtractor and extract_policy interface.

Verifies:
- Accurate extraction on sample_health_policy.pdf
  (deductibles, coinsurance, OOP max, prior auth 72h, cosmetic surgery excluded)
- Missing fields strictly defaulting to None/null
- Retention of conflicting evidence
- Graceful fallback on malformed model output
- Graceful fallback on unavailable Ollama server
- Exception handling on invalid PDFs
- Citation accuracy (exact page number and verbatim text matches)
- Non-inference of coverage from missing exclusions
"""

from pathlib import Path
from unittest import mock
import httpx
import pytest

from ai.extraction.pdf_extractor import CorruptPDFError, PDFNotFoundError
from ai.extraction.policy_extractor import PolicyExtractor, extract_policy
from ai.llm.client import OllamaClient
from ai.schemas.policy import CoverageStatus, PolicyAnalysis


def test_extract_sample_health_policy(sample_pdf_path):
    """Verify extraction requirements on the synthetic sample health policy fixture."""
    analysis: PolicyAnalysis = extract_policy(sample_pdf_path)

    # 1. Metadata
    assert analysis.metadata.policy_id == "APX-2026-SLV-9012"
    assert "Apex Mutual" in (analysis.metadata.insurer_name or "")
    assert "Apex Silver" in (analysis.metadata.policy_name or "")
    assert analysis.metadata.plan_year == 2026
    assert analysis.metadata.effective_date == "2026-01-01"

    # 2. Network-specific Deductibles
    assert analysis.deductibles.individual_in_network == 1500.0
    assert analysis.deductibles.individual_out_of_network == 3000.0
    assert analysis.deductibles.family_in_network == 3000.0
    assert analysis.deductibles.family_out_of_network == 6000.0

    # 3. Coinsurance percentages
    assert analysis.coinsurance.in_network_percentage == 20.0
    assert analysis.coinsurance.out_of_network_percentage == 40.0

    # 4. Out-of-pocket maximums
    assert analysis.out_of_pocket_max.individual_in_network == 6500.0
    assert analysis.out_of_pocket_max.individual_out_of_network == 13000.0
    assert analysis.out_of_pocket_max.family_in_network == 13000.0
    assert analysis.out_of_pocket_max.family_out_of_network == 26000.0

    # 5. Copayments
    assert analysis.copays.primary_care == 25.0
    assert analysis.copays.specialist == 50.0
    assert analysis.copays.urgent_care == 75.0
    assert analysis.copays.emergency_room == 350.0
    assert analysis.copays.generic_prescription == 10.0
    assert analysis.copays.preferred_brand_prescription == 40.0
    assert analysis.copays.non_preferred_brand_prescription == 80.0

    # 6. Prior Authorization (72 hours beforehand for elective inpatient)
    assert len(analysis.prior_authorizations) >= 1
    found_72h = any(
        "72 hours" in pa.timeline_requirement or "72 hours" in pa.details
        for pa in analysis.prior_authorizations
    )
    assert found_72h, "Expected prior authorization timeline '72 hours' to be extracted."

    # 7. Exclusions (Cosmetic surgery excluded)
    assert len(analysis.exclusions) > 0
    found_cosmetic = any("cosmetic" in ex.lower() for ex in analysis.exclusions)
    assert found_cosmetic, "Expected 'cosmetic surgery' to be present in exclusions."

    # 8. Waiting periods strictly NOT inferred
    # In sample_health_policy.pdf, no waiting period is specified -> must be empty!
    assert analysis.waiting_periods == []


def test_citation_accuracy(sample_pdf_path):
    """Verify that every extracted evidence span matches verbatim text on its cited page."""
    analysis = extract_policy(sample_pdf_path)

    # PyMuPDF extractor to load raw pages for ground-truth verification
    from ai.extraction.pdf_extractor import PDFExtractor
    raw_doc = PDFExtractor().extract(sample_pdf_path)

    # Check deductible citations
    assert len(analysis.deductibles.evidence) > 0
    for span in analysis.deductibles.evidence:
        page = raw_doc.get_page(span.page_number)
        assert page is not None
        # Verify cited text actually appears in the text of that exact page
        assert span.text.lower() in page.text.lower()

    # Check copay citations
    assert len(analysis.copays.evidence) > 0
    for span in analysis.copays.evidence:
        page = raw_doc.get_page(span.page_number)
        assert page is not None
        assert span.text.lower() in page.text.lower()

    # Check prior auth citations
    for pa in analysis.prior_authorizations:
        for span in pa.evidence:
            page = raw_doc.get_page(span.page_number)
            assert page is not None
            assert span.text.lower() in page.text.lower()


def test_missing_fields_default_to_null(temp_pdf_factory):
    """Verify that absent/unmentioned policy provisions strictly remain None/null."""
    sparse_policy_text = [
        """BAREBONES POLICY 2026
        Plan Name: Minimal Plan
        SECTION 1: OFFICE VISITS
        Primary Care Physician (PCP): $30.00 copay.
        """
    ]
    sparse_pdf = temp_pdf_factory(sparse_policy_text, filename="sparse_policy.pdf")
    analysis = extract_policy(sparse_pdf)

    # Primary care was mentioned
    assert analysis.copays.primary_care == 30.0

    # All unmentioned fields MUST be None
    assert analysis.deductibles.individual_in_network is None
    assert analysis.deductibles.individual_out_of_network is None
    assert analysis.coinsurance.in_network_percentage is None
    assert analysis.out_of_pocket_max.individual_in_network is None
    assert analysis.metadata.policy_id is None
    assert analysis.waiting_periods == []
    assert analysis.exclusions == []


def test_never_infer_coverage_from_missing_exclusions():
    """Verify system invariant: Never infer coverage from missing exclusions."""
    analysis = PolicyAnalysis(
        exclusions=["Cosmetic surgery", "Experimental therapies"]
    )
    # Check that a service not in exclusions (e.g., "Acupuncture") is NOT automatically marked covered
    covered_services = [b.service_name for b in analysis.benefits if b.status == CoverageStatus.COVERED]
    assert "Acupuncture" not in covered_services
    # Benefits list should only contain affirmatively stated items
    assert len(analysis.benefits) == 0


def test_conflicting_evidence_retention(temp_pdf_factory):
    """Verify that conflicting or ambiguous clauses are captured in conflicting_evidence."""
    conflicting_pages = [
        """SCHEDULE OF BENEFITS - AMBIGUOUS RIDER
        Section 1: In-Network Services: 20% coinsurance after deductible is met.
        """,
        """AMENDMENT RIDER
        Notwithstanding prior clauses, conflicting terms: In-Network Services: 30% coinsurance.
        """
    ]
    pdf_path = temp_pdf_factory(conflicting_pages, filename="conflict.pdf")
    analysis = extract_policy(pdf_path)

    # Discrepancy or overriding wording must be recorded
    assert len(analysis.conflicting_evidence) > 0
    conflict = analysis.conflicting_evidence[0]
    assert "conflict" in conflict.description.lower() or "overriding" in conflict.description.lower()


def test_fallback_on_unavailable_ollama(sample_pdf_path):
    """Verify PolicyExtractor falls back to deterministic extraction when Ollama is offline."""
    # Point client to non-existent server port
    offline_client = OllamaClient(base_url="http://127.0.0.1:59999", timeout_seconds=1)
    extractor = PolicyExtractor(llm_client=offline_client, use_llm=True)

    # Should not crash; extracts successfully using deterministic engine
    analysis = extractor.extract_from_pdf(sample_pdf_path)
    assert analysis.deductibles.individual_in_network == 1500.0
    assert analysis.coinsurance.in_network_percentage == 20.0
    assert analysis.extraction_source in ("deterministic", "hybrid")


def test_fallback_on_malformed_model_output(sample_pdf_path):
    """Verify PolicyExtractor handles malformed/corrupted LLM outputs gracefully."""
    mock_client = OllamaClient()
    mock_bad_response = httpx.Response(
        status_code=200,
        text="MALFORMED_NON_JSON_OUTPUT_<<<>>>",
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
    )

    with mock.patch("httpx.Client.post", return_value=mock_bad_response):
        extractor = PolicyExtractor(llm_client=mock_client, use_llm=True)
        analysis = extractor.extract_from_pdf(sample_pdf_path)
        # Should cleanly fall back and extract exact values
        assert analysis.deductibles.individual_in_network == 1500.0
        assert analysis.coinsurance.in_network_percentage == 20.0


def test_invalid_pdf_handling(tmp_path):
    """Verify proper exceptions on missing or corrupt PDF files."""
    # 1. Non-existent file
    missing = tmp_path / "absent.pdf"
    with pytest.raises(PDFNotFoundError):
        extract_policy(missing)

    # 2. Corrupted file
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"NOT A REAL PDF FILE HEADER")
    with pytest.raises(CorruptPDFError):
        extract_policy(corrupt)
