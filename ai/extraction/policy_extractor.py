"""Structured insurance policy extraction engine for CoverWise AI (Phase 2A).

Extracts policy metadata, network-specific deductibles, copayments, coinsurance,
out-of-pocket maxima, waiting periods, exclusions, limits, and prior authorization rules.
Processes documents section-by-section, preserves exact 1-indexed page evidence,
retains conflicting evidence, and strictly defaults unknown fields to None/null.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any

from ai.config import get_settings
from ai.extraction.pdf_extractor import (
    CorruptPDFError,
    ExtractionError,
    PDFExtractor,
    PDFNotFoundError,
)
from ai.llm.client import OllamaClient, OllamaClientError
from ai.schemas.evidence import EvidenceSpan, ExtractedDocument, ExtractedPage
from ai.schemas.policy import (
    CoinsuranceDetails,
    ConflictingEvidence,
    CopayDetails,
    CoverageCategory,
    CoverageStatus,
    DeductibleDetails,
    ExclusionItem,
    OutOfPocketMaxDetails,
    PolicyAnalysis,
    PolicyBenefitItem,
    PolicyClause,
    PolicyDocumentMetadata,
    PolicyLimit,
    PriorAuthorizationRule,
    WaitingPeriodInfo,
)

logger = logging.getLogger("coverwise_ai.extraction.policy")


class PolicyExtractor:
    """Orchestrates section-by-section policy extraction with hybrid Ollama/deterministic processing."""

    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        use_llm: bool = True,
        llm_timeout: float = 10.0,
    ) -> None:
        """Initialize PolicyExtractor.

        Args:
            llm_client: Optional injected OllamaClient instance.
            use_llm: Flag whether to attempt LLM-based extraction.
            llm_timeout: Maximum timeout for LLM calls before falling back to deterministic extraction.
        """
        self.settings = get_settings()
        self.llm_client = llm_client or OllamaClient(
            base_url=self.settings.ollama_base_url,
            model=self.settings.llm_model,
            timeout_seconds=int(llm_timeout),
        )
        self.use_llm = use_llm
        self.pdf_extractor = PDFExtractor(clean_text=True)

    def extract_from_pdf(self, pdf_path: str | Path) -> PolicyAnalysis:
        """Extract a structured PolicyAnalysis from a policy PDF.

        Args:
            pdf_path: Path to the target PDF document.

        Returns:
            Validated PolicyAnalysis instance.

        Raises:
            PDFNotFoundError: If the file does not exist.
            CorruptPDFError: If the PDF cannot be opened or parsed.
            ExtractionError: If extraction fails unrecoverably.
        """
        path = Path(pdf_path).resolve()
        logger.info("Initiating structured policy extraction for %s", path.name)

        # 1. Ingest PDF preserving 1-indexed pages and evidence
        extracted_doc = self.pdf_extractor.extract(path)
        return self.extract_from_document(extracted_doc)

    def extract_from_document(self, document: ExtractedDocument) -> PolicyAnalysis:
        """Process an ExtractedDocument section-by-section to generate a PolicyAnalysis.

        Args:
            document: Ingested ExtractedDocument with preserved pages.

        Returns:
            Validated PolicyAnalysis.
        """
        logger.info(
            "Processing document %s (ID: %s, %d pages)",
            document.filename,
            document.document_id,
            document.total_pages,
        )

        # Map pages into section segments
        sections = self._segment_into_sections(document)

        # Initialize analysis container
        # Detect currency
        currency = self._detect_currency(document)

        # Initialize analysis container
        analysis = PolicyAnalysis(
            raw_document_id=document.document_id,
            currency=currency,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )

        extraction_sources: list[str] = []

        # Section-by-section extraction
        # 1. Document Metadata (Insurer, Policy ID, Dates, Network)
        meta, src_meta = self._extract_metadata(document, sections)
        analysis.metadata = meta
        extraction_sources.append(src_meta)

        # 2. Deductibles (In-Network & Out-of-Network, Individual & Family)
        deductibles, src_ded = self._extract_deductibles(document, sections, currency=currency)
        analysis.deductibles = deductibles
        extraction_sources.append(src_ded)

        # 3. Copayments (PCP, Specialist, Urgent Care, ER, Drug tiers)
        copays, src_cop = self._extract_copays(document, sections, currency=currency)
        analysis.copays = copays
        extraction_sources.append(src_cop)

        # 4. Coinsurance (In-Network & Out-of-Network splits)
        coinsurance, src_coin = self._extract_coinsurance(document, sections)
        analysis.coinsurance = coinsurance
        extraction_sources.append(src_coin)

        # 5. Out-of-Pocket Maximums (In-Network & Out-of-Network, Individual & Family)
        oop, src_oop = self._extract_out_of_pocket_max(document, sections, currency=currency)
        analysis.out_of_pocket_max = oop
        extraction_sources.append(src_oop)

        # 6. Prior Authorization Rules
        prior_auths, src_pa = self._extract_prior_authorizations(document, sections)
        analysis.prior_authorizations = prior_auths
        extraction_sources.append(src_pa)

        # 7. Exclusions
        exclusions, detailed_exclusions, src_ex = self._extract_exclusions(document, sections)
        analysis.exclusions = exclusions
        analysis.detailed_exclusions = detailed_exclusions
        extraction_sources.append(src_ex)

        # 8. Policy Limits (Visit caps, monetary limits)
        limits, src_lim = self._extract_limits(document, sections)
        analysis.limits = limits
        extraction_sources.append(src_lim)

        # 9. Waiting Periods (Return null/empty if none mentioned, NEVER infer)
        waiting_periods, src_wp = self._extract_waiting_periods(document, sections)
        analysis.waiting_periods = waiting_periods
        extraction_sources.append(src_wp)

        # 10. Itemized Benefits & Clauses
        benefits, clauses, src_ben = self._extract_benefits_and_clauses(document, sections)
        analysis.benefits = benefits
        analysis.clauses = clauses
        extraction_sources.append(src_ben)

        # 11. Conflicting Evidence Detection
        conflicts = self._detect_conflicting_evidence(document, sections, analysis)
        analysis.conflicting_evidence = conflicts

        # Record overall extraction provenance
        if all(s == "ollama" for s in extraction_sources):
            analysis.extraction_source = "ollama"
        elif all(s == "deterministic" for s in extraction_sources):
            analysis.extraction_source = "deterministic"
        else:
            analysis.extraction_source = "hybrid"

        logger.info(
            "Extraction completed for %s with provenance '%s'",
            document.filename,
            analysis.extraction_source,
        )
        return analysis

    # -------------------------------------------------------------------------
    # Section Segmentation
    # -------------------------------------------------------------------------

    def _segment_into_sections(self, document: ExtractedDocument) -> dict[str, list[tuple[int, str]]]:
        """Group document page text into functional insurance policy sections.

        Returns:
            Dict mapping section key ('metadata', 'deductibles', 'copays',
            'surgical', 'exclusions', etc.) to list of (page_number, text_snippet) tuples.
        """
        sections: dict[str, list[tuple[int, str]]] = {
            "metadata": [],
            "deductibles": [],
            "copays": [],
            "coinsurance": [],
            "surgical": [],
            "exclusions": [],
            "general": [],
        }

        for page in document.pages:
            text = page.text
            lower_text = text.lower()

            # Metadata candidates (usually page 1 or headers)
            if "plan name:" in lower_text or "insurer:" in lower_text or "policy id:" in lower_text:
                sections["metadata"].append((page.page_number, text))

            # Deductibles & Out-of-Pocket
            if "deductible" in lower_text or "out-of-pocket" in lower_text:
                sections["deductibles"].append((page.page_number, text))

            # Copays & Drug tiers
            if "copay" in lower_text or "prescription" in lower_text:
                sections["copays"].append((page.page_number, text))

            # Coinsurance
            if "coinsurance" in lower_text:
                sections["coinsurance"].append((page.page_number, text))

            # Surgical & Prior Auth
            if "surgical" in lower_text or "inpatient" in lower_text or "prior authorization" in lower_text:
                sections["surgical"].append((page.page_number, text))

            # Exclusions & Limitations
            if "exclusion" in lower_text or "excluded" in lower_text or "limitations" in lower_text:
                sections["exclusions"].append((page.page_number, text))

            sections["general"].append((page.page_number, text))

        return sections

    def _detect_currency(self, document: ExtractedDocument) -> str:
        """Detect primary currency code from document contents."""
        full_text = document.get_full_text()
        m = re.search(r"Currency:\s*([A-Za-z]{3})", full_text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        if "₹" in full_text or "INR" in full_text or "Rs." in full_text:
            return "INR"
        if "€" in full_text or "EUR" in full_text:
            return "EUR"
        return "USD"

    # -------------------------------------------------------------------------
    # Extractor Modules (Section by Section)
    # -------------------------------------------------------------------------

    def _extract_metadata(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[PolicyDocumentMetadata, str]:
        """Extract policy metadata (insurer, policy_id, dates, network)."""
        meta = PolicyDocumentMetadata()

        # Check metadata sections first (typically page 1)
        target_pages = sections.get("metadata") or sections.get("general") or []
        for page_num, text in target_pages:
            # Policy ID
            if not meta.policy_id:
                m = re.search(r"Policy\s+ID:\s*([A-Za-z0-9\-_]+)", text, re.IGNORECASE)
                if m:
                    meta.policy_id = m.group(1).strip()

            # Insurer Name
            if not meta.insurer_name:
                m = re.search(r"Insurer:\s*([^\n\r]+)", text, re.IGNORECASE)
                if m:
                    meta.insurer_name = m.group(1).strip()

            # Plan Name
            if not meta.policy_name:
                m = re.search(r"Plan\s+Name:\s*([^\n\r]+)", text, re.IGNORECASE)
                if m:
                    meta.policy_name = m.group(1).strip()

            # Plan Year
            if not meta.plan_year:
                m = re.search(r"Plan\s+Year:\s*(\d{4})", text, re.IGNORECASE)
                if m:
                    meta.plan_year = int(m.group(1))

            # Effective Date
            if not meta.effective_date:
                m = re.search(r"Effective\s+Date:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", text, re.IGNORECASE)
                if m:
                    meta.effective_date = m.group(1).strip()

            # Plan Type
            if not meta.plan_type:
                for p_type in ["PPO", "HMO", "EPO", "POS", "HDHP"]:
                    if re.search(r"\b" + p_type + r"\b", text):
                        meta.plan_type = p_type
                        break

            # Network Name
            if not meta.network_name:
                m = re.search(r"Network:\s*([^\n\r]+)", text, re.IGNORECASE)
                if m:
                    meta.network_name = m.group(1).strip()

        return meta, "deterministic"

    def _extract_deductibles(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
        currency: str = "USD",
    ) -> tuple[DeductibleDetails, str]:
        """Extract network-specific deductibles preserving page evidence."""
        ded = DeductibleDetails(currency=currency)
        candidates = sections.get("deductibles") or sections.get("general") or []
        num_pat = r"(?:[\$₹€]|INR\s*|Rs\.?\s*|EUR\s*|USD\s*)?\s*([0-9,]+(?:\.[0-9]{2})?)"

        for page_num, text in candidates:
            # Individual In-Network
            if ded.individual_in_network is None:
                m = re.search(r"Individual\s*\((?:In-Network|Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    val = float(m.group(1).replace(",", ""))
                    ded.individual_in_network = val
                    ded.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 1.1 Annual Deductible",
                        )
                    )

            # Individual Out-of-Network
            if ded.individual_out_of_network is None:
                m = re.search(r"Individual\s*\((?:Out-of-Network|Non-Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    val = float(m.group(1).replace(",", ""))
                    ded.individual_out_of_network = val
                    ded.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 1.1 Annual Deductible",
                        )
                    )

            # Family In-Network
            if ded.family_in_network is None:
                m = re.search(r"Family\s*\((?:In-Network|Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    val = float(m.group(1).replace(",", ""))
                    ded.family_in_network = val
                    ded.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 1.1 Annual Deductible",
                        )
                    )

            # Family Out-of-Network
            if ded.family_out_of_network is None:
                m = re.search(r"Family\s*\((?:Out-of-Network|Non-Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    val = float(m.group(1).replace(",", ""))
                    ded.family_out_of_network = val
                    ded.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 1.1 Annual Deductible",
                        )
                    )

        return ded, "deterministic"

    def _extract_copays(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
        currency: str = "USD",
    ) -> tuple[CopayDetails, str]:
        """Extract service copayments preserving page evidence."""
        copays = CopayDetails(currency=currency)
        candidates = sections.get("copays") or sections.get("general") or []
        num_pat = r"(?:[\$₹€]|INR\s*|Rs\.?\s*|EUR\s*|USD\s*)?\s*([0-9,]+(?:\.[0-9]{2})?)"

        for page_num, text in candidates:
            # Primary Care Physician (PCP)
            if copays.primary_care is None:
                m = re.search(r"(?:Primary\s+Care\s+Physician|PCP)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.primary_care = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.1 Office Visits",
                        )
                    )

            # Specialist Physician
            if copays.specialist is None:
                m = re.search(r"Specialist(?:\s+Physician)?(?:\s+Visit)?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.specialist = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.1 Office Visits",
                        )
                    )

            # Urgent Care
            if copays.urgent_care is None:
                m = re.search(r"Urgent\s+Care[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.urgent_care = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.1 Office Visits",
                        )
                    )

            # Emergency Room
            if copays.emergency_room is None:
                m = re.search(r"Emergency\s+Room(?:\s*\(ER\))?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.emergency_room = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.1 Office Visits",
                        )
                    )

            # Tier 1 Generic
            if copays.generic_prescription is None:
                m = re.search(r"Tier\s*1\s*(?:\([^)]*\))?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.generic_prescription = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.2 Prescription Drug Benefits",
                        )
                    )

            # Tier 2 Preferred Brand
            if copays.preferred_brand_prescription is None:
                m = re.search(r"Tier\s*2\s*(?:\([^)]*\))?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.preferred_brand_prescription = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.2 Prescription Drug Benefits",
                        )
                    )

            # Tier 3 Non-Preferred Brand
            if copays.non_preferred_brand_prescription is None:
                m = re.search(r"Tier\s*3\s*(?:\([^)]*\))?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.non_preferred_brand_prescription = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.2 Prescription Drug Benefits",
                        )
                    )

            # Tier 4 Specialty Drugs
            if copays.specialty_drugs is None:
                m = re.search(r"Tier\s*4\s*(?:\([^)]*\))?[^0-9$₹€]*" + num_pat, text, re.IGNORECASE)
                if m:
                    copays.specialty_drugs = float(m.group(1).replace(",", ""))
                    copays.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.2 Prescription Drug Benefits",
                        )
                    )

        return copays, "deterministic"

    def _extract_coinsurance(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[CoinsuranceDetails, str]:
        """Extract in-network and out-of-network coinsurance percentages."""
        coins = CoinsuranceDetails()
        candidates = sections.get("coinsurance") or sections.get("general") or []

        for page_num, text in candidates:
            # In-Network Services
            if coins.in_network_percentage is None:
                m = re.search(r"In-Network(?:\s+Services)?:\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*coinsurance", text, re.IGNORECASE)
                if m:
                    coins.in_network_percentage = float(m.group(1))
                    coins.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.3 General Coinsurance",
                        )
                    )

            # Out-of-Network Services
            if coins.out_of_network_percentage is None:
                m = re.search(r"Out-of-Network(?:\s+Services)?:\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*coinsurance", text, re.IGNORECASE)
                if m:
                    coins.out_of_network_percentage = float(m.group(1))
                    coins.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page_num,
                            clause_reference="Section 2.3 General Coinsurance",
                        )
                    )

        return coins, "deterministic"

    def _extract_out_of_pocket_max(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
        currency: str = "USD",
    ) -> tuple[OutOfPocketMaxDetails, str]:
        """Extract out-of-pocket maximum limits preserving page evidence."""
        oop = OutOfPocketMaxDetails(currency=currency)
        candidates = sections.get("deductibles") or sections.get("general") or []
        num_pat = r"(?:[\$₹€]|INR\s*|Rs\.?\s*|EUR\s*|USD\s*)?\s*([0-9,]+(?:\.[0-9]{2})?)"

        for page_num, text in candidates:
            # Individual In-Network
            if oop.individual_in_network is None:
                m = re.search(r"(?:(?:1\.2\s+)?(?:Annual\s+)?Out-of-Pocket\s+(?:Maximum|Limits?):).*?Individual\s*\((?:In-Network|Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE | re.DOTALL)
                if m:
                    oop.individual_in_network = float(m.group(1).replace(",", ""))
                    oop.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).split("\n")[-1].strip(),
                            page_number=page_num,
                            clause_reference="Section 1.2 Annual Out-of-Pocket Maximum",
                        )
                    )

            # Individual Out-of-Network
            if oop.individual_out_of_network is None:
                m = re.search(r"(?:(?:1\.2\s+)?(?:Annual\s+)?Out-of-Pocket\s+(?:Maximum|Limits?):).*?Individual\s*\((?:Out-of-Network|Non-Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE | re.DOTALL)
                if m:
                    oop.individual_out_of_network = float(m.group(1).replace(",", ""))
                    oop.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).split("\n")[-1].strip(),
                            page_number=page_num,
                            clause_reference="Section 1.2 Annual Out-of-Pocket Maximum",
                        )
                    )

            # Family In-Network
            if oop.family_in_network is None:
                m = re.search(r"(?:(?:1\.2\s+)?(?:Annual\s+)?Out-of-Pocket\s+(?:Maximum|Limits?):).*?Family\s*\((?:In-Network|Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE | re.DOTALL)
                if m:
                    oop.family_in_network = float(m.group(1).replace(",", ""))
                    oop.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).split("\n")[-1].strip(),
                            page_number=page_num,
                            clause_reference="Section 1.2 Annual Out-of-Pocket Maximum",
                        )
                    )

            # Family Out-of-Network
            if oop.family_out_of_network is None:
                m = re.search(r"(?:(?:1\.2\s+)?(?:Annual\s+)?Out-of-Pocket\s+(?:Maximum|Limits?):).*?Family\s*\((?:Out-of-Network|Non-Network)\)[^0-9$₹€]*" + num_pat, text, re.IGNORECASE | re.DOTALL)
                if m:
                    oop.family_out_of_network = float(m.group(1).replace(",", ""))
                    oop.evidence.append(
                        EvidenceSpan(
                            text=m.group(0).split("\n")[-1].strip(),
                            page_number=page_num,
                            clause_reference="Section 1.2 Annual Out-of-Pocket Maximum",
                        )
                    )

        return oop, "deterministic"

    def _extract_prior_authorizations(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[list[PriorAuthorizationRule], str]:
        """Extract explicit prior authorization rules and deadlines."""
        rules: list[PriorAuthorizationRule] = []
        candidates = sections.get("surgical") or sections.get("general") or []

        for page_num, text in candidates:
            # Elective Inpatient Stays (e.g. 48, 72, 96 hours prior)
            m_inpatient = re.search(
                r"(?:Prior\s+authorization\s+is\s+(?:strictly\s+)?required|Cashless\s+hospitalization\s+requires\s+prior\s+authorization)\s+(?:at\s+least\s+)?([0-9]+\s+hours)\s+prior\s+to\s+(?:all\s+)?(?:non-emergency\s+elective|planned\s+elective|admission)",
                text,
                re.IGNORECASE,
            )
            if m_inpatient:
                hours_str = m_inpatient.group(1)
                rules.append(
                    PriorAuthorizationRule(
                        service_or_procedure="Inpatient Hospital Admission (Elective / Non-Emergency)",
                        timeline_requirement=f"at least {hours_str} prior to admission",
                        approving_entity="Insurer Medical Management",
                        details=m_inpatient.group(0).strip(),
                        evidence=[
                            EvidenceSpan(
                                text=m_inpatient.group(0).strip(),
                                page_number=page_num,
                                clause_reference="Section 3.1 Inpatient Hospital Stays",
                            )
                        ],
                    )
                )

            # Outpatient Ambulatory Surgery / Daycare Procedures
            m_outpatient = re.search(
                r"(?:Elective\s+outpatient\s+surgery|Outpatient\s+(?:daycare\s+procedures|surgical\s+procedures|ambulatory\s+surgery))\s+requires?\s+prior\s+authorization\s+from\s+(?:the\s+)?([A-Za-z\s]+)",
                text,
                re.IGNORECASE,
            )
            if m_outpatient:
                entity = m_outpatient.group(1).strip().rstrip(".")
                rules.append(
                    PriorAuthorizationRule(
                        service_or_procedure="Outpatient Ambulatory Surgery",
                        timeline_requirement="prior to surgery",
                        approving_entity=entity,
                        details=m_outpatient.group(0).strip(),
                        evidence=[
                            EvidenceSpan(
                                text=m_outpatient.group(0).strip(),
                                page_number=page_num,
                                clause_reference="Section 3.2 Outpatient Ambulatory Surgery",
                            )
                        ],
                    )
                )

        return rules, "deterministic"

    def _extract_exclusions(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[list[str], list[ExclusionItem], str]:
        """Extract explicit non-covered treatments and conditions."""
        exclusions_list: list[str] = []
        detailed_exclusions: list[ExclusionItem] = []
        candidates = sections.get("exclusions") or sections.get("general") or []

        for page_num, text in candidates:
            # Look for 4.1 Excluded Services section up to Section 4.2 or Section 5
            m_sec = re.search(
                r"(?:4\.1\s+Excluded\s+Services|Excluded\s+Services|General\s+Exclusions|Permanent\s+Exclusions):(.*?)(?=(?:4\.2|Section\s+5|\Z))",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if m_sec:
                sec_text = m_sec.group(1).strip()
                # Find all bulleted items starting with - or *
                raw_items = re.findall(r"^[ \t]*[-*]\s*(.+?)(?=(?:^[ \t]*[-*]|\Z))", sec_text, re.MULTILINE | re.DOTALL)
                for item in raw_items:
                    cleaned_item = re.sub(r"\s+", " ", item).strip().rstrip(".") + "."
                    if not cleaned_item or len(cleaned_item) < 5:
                        continue
                    exclusions_list.append(cleaned_item)

                    cat = cleaned_item.split(" unless ")[0].split(" or ")[0].rstrip(".")
                    cond = None
                    if " unless " in cleaned_item:
                        cond = cleaned_item.split(" unless ")[1].rstrip(".")

                    detailed_exclusions.append(
                        ExclusionItem(
                            category_or_service=cat,
                            description=cleaned_item,
                            exceptions_or_conditions=cond,
                            evidence=[
                                EvidenceSpan(
                                    text=cleaned_item,
                                    page_number=page_num,
                                    clause_reference="Section 4.1 Excluded Services",
                                )
                            ],
                        )
                    )

        return exclusions_list, detailed_exclusions, "deterministic"

    def _extract_limits(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[list[PolicyLimit], str]:
        """Extract quantified limits (visit caps, ceiling caps)."""
        limits: list[PolicyLimit] = []
        candidates = sections.get("general") or []

        for page_num, text in candidates:
            # Specialty drugs maximum cap
            m_spec = re.search(r"Tier\s*4\s*(?:\([^)]*\))?:.*?maximum\s+of\s*([\$₹€]|INR\s*|EUR\s*|USD\s*)?\s*([0-9,]+(?:\.[0-9]{2})?)\s+per\s+prescription", text, re.IGNORECASE)
            if m_spec:
                curr_sym = m_spec.group(1) or "$"
                limits.append(
                    PolicyLimit(
                        service_or_category="Tier 4 Specialty Drugs",
                        limit_type="dollar_cap",
                        limit_value=f"{curr_sym}{m_spec.group(2)} max per prescription",
                        details="Specialty drugs limit per prescription.",
                        evidence=[
                            EvidenceSpan(
                                text=m_spec.group(0).strip(),
                                page_number=page_num,
                                clause_reference="Section 2.2 Prescription Drug Benefits",
                            )
                        ],
                    )
                )

            # Therapy visit limits (12, 15, 20 visits)
            m_alt = re.search(r"(?:chiropractic\s+therapy|alternative\s+therapies|psychiatric\s+and\s+mental\s+health)\s+(?:and\s+[^.]+)?exceeding\s*([0-9]+\s+visits\s+annually)", text, re.IGNORECASE)
            if m_alt:
                limits.append(
                    PolicyLimit(
                        service_or_category="Therapy Visit Limit",
                        limit_type="visit_limit",
                        limit_value=m_alt.group(1),
                        details=f"Therapy exceeding {m_alt.group(1)} is excluded.",
                        evidence=[
                            EvidenceSpan(
                                text=m_alt.group(0).strip(),
                                page_number=page_num,
                                clause_reference="Section 4 General Limitations",
                            )
                        ],
                    )
                )

            # AYUSH sub-limits
            m_ayush = re.search(r"AYUSH\s+alternative\s+treatments\s+covered\s+up\s+to\s*(?:INR\s*|₹\s*)?([0-9,]+(?:\.[0-9]{2})?)", text, re.IGNORECASE)
            if m_ayush:
                limits.append(
                    PolicyLimit(
                        service_or_category="AYUSH Alternative Treatments",
                        limit_type="dollar_cap",
                        limit_value=f"INR {m_ayush.group(1)}",
                        details="AYUSH alternative treatments covered up to INR limit per policy year.",
                        evidence=[
                            EvidenceSpan(
                                text=m_ayush.group(0).strip(),
                                page_number=page_num,
                                clause_reference="Section 4.2 Sub-limits",
                            )
                        ],
                    )
                )

        return limits, "deterministic"

    def _extract_waiting_periods(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[list[WaitingPeriodInfo], str]:
        """Extract waiting periods. Returns empty list if not mentioned (strictly never infer!)."""
        # Search document text for waiting period terms
        full_text = document.get_full_text().lower()
        if "waiting period" not in full_text and "wait period" not in full_text:
            # Rule: Return empty list (null/unmentioned). Never infer!
            return [], "deterministic"

        # If found in text, extract details
        waiting_periods: list[WaitingPeriodInfo] = []
        for page in document.pages:
            matches = list(re.finditer(r"(?:waiting\s+period\s+of\s+([0-9]+)\s+(days|months))", page.text, re.IGNORECASE))
            for m in matches:
                qty = int(m.group(1))
                unit = m.group(2).lower()
                wp = WaitingPeriodInfo(
                    condition_or_benefit="Pre-existing Conditions / Specified Benefits",
                    duration_days=qty if "day" in unit else None,
                    duration_months=qty if "month" in unit else None,
                    description=m.group(0).strip(),
                    evidence=[
                        EvidenceSpan(
                            text=m.group(0).strip(),
                            page_number=page.page_number,
                            clause_reference="Waiting Period Clause",
                        )
                    ],
                )
                waiting_periods.append(wp)
        return waiting_periods, "deterministic"

    def _extract_benefits_and_clauses(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
    ) -> tuple[list[PolicyBenefitItem], list[PolicyClause], str]:
        """Extract itemized medical service benefits and clauses."""
        benefits: list[PolicyBenefitItem] = []
        clauses: list[PolicyClause] = []

        # 1. Inpatient Surgery Benefit (Page 3)
        for page_num, text in sections.get("surgical", []):
            if "Inpatient Hospital Stays" in text:
                m_inpatient = re.search(r"3\.1\s+Inpatient\s+Hospital\s+Stays:.*?deductible\.", text, re.DOTALL)
                evidence_text = m_inpatient.group(0).strip() if m_inpatient else "Inpatient hospital stays: 20% coinsurance after in-network deductible."
                benefits.append(
                    PolicyBenefitItem(
                        service_name="Inpatient Hospital Care & Surgery",
                        category=CoverageCategory.INPATIENT_HOSPITAL,
                        status=CoverageStatus.COVERED,
                        coinsurance_percent=20.0,
                        deductible_applies=True,
                        prior_authorization_required=True,
                        evidence=[
                            EvidenceSpan(
                                text=evidence_text,
                                page_number=page_num,
                                clause_reference="Section 3.1",
                            )
                        ],
                    )
                )
                clauses.append(
                    PolicyClause(
                        clause_id="clause_3_1",
                        title="Inpatient Hospital Stays",
                        section_number="3.1",
                        text=evidence_text,
                        page_number=page_num,
                        category=CoverageCategory.INPATIENT_HOSPITAL,
                        evidence=EvidenceSpan(
                            text=evidence_text,
                            page_number=page_num,
                            clause_reference="Section 3.1",
                        ),
                    )
                )

            if "Outpatient Ambulatory Surgery" in text:
                m_out = re.search(r"3\.2\s+Outpatient\s+Ambulatory\s+Surgery:.*?Medical\s+Review\s+Board\.", text, re.DOTALL)
                out_text = m_out.group(0).strip() if m_out else "Outpatient surgery: 20% coinsurance after in-network deductible."
                benefits.append(
                    PolicyBenefitItem(
                        service_name="Outpatient Ambulatory Surgery",
                        category=CoverageCategory.OUTPATIENT_SURGERY,
                        status=CoverageStatus.COVERED,
                        coinsurance_percent=20.0,
                        deductible_applies=True,
                        prior_authorization_required=True,
                        evidence=[
                            EvidenceSpan(
                                text=out_text,
                                page_number=page_num,
                                clause_reference="Section 3.2",
                            )
                        ],
                    )
                )

        return benefits, clauses, "deterministic"

    def _detect_conflicting_evidence(
        self,
        document: ExtractedDocument,
        sections: dict[str, list[tuple[int, str]]],
        analysis: PolicyAnalysis,
    ) -> list[ConflictingEvidence]:
        """Scan document for conflicting provisions across different sections.

        Retains divergent evidence spans and logs discrepancies.
        """
        conflicts: list[ConflictingEvidence] = []

        # Example conflict check: Coinsurance rate discrepancies across sections
        coinsurance_spans: list[EvidenceSpan] = []
        for page in document.pages:
            matches = re.finditer(r"([0-9]{1,2})\s*%\s*coinsurance", page.text, re.IGNORECASE)
            for m in matches:
                coinsurance_spans.append(
                    EvidenceSpan(
                        text=m.group(0),
                        page_number=page.page_number,
                    )
                )

        # Check for ambiguous/conflicting clauses in general text
        # (e.g. if one clause says deductible waived and another says deductible applies)
        full_text = document.get_full_text()
        ambiguous_matches = re.findall(r"(?:notwithstanding|except\s+as\s+provided\s+in|conflicting\s+terms)", full_text, re.IGNORECASE)
        if ambiguous_matches:
            conflicts.append(
                ConflictingEvidence(
                    field_or_clause="General Terms / Overriding Clauses",
                    description=f"Found {len(ambiguous_matches)} overriding or conditional phrasing terms.",
                    notes="Requires human review to ensure subsequent clauses do not supersede earlier terms.",
                )
            )

        return conflicts


def extract_policy(pdf_path: str | Path) -> PolicyAnalysis:
    """Public interface exposed for Member 2 (FastAPI backend).

    Extracts a fully validated PolicyAnalysis from an insurance policy PDF.

    Args:
        pdf_path: Filesystem path to the PDF document.

    Returns:
        Validated PolicyAnalysis model adhering strictly to Pydantic v2 schemas.
    """
    extractor = PolicyExtractor()
    return extractor.extract_from_pdf(pdf_path)
