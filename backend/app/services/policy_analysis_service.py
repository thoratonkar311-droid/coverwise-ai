from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

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


@dataclass
class ExtractedAnalysisOutput:
    """Comprehensive analysis result bridging AI extraction and calculation rules."""

    coverage_status: str  # likely_covered, partially_covered, not_determined, not_covered
    coverage_information: str
    deductible: Optional[float] = None
    copay: Optional[float] = None
    copay_percentage: Optional[float] = None
    coverage_limit: Optional[float] = None
    exclusions: List[str] = field(default_factory=list)
    waiting_periods: Optional[str] = None
    confidence: float = 0.0
    explanation: str = ""
    evidence_references: List[EvidenceItem] = field(default_factory=list)
    raw_ai_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_structured_result(self) -> StructuredAIAnalysisResult:
        """Convert to strict AI contract Pydantic schema."""
        return StructuredAIAnalysisResult(
            coverage_status=self.coverage_status,
            coverage_information=self.coverage_information,
            rules=StructuredPolicyRules(
                deductible=self.deductible,
                copay_fixed=self.copay,
                copay_percentage=self.copay_percentage,
                coverage_limit=self.coverage_limit,
                exclusions=self.exclusions,
                waiting_periods=self.waiting_periods,
                has_policy_rules=self.coverage_status not in ("not_determined", "not_covered"),
            ),
            exclusions=self.exclusions,
            waiting_periods=self.waiting_periods,
            evidence=self.evidence_references,
            confidence=self.confidence,
            warnings=[f"Sub-limit of Rs. {self.coverage_limit:,.2f} applies"] if self.coverage_limit else [],
            explanation=self.explanation,
            raw_ai_metadata=self.raw_ai_metadata,
        )

    @classmethod
    def from_structured_result(cls, res: StructuredAIAnalysisResult) -> "ExtractedAnalysisOutput":
        """Instantiate from strict AI contract Pydantic schema."""
        return cls(
            coverage_status=res.coverage_status,
            coverage_information=res.coverage_information,
            deductible=res.rules.deductible,
            copay=res.rules.copay_fixed,
            copay_percentage=res.rules.copay_percentage,
            coverage_limit=res.rules.coverage_limit,
            exclusions=res.exclusions,
            waiting_periods=res.waiting_periods,
            confidence=res.confidence,
            explanation=res.explanation,
            evidence_references=res.evidence,
            raw_ai_metadata=res.raw_ai_metadata,
        )


class PolicyAnalysisServiceInterface(ABC):
    """
    Abstract Service Interface for Policy Intelligence, Coverage Analysis, and Document Extraction.

    Designed for Member 3 (AI/ML) to seamlessly plug in OCR (PaddleOCR), LLM extraction (Qwen/Ollama),
    and RAG semantic search without modifying backend API routes or database handlers.
    """

    @abstractmethod
    def extract_policy_information(
        self,
        input_data: DocumentExtractionInput,
    ) -> ExtractedPolicyInfo:
        """Extract high-level policy document metadata and summary via OCR/LLM pipeline."""
        pass

    @abstractmethod
    def analyze_coverage(
        self,
        policy: Policy,
        treatment_name: str,
        db: Session,
        hospital_quote: Optional[float] = None,
    ) -> ExtractedAnalysisOutput:
        """Analyze policy document clauses against a specific medical treatment query."""
        pass

    @abstractmethod
    def retrieve_evidence(
        self,
        input_data: EvidenceQueryInput,
    ) -> EvidenceRetrievalOutput:
        """Retrieve supporting clauses and traceable citations via semantic/RAG query."""
        pass


