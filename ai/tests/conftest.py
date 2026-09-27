"""Pytest fixtures for CoverWise AI test suite."""

from pathlib import Path
import pytest
try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

from ai.config import Settings
from ai.schemas.evidence import EvidenceSpan
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


@pytest.fixture
def sample_pdf_path() -> Path:
    """Return path to the synthetic sample health policy PDF."""
    path = Path(__file__).resolve().parent.parent / "sample_policies" / "sample_health_policy.pdf"
    assert path.is_file(), f"Sample health policy PDF not found at {path}"
    return path


@pytest.fixture
def temp_pdf_factory(tmp_path: Path):
    """Factory fixture to create synthetic custom PDFs for testing edge cases."""

    def _create_pdf(pages_text: list[str], filename: str = "temp_test.pdf") -> Path:
        target_path = tmp_path / filename
        doc = fitz.open()
        for text in pages_text:
            page = doc.new_page(width=595, height=842)
            if text:
                rect = fitz.Rect(50, 50, 545, 792)
                page.insert_textbox(rect, text, fontsize=10)
        doc.save(str(target_path))
        doc.close()
        return target_path

    return _create_pdf


@pytest.fixture
def custom_settings() -> Settings:
    """Fixture providing isolated Settings with predictable test defaults."""
    return Settings(
        ollama_base_url="http://test-server:11434",
        llm_model="qwen2.5:7b",
        embedding_model="BAAI/bge-m3",
        environment="testing",
        log_level="DEBUG",
    )


@pytest.fixture
def sample_policy_analysis() -> PolicyAnalysis:
    """Fixture providing a populated PolicyAnalysis with verified citations."""
    return PolicyAnalysis(
        raw_document_id="sha256-test-12345",
        metadata=PolicyDocumentMetadata(
            policy_id="POL-9921",
            policy_name="Horizon PPO Gold",
            insurer_name="Horizon Health",
            plan_type="PPO",
            plan_year=2026,
        ),
        deductibles=DeductibleDetails(
            individual_in_network=1000.0,
            individual_out_of_network=2500.0,
            family_in_network=2000.0,
            currency="USD",
            evidence=[
                EvidenceSpan(
                    text="Individual In-Network Deductible: $1,000",
                    page_number=1,
                    clause_reference="Section 1.1",
                )
            ],
        ),
        copays=CopayDetails(
            primary_care=20.0,
            specialist=40.0,
            urgent_care=60.0,
            evidence=[
                EvidenceSpan(
                    text="PCP copay is $20 per visit",
                    page_number=2,
                    clause_reference="Section 2.1",
                )
            ],
        ),
        coinsurance=CoinsuranceDetails(
            in_network_percentage=20.0,
            out_of_network_percentage=40.0,
        ),
        out_of_pocket_max=OutOfPocketMaxDetails(
            individual_in_network=5000.0,
            family_in_network=10000.0,
        ),
        benefits=[
            PolicyBenefitItem(
                service_name="Inpatient Surgery",
                category=CoverageCategory.INPATIENT_HOSPITAL,
                status=CoverageStatus.COVERED,
                coinsurance_percent=20.0,
                deductible_applies=True,
                prior_authorization_required=True,
                evidence=[
                    EvidenceSpan(
                        text="Inpatient hospital care covered at 20% coinsurance after deductible.",
                        page_number=3,
                        clause_reference="Section 3.1",
                    )
                ],
            )
        ],
        clauses=[
            PolicyClause(
                clause_id="clause_01",
                title="Prior Authorization Requirement",
                section_number="3.1",
                text="Prior authorization is strictly required for non-emergency hospital stays.",
                page_number=3,
                category=CoverageCategory.INPATIENT_HOSPITAL,
                is_limitation=True,
            )
        ],
        exclusions=["Cosmetic surgery", "Experimental treatments"],
    )