class MockPolicyAnalysisService(PolicyAnalysisServiceInterface):
    """
    Default mock implementation providing realistic policy intelligence scenarios.

    Adheres strictly to the principle:
    'Do not invent policy facts. If no reliable policy rule is available, return not_determined.'
    """

    def extract_policy_information(
        self,
        input_data: DocumentExtractionInput,
    ) -> ExtractedPolicyInfo:
        """Mock policy document extraction based on filename or contents."""
        name_lower = input_data.filename.lower()
        text_lower = (input_data.raw_text or "").lower()

        # Inferred insurer and plan
        if "star" in name_lower or "star" in text_lower:
            insurer = "Star Health & Allied Insurance"
            plan = "Star Comprehensive Health Insurance Plan"
            policy_num = "STAR-COMP-2024-9104"
            sum_insured = 1000000.0
        elif "bajaj" in name_lower or "bajaj" in text_lower:
            insurer = "Bajaj Allianz General Insurance"
            plan = "Health Guard Gold Plan"
            policy_num = "BAGI-HG-882310"
            sum_insured = 750000.0
        elif "care" in name_lower or "religare" in name_lower or "care" in text_lower:
            insurer = "Care Health Insurance"
            plan = "Care Advantage Elite"
            policy_num = "CARE-ADV-441092"
            sum_insured = 500000.0
        elif "hdfc" in name_lower or "ergo" in name_lower or "hdfc" in text_lower:
            insurer = "HDFC ERGO General Insurance"
            plan = "Optima Secure"
            policy_num = "HDFC-OS-300188"
            sum_insured = 1000000.0
        else:
            insurer = "National Health Assurance Co."
            plan = "Standard Comprehensive Mediclaim"
            policy_num = "POL-2024-8849201"
            sum_insured = 500000.0

        return ExtractedPolicyInfo(
            insurer_name=insurer,
            plan_name=plan,
            policy_number=policy_num,
            policy_holder_name="Rajesh Kumar Sharma",
            sum_insured=sum_insured,
            validity_period="01-Apr-2024 to 31-Mar-2025",
            summary=(
                f"Comprehensive health policy issued by {insurer} offering inpatient hospitalization, "
                "day-care procedures, organ donor expenses, and AYUSH coverage subject to specific procedure sub-limits."
            ),
            metadata={
                "source_file": input_data.filename,
                "mime_type": input_data.content_type,
                "page_count": 28,
                "ocr_engine": "mock_paddle_ocr_v4",
                "extracted_sections": ["Preamble", "Definitions", "Benefits", "Waiting Periods", "Exclusions"],
            },
            confidence=0.95,
        )

    def analyze_coverage(
        self,
        policy: Policy,
        treatment_name: str,
        db: Session,
        hospital_quote: Optional[float] = None,
    ) -> ExtractedAnalysisOutput:
        clean_treatment = treatment_name.strip().lower()
        doc_name = policy.filename or "policy_document.pdf"

        # Scenario 1: Cataract Surgery (common sub-limit)
        if "cataract" in clean_treatment:
            return ExtractedAnalysisOutput(
                coverage_status="partially_covered",
                coverage_information="Covered subject to standard optical procedure sub-limit.",
                deductible=0.0,
                copay=0.0,
                copay_percentage=0.0,
                coverage_limit=40000.0,
                exclusions=["Premium multifocal intraocular lenses (patient pays difference)", "Cosmetic tinting"],
                waiting_periods="24 months for pre-existing or age-related cataracts",
                confidence=0.94,
                explanation="Cataract surgery is covered under day-care procedures, but capped at Rs. 40,000 per eye under Section 4.B.",
                evidence_references=[
                    EvidenceItem(
                        document_source=doc_name,
                        page=12,
                        clause_section="Section 4.B - Specified Procedure Sub-limits",
                        extracted_text="Cataract surgeries are subject to a maximum claim limit of Rs. 40,000 per eye inclusive of intraocular lens.",
                        interpretation="The insurer pays up to 40,000 INR per eye. Standard monofocal lenses are included.",
                        confidence=0.95,
                    )
                ],
            )

        # Scenario 2: Knee Replacement / Joint Surgery (co-pay and high sublimit)
        elif "knee" in clean_treatment or "joint" in clean_treatment:
            return ExtractedAnalysisOutput(
                coverage_status="partially_covered",
                coverage_information="Covered with a 10% co-payment and 24-month joint disease waiting period.",
                deductible=5000.0,
                copay=0.0,
                copay_percentage=10.0,
                coverage_limit=250000.0,
                exclusions=["Experimental synthetic robotic implants", "Specialist private nursing charges"],
                waiting_periods="24 months waiting period for joint replacement unless due to accidental injury",
                confidence=0.91,
                explanation="Joint replacement surgery is covered up to Rs. 2,50,000 per joint with a mandatory 10% co-payment.",
                evidence_references=[
                    EvidenceItem(
                        document_source=doc_name,
                        page=15,
                        clause_section="Section 6.3 - Major Joint Surgeries",
                        extracted_text="Total Knee Arthroplasty is admissible after 24 continuous months of coverage with 10% co-pay.",
                        interpretation="Patient pays 10% of eligible expenses after deductible; 2-year waiting period applies.",
                        confidence=0.92,
                    )
                ],
            )

        # Scenario 3: Heart Stent / Angioplasty (likely covered, standard sum insured limit)
        elif "heart" in clean_treatment or "stent" in clean_treatment or "angioplasty" in clean_treatment:
            return ExtractedAnalysisOutput(
                coverage_status="likely_covered",
                coverage_information="Covered under standard inpatient cardiovascular hospitalization.",
                deductible=0.0,
                copay=0.0,
                copay_percentage=0.0,
                coverage_limit=500000.0,
                exclusions=["Experimental biodegradable non-FDA approved stents"],
                waiting_periods="30 days initial waiting period (waived for emergencies)",
                confidence=0.96,
                explanation="Cardiovascular interventions including stent placement are covered up to the base sum insured.",
                evidence_references=[
                    EvidenceItem(
                        document_source=doc_name,
                        page=8,
                        clause_section="Section 3.1 - Inpatient Hospitalization Care",
                        extracted_text="Medical expenses incurred for cardiovascular interventions including PTCA stenting are admissible.",
                        interpretation="Inpatient hospitalization and ICU charges are covered subject to annual sum insured.",
                        confidence=0.97,
                    )
                ],
            )

        # Scenario 4: Appendectomy / General Surgery (fully covered up to limit)
        elif "append" in clean_treatment or "hernia" in clean_treatment:
            return ExtractedAnalysisOutput(
                coverage_status="likely_covered",
                coverage_information="Fully covered as an emergency/acute inpatient surgery.",
                deductible=0.0,
                copay=0.0,
                copay_percentage=0.0,
                coverage_limit=300000.0,
                exclusions=["Non-medical hygiene kits", "Admission convenience charges"],
                waiting_periods="None for acute appendicitis (emergency)",
                confidence=0.95,
                explanation="Acute emergency surgeries are covered without special sub-limits up to sum insured.",
                evidence_references=[
                    EvidenceItem(
                        document_source=doc_name,
                        page=6,
                        clause_section="Section 2.4 - Emergency Hospitalization",
                        extracted_text="Emergency acute surgeries required for life-threatening conditions are payable immediately.",
                        interpretation="Immediate coverage with zero waiting period for acute emergency surgeries.",
                        confidence=0.96,
                    )
                ],
            )

        # Scenario 5: Cosmetic Surgery / Dental (explicitly excluded)
        elif any(term in clean_treatment for term in ("cosmetic", "rhinoplasty", "veneer", "botox", "liposuction")):
            return ExtractedAnalysisOutput(
                coverage_status="not_covered",
                coverage_information="Excluded under General Policy Exclusions.",
                deductible=None,
                copay=None,
                copay_percentage=None,
                coverage_limit=0.0,
                exclusions=["Aesthetic or cosmetic surgery", "Dental surgery unless caused by accidental bodily injury"],
                waiting_periods="Permanently excluded",
                confidence=0.98,
                explanation="Aesthetic and cosmetic treatments are permanently excluded under Section 7 (General Exclusions).",
                evidence_references=[
                    EvidenceItem(
                        document_source=doc_name,
                        page=22,
                        clause_section="Section 7.1 - Permanent Exclusions",
                        extracted_text="Any treatment, surgery, or procedure undertaken for aesthetic or cosmetic enhancement is excluded.",
                        interpretation="Cosmetic interventions are non-payable under any circumstances.",
                        confidence=0.99,
                    )
                ],
            )

        # Scenario 6: Unknown, ambiguous or unlisted treatment -> "not_determined"
        # "Do not invent policy facts. If no reliable policy rule is available, return: not_determined"
        else:
            return ExtractedAnalysisOutput(
                coverage_status="not_determined",
                coverage_information="No specific coverage determination could be made for this treatment from the policy document.",
                deductible=None,
                copay=None,
                copay_percentage=None,
                coverage_limit=None,
                exclusions=[],
                waiting_periods=None,
                confidence=0.25,
                explanation=(
                    f"No explicit clause, sub-limit, or exclusion matching '{treatment_name}' was found in {doc_name}. "
                    "A formal pre-authorization request or medical underwriter review is recommended."
                ),
                evidence_references=[],
                raw_ai_metadata={"unmatched_query": treatment_name},
            )

    def retrieve_evidence(
        self,
        input_data: EvidenceQueryInput,
    ) -> EvidenceRetrievalOutput:
        """Search policy clauses and retrieve traceable citations supporting semantic queries."""
        q_clean = input_data.query.strip().lower()
        doc = input_data.document_source or "policy_document.pdf"
        matched_items: List[EvidenceItem] = []

        if "cataract" in q_clean or "eye" in q_clean or "optical" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=12,
                    clause_section="Section 4.B - Specified Procedure Sub-limits",
                    extracted_text="Cataract surgeries are subject to a maximum claim limit of Rs. 40,000 per eye inclusive of intraocular lens.",
                    interpretation="Optical claims for cataracts capped at Rs. 40,000 per eye.",
                    confidence=0.95,
                )
            )
        if "knee" in q_clean or "joint" in q_clean or "ortho" in q_clean or "copay" in q_clean or "co-pay" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=15,
                    clause_section="Section 6.3 - Major Joint Surgeries",
                    extracted_text="Total Knee Arthroplasty is admissible after 24 continuous months of coverage with 10% co-pay.",
                    interpretation="10% co-pay applies to joint surgeries after 2-year waiting period.",
                    confidence=0.92,
                )
            )
        if "heart" in q_clean or "cardiac" in q_clean or "stent" in q_clean or "angioplasty" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=8,
                    clause_section="Section 3.1 - Inpatient Hospitalization Care",
                    extracted_text="Medical expenses incurred for cardiovascular interventions including PTCA stenting are admissible.",
                    interpretation="Cardiovascular hospitalization payable up to sum insured.",
                    confidence=0.97,
                )
            )
        if "room" in q_clean or "icu" in q_clean or "rent" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=5,
                    clause_section="Section 2.1 - Room Rent and ICU Eligibility",
                    extracted_text="Room rent is capped at 1% of Sum Insured per day; ICU charges capped at 2% of Sum Insured per day.",
                    interpretation="Daily room rent capped at 1% of base sum insured.",
                    confidence=0.93,
                )
            )
        if "cosmetic" in q_clean or "exclusion" in q_clean or "aesthetic" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=22,
                    clause_section="Section 7.1 - Permanent Exclusions",
                    extracted_text="Any treatment, surgery, or procedure undertaken for aesthetic or cosmetic enhancement is excluded.",
                    interpretation="Cosmetic and aesthetic treatments are non-payable.",
                    confidence=0.99,
                )
            )
        if "waiting" in q_clean or "pre-existing" in q_clean or "ped" in q_clean:
            matched_items.append(
                EvidenceItem(
                    document_source=doc,
                    page=10,
                    clause_section="Section 5.1 - Pre-existing Diseases (PED)",
                    extracted_text="Pre-existing diseases covered after 36 continuous months of insurance with the company.",
                    interpretation="Standard 36-month waiting period applies for pre-existing medical conditions.",
                    confidence=0.94,
                )
            )

        limited_items = matched_items[: input_data.max_results]
        summary = (
            f"Found {len(limited_items)} relevant policy clause(s) for '{input_data.query}'."
            if limited_items
            else f"No specific clauses found matching '{input_data.query}' in policy documents."
        )

        return EvidenceRetrievalOutput(
            query=input_data.query,
            evidence_items=limited_items,
            summary=summary,
        )


# Default singleton instance for dependency injection
default_policy_analysis_service = MockPolicyAnalysisService()


def get_policy_analysis_service() -> PolicyAnalysisServiceInterface:
    """Dependency provider for policy analysis service."""
    return default_policy_analysis_service
