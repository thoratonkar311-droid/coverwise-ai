import logging
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.conversation import ConversationMessage, PolicyConversation
from app.models.policy import Policy
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.policy_repository import PolicyRepository
from app.schemas.conversation import (
    ConversationEvidenceResponse,
    ConversationMessageResponse,
    ConversationResponse,
)
from app.services.treatment_estimation_service import (
    TreatmentCostEstimationService,
    TreatmentScenarioInput,
    get_treatment_estimation_service,
)

logger = logging.getLogger("coverwise.services.conversation")


class ConversationService:
    """Orchestrates multi-turn policy conversational sessions, grounded retrieval, and scenario estimation."""

    def __init__(
        self,
        estimation_service: Optional[TreatmentCostEstimationService] = None,
    ) -> None:
        self.estimation_service = (
            estimation_service or get_treatment_estimation_service()
        )

    def create_conversation(
        self,
        db: Session,
        policy_id: int,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        initial_message: Optional[str] = None,
    ) -> PolicyConversation:
        """Initialize a new conversation session and optionally process initial inquiry."""
        policy_repo = PolicyRepository(db)
        policy = policy_repo.get_by_id(policy_id)
        if not policy:
            raise ValueError(f"Policy #{policy_id} not found.")

        repo = ConversationRepository(db)
        conv = repo.create(
            policy_id=policy.id,
            user_id=user_id,
            title=title or (f"Inquiry: {policy.plan_name or policy.filename}"),
        )

        if initial_message and initial_message.strip():
            self.post_message(
                db=db,
                conversation_id=conv.id,
                content=initial_message.strip(),
            )
            # Refresh to get updated message history
            conv = repo.get_by_id(conv.id) or conv

        return conv

    def post_message(
        self,
        db: Session,
        conversation_id: int,
        content: str,
        treatment_scenario: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """Process a user message, maintain conversational context, perform grounded retrieval, and reply."""
        repo = ConversationRepository(db)
        conv = repo.get_by_id(conversation_id)
        if not conv:
            raise ValueError(f"Conversation #{conversation_id} not found.")

        policy_repo = PolicyRepository(db)
        policy = policy_repo.get_by_id(conv.policy_id)
        if not policy:
            raise ValueError(f"Policy #{conv.policy_id} not found.")

        # 1. Record User Message
        user_msg = repo.add_message(
            conversation_id=conv.id,
            role="user",
            content=content,
            treatment_scenario=treatment_scenario,
        )

        # 2. Extract Prior Context from Conversation History
        history = [
            {"role": m.role, "content": m.content}
            for m in (conv.messages or [])
            if m.id != user_msg.id
        ]

        # 3. Check for Treatment Scenario or Cost Inquiries
        active_scenario = treatment_scenario or (conv.context_metadata or {}).get("active_scenario")
        # Only parse cost scenario if the user query explicitly asks for cost/quote calculation
        is_cost_inquiry = any(
            kw in content.lower()
            for kw in [
                "quote", "cost estimate", "estimate cost", "how much will it cost",
                "estimate my expense", "out of pocket calculation", "calculate my share",
                "how much will i pay", "how much does insurer pay", "calculate cost",
                "cost breakdown", "financial estimate"
            ]
        )
        parsed_scenario = self._try_parse_scenario(content, active_scenario, history=history) if is_cost_inquiry else None

        cost_estimate_data = None
        if parsed_scenario:
            try:
                estimate_res = self.estimation_service.estimate(
                    scenario=parsed_scenario,
                    policy=policy,
                )
                cost_estimate_data = estimate_res.model_dump()
                # Update conversation session context
                repo.update_context_metadata(
                    conversation_id=conv.id,
                    context_metadata={"active_scenario": parsed_scenario.model_dump()},
                )
            except Exception as exc:
                logger.warning(f"Error computing cost estimate for message: {exc}")

        # 4. Perform Policy Grounded Retrieval via AI/RAG engine
        qa_result = self._retrieve_policy_answer(
            policy=policy,
            question=content,
            history=history,
            cost_estimate_data=cost_estimate_data,
        )

        # 5. Persist Assistant Response
        assistant_msg = repo.add_message(
            conversation_id=conv.id,
            role="assistant",
            content=qa_result["answer"],
            confidence=qa_result.get("confidence", "High" if qa_result.get("grounded") else "Insufficient evidence"),
            is_grounded=qa_result.get("grounded", True),
            uncertainty_reason=qa_result.get("uncertainty_reason"),
            missing_information=qa_result.get("missing_information"),
            treatment_scenario=parsed_scenario.model_dump() if parsed_scenario else None,
            cost_estimate=cost_estimate_data,
        )

        # 6. Persist Evidence References
        for cit in qa_result.get("citations", []):
            repo.add_evidence_reference(
                message_id=assistant_msg.id,
                policy_id=policy.id,
                document_source=cit.get("document_name") or policy.filename,
                page=cit.get("page_number"),
                clause_section=cit.get("clause_title") or cit.get("clause_reference"),
                extracted_text=cit.get("verbatim_text"),
                interpretation=cit.get("interpretation") or f"Grounded evidence from page {cit.get('page_number')}",
                confidence=cit.get("confidence", 0.95),
            )

        db.refresh(assistant_msg)
        return assistant_msg

    def _try_parse_scenario(
        self,
        content: str,
        existing_scenario: Optional[Dict[str, Any]],
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[TreatmentScenarioInput]:
        """Detect procedure keywords and numerical quotes from user text or active scenario."""
        c_lower = content.lower()

        # Check for quoted amount in text e.g. "quote is ₹3,00,000" or "quote is 280000"
        quote_match = re.search(r"(?:quote|cost|charge|bill|₹|rs\.?|\$)\s*(?:is|of|amount)?\s*(?:₹|rs\.?|\$)?\s*([0-9,]+(?:\.[0-9]{2})?)", c_lower)
        parsed_quote = None
        if quote_match:
            raw_num = quote_match.group(1).replace(",", "")
            try:
                val = float(raw_num)
                if val > 100:  # Avoid matching small numbers like 10%
                    parsed_quote = val
            except ValueError:
                pass

        # Identify treatment name
        treatment_name = None
        for name in [
            "total knee replacement", "knee replacement", "cataract surgery", "cataract",
            "angioplasty", "appendectomy", "hernia repair", "hernia",
            "maternity", "delivery", "c-section", "dialysis", "chemotherapy", "icu hospitalization",
        ]:
            if name in c_lower:
                treatment_name = name
                break

        if not treatment_name and existing_scenario:
            treatment_name = existing_scenario.get("treatment_name")

        if not treatment_name and history:
            for m in reversed(history):
                prev_text = (m.get("content") or "").lower()
                for name in [
                    "total knee replacement", "knee replacement", "cataract surgery", "cataract",
                    "angioplasty", "appendectomy", "hernia repair", "hernia",
                    "maternity", "delivery", "c-section", "dialysis", "chemotherapy", "icu hospitalization",
                ]:
                    if name in prev_text:
                        treatment_name = name
                        break
                if treatment_name:
                    break

        if treatment_name:
            effective_quote = parsed_quote or (existing_scenario.get("quoted_cost") if existing_scenario else None)
            return TreatmentScenarioInput(
                treatment_name=treatment_name,
                quoted_cost=effective_quote,
                diagnosis=(existing_scenario or {}).get("diagnosis"),
                hospital_name=(existing_scenario or {}).get("hospital_name"),
                city=(existing_scenario or {}).get("city"),
                hospital_type=(existing_scenario or {}).get("hospital_type"),
                inpatient_outpatient=(existing_scenario or {}).get("inpatient_outpatient", "inpatient"),
                length_of_stay_days=(existing_scenario or {}).get("length_of_stay_days"),
                patient_age=(existing_scenario or {}).get("patient_age"),
                non_payable_items=(existing_scenario or {}).get("non_payable_items", 0.0),
            )

        return None

    def _retrieve_policy_answer(
        self,
        policy: Policy,
        question: str,
        history: List[Dict[str, Any]],
        cost_estimate_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform grounded retrieval against indexed policy using ai RAG module."""
        try:
            import sys
            from pathlib import Path

            root_dir = Path(__file__).resolve().parents[3]
            if str(root_dir) not in sys.path:
                sys.path.insert(0, str(root_dir))

            from ai.retrieval.retriever import (
                answer_policy_question,
                get_default_vector_store,
                index_policy,
            )

            policy_identifier = str(policy.id)
            vstore = get_default_vector_store()

            # Ensure policy is indexed in vector store
            existing = vstore.get_chunks_by_document(policy_identifier, user_id=policy.user_id)
            if not existing:
                candidate_paths = []
                if policy.file_path:
                    candidate_paths.append(Path(policy.file_path))
                if policy.filename:
                    candidate_paths.append(Path(policy.filename))
                    sample_dir = root_dir / "ai" / "sample_policies"
                    candidate_paths.append(sample_dir / policy.filename)

                for cand in candidate_paths:
                    if cand.exists() and cand.is_file():
                        try:
                            index_policy(
                                pdf_path=cand,
                                policy_id=policy_identifier,
                                user_id=policy.user_id,
                                vector_store=vstore,
                            )
                            break
                        except Exception as e:
                            logger.warning(f"Failed to auto-index candidate PDF {cand}: {e}")

            res = answer_policy_question(
                policy_id=policy_identifier,
                question=question,
                user_id=policy.user_id,
                conversation_history=history,
            )

            # If not grounded or unstated, check fallback grounded answer
            if not res.get("grounded") and any(
                kw in question.lower()
                for kw in ["knee", "replacement", "room", "rent", "waiting", "document", "claim", "deductible"]
            ):
                return self._fallback_grounded_answer(policy, question, cost_estimate_data)

            # If cost estimate is available, augment the answer with financial clarity
            if cost_estimate_data and res.get("grounded"):
                est = cost_estimate_data
                curr = est.get("currency", "INR")
                res["answer"] += (
                    f"\n\n**Financial Treatment Estimate:**\n"
                    f"- Likely treatment expense: {curr} {est.get('estimated_total_cost', 0):,.2f}\n"
                    f"- Potentially eligible amount: {curr} {est.get('potentially_eligible_amount', 0):,.2f}\n"
                    f"- Approximate insurer contribution: {curr} {est.get('estimated_insurer_contribution', 0):,.2f}\n"
                    f"- Approximate patient responsibility: {curr} {est.get('estimated_patient_responsibility', 0):,.2f}\n"
                    f"*(Estimate — not insurer authorization. Final settlement is subject to claim adjudication).* "
                )
            return res
        except Exception as exc:
            logger.warning(f"Error in RAG retrieval for question '{question}': {exc}. Using deterministic synthesis.")
            return self._fallback_grounded_answer(policy, question, cost_estimate_data)

    def _fallback_grounded_answer(
        self,
        policy: Policy,
        question: str,
        cost_estimate_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Robust deterministic synthesis strictly grounded in the active policy's extracted rules and evidence."""
        q_lower = question.lower()
        doc_name = policy.filename or "uploaded policy"
        rules = policy.coverage_rules or []
        ev_refs = policy.evidence_references or []
        raw_meta = policy.raw_metadata or {}
        limits_meta = raw_meta.get("procedure_limits") or raw_meta.get("limits") or {}
        waiting_meta = raw_meta.get("waiting_periods") or {}

        # 1. Check procedure / treatment queries
        matching_rule = None
        for r in rules:
            proc = (r.procedure_name or r.rule_name or "").lower()
            if proc and (proc in q_lower or any(w in q_lower for w in proc.split() if len(w) > 3)):
                matching_rule = r
                break

        if matching_rule:
            p_name = matching_rule.procedure_name or matching_rule.rule_name
            status = matching_rule.coverage_status or "covered"
            parts = [f"{p_name} is {status} under active policy '{doc_name}'."]
            
            pct = matching_rule.coverage_percentage or matching_rule.coverage_limit_percentage_of_si
            cap = matching_rule.coverage_limit_amount
            if pct and cap:
                parts.append(f"Coverage is limited to {pct}% of sum insured (maximum ₹{cap:,.0f}).")
            elif cap:
                parts.append(f"Coverage is capped at maximum ₹{cap:,.0f}.")
            elif pct:
                parts.append(f"Coverage is up to {pct}% of sum insured.")

            if matching_rule.waiting_period:
                parts.append(f"A {matching_rule.waiting_period}-month waiting period applies.")
            elif matching_rule.conditions:
                parts.append(f"Conditions: {matching_rule.conditions}.")

            copay = matching_rule.copay_percentage if matching_rule.copay_percentage is not None else getattr(policy, "copay_percentage", None)
            if copay is not None:
                parts.append(f"Applicable co-pay: {copay}%.")

            if matching_rule.exclusions:
                parts.append(f"Exclusions: {matching_rule.exclusions}.")

            answer = " ".join(parts)
            if cost_estimate_data:
                est = cost_estimate_data
                curr = est.get("currency", "INR")
                answer += (
                    f"\n\n**Financial Treatment Estimate:**\n"
                    f"- Likely treatment expense: {curr} {est.get('estimated_total_cost', 0):,.2f}\n"
                    f"- Potentially eligible amount: {curr} {est.get('potentially_eligible_amount', 0):,.2f}\n"
                    f"- Approximate insurer contribution: {curr} {est.get('estimated_insurer_contribution', 0):,.2f}\n"
                    f"- Approximate patient responsibility: {curr} {est.get('estimated_patient_responsibility', 0):,.2f}\n"
                    f"*(Estimate — not insurer authorization).* "
                )

            citations = []
            if getattr(matching_rule, "evidence_references", None):
                for ev in matching_rule.evidence_references:
                    citations.append({
                        "document_name": doc_name,
                        "page_number": ev.page or 1,
                        "clause_title": ev.clause_section or "Contractual Rule",
                        "clause_reference": ev.clause_section or "Rule",
                        "verbatim_text": ev.extracted_text or matching_rule.rule_name,
                    })
            else:
                for ev in ev_refs:
                    if p_name.lower() in (ev.extracted_text or "").lower() or (ev.clause_section and p_name.lower() in ev.clause_section.lower()):
                        citations.append({
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Contractual Rule",
                            "clause_reference": ev.clause_section or "Rule",
                            "verbatim_text": ev.extracted_text,
                        })
                        break

            return {
                "answer": answer,
                "grounded": True,
                "confidence": "High",
                "citations": citations,
            }

        # 2. Check Waiting Periods
        if "waiting" in q_lower:
            wait_rules = [r for r in rules if r.category == "waiting_period" or r.waiting_period]
            if wait_rules or waiting_meta:
                wait_descriptions = []
                for wr in wait_rules:
                    wait_descriptions.append(f"{wr.rule_name}: {wr.waiting_period} months" if wr.waiting_period else wr.rule_name)
                for k, v in waiting_meta.items():
                    if isinstance(v, (int, float, str)):
                        wait_descriptions.append(f"{k.replace('_', ' ').title()}: {v}")
                
                citations = []
                for ev in ev_refs:
                    if "waiting" in (ev.extracted_text or "").lower() or "waiting" in (ev.clause_section or "").lower():
                        citations.append({
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Waiting Periods",
                            "clause_reference": ev.clause_section or "Clause",
                            "verbatim_text": ev.extracted_text,
                        })
                return {
                    "answer": f"Waiting periods established in '{doc_name}': " + "; ".join(wait_descriptions) + ".",
                    "grounded": True,
                    "confidence": "High",
                    "citations": citations[:3],
                }
            return {
                "answer": f"Waiting periods are Not Determined under the active policy ({doc_name}). The document does not establish specific waiting period terms.",
                "grounded": False,
                "confidence": "Low",
                "citations": [],
                "uncertainty_reason": "Waiting periods not established in policy document.",
            }

        # 3. Check Room Rent / ICU
        if "room" in q_lower or "rent" in q_lower or "icu" in q_lower:
            room_rules = [r for r in rules if "room" in (r.rule_name or "").lower() or "icu" in (r.rule_name or "").lower()]
            if room_rules or "room_rent_limit" in raw_meta or "icu_limit" in raw_meta:
                room_parts = []
                for rr in room_rules:
                    room_parts.append(f"{rr.rule_name}: {rr.conditions or rr.coverage_status}")
                if "room_rent_limit" in raw_meta:
                    room_parts.append(f"Room rent limit: {raw_meta['room_rent_limit']}")
                if "icu_limit" in raw_meta:
                    room_parts.append(f"ICU limit: {raw_meta['icu_limit']}")

                citations = []
                for ev in ev_refs:
                    if any(w in (ev.extracted_text or "").lower() for w in ["room", "rent", "icu"]):
                        citations.append({
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Room Rent Terms",
                            "clause_reference": ev.clause_section or "Clause",
                            "verbatim_text": ev.extracted_text,
                        })
                return {
                    "answer": f"Room and ICU eligibility under '{doc_name}': " + "; ".join(room_parts) + ".",
                    "grounded": True,
                    "confidence": "High",
                    "citations": citations[:2],
                }
            return {
                "answer": f"Room rent and ICU limits are Not Determined under the active policy ({doc_name}).",
                "grounded": False,
                "confidence": "Low",
                "citations": [],
                "uncertainty_reason": "Room rent limits not established in active policy.",
            }

        # 4. Check Deductible
        if "deductible" in q_lower:
            pol_deductible = getattr(policy, "deductible", None)
            if pol_deductible is not None:
                citations = []
                for ev in ev_refs:
                    if "deductible" in (ev.extracted_text or "").lower():
                        citations.append({
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Deductible Terms",
                            "clause_reference": ev.clause_section or "Clause",
                            "verbatim_text": ev.extracted_text,
                        })
                return {
                    "answer": f"Under active policy '{doc_name}', the annual deductible is ₹{pol_deductible:,.2f}.",
                    "grounded": True,
                    "confidence": "High",
                    "citations": citations[:2],
                }
            return {
                "answer": f"The active policy document ({doc_name}) does not establish an annual deductible. Deductible is Not Determined.",
                "grounded": False,
                "confidence": "Low",
                "citations": [],
                "uncertainty_reason": "Deductible not established in active policy document.",
            }

        # 5. Check Copay
        if "copay" in q_lower or "co-pay" in q_lower:
            pol_copay = getattr(policy, "copay_percentage", None)
            if pol_copay is not None:
                citations = []
                for ev in ev_refs:
                    if "copay" in (ev.extracted_text or "").lower() or "co-pay" in (ev.extracted_text or "").lower():
                        citations.append({
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Co-Payment Terms",
                            "clause_reference": ev.clause_section or "Clause",
                            "verbatim_text": ev.extracted_text,
                        })
                return {
                    "answer": f"Under active policy '{doc_name}', the applicable co-payment is {pol_copay}%.",
                    "grounded": True,
                    "confidence": "High",
                    "citations": citations[:2],
                }
            return {
                "answer": f"Co-payment is Not Determined under active policy ({doc_name}).",
                "grounded": False,
                "confidence": "Low",
                "citations": [],
                "uncertainty_reason": "Co-payment not established in active policy document.",
            }

        # 6. Check Claim / Documentation
        if "document" in q_lower or "claim" in q_lower:
            for ev in ev_refs:
                if any(w in (ev.extracted_text or "").lower() for w in ["claim", "document", "discharge", "reimbursement"]):
                    return {
                        "answer": f"Claim terms per '{doc_name}' ({ev.clause_section or 'Section'}, Page {ev.page or 1}): \"{ev.extracted_text.strip()}\"",
                        "grounded": True,
                        "confidence": "High",
                        "citations": [{
                            "document_name": doc_name,
                            "page_number": ev.page or 1,
                            "clause_title": ev.clause_section or "Claim Documentation",
                            "clause_reference": ev.clause_section or "Clause",
                            "verbatim_text": ev.extracted_text,
                        }],
                    }
            return {
                "answer": f"Claim documentation requirements are Not Determined under the active policy ({doc_name}).",
                "grounded": False,
                "confidence": "Low",
                "citations": [],
                "uncertainty_reason": "Claim documentation not found in extracted policy content.",
            }

        # 7. Default fallback: search evidence references for matching keywords
        tokens = [w for w in re.findall(r"\w+", q_lower) if len(w) > 3 and w not in {"what", "when", "where", "which", "does", "policy", "cover"}]
        for ev in ev_refs:
            ev_text = (ev.extracted_text or "").lower()
            if any(t in ev_text for t in tokens):
                return {
                    "answer": f"Under active policy '{doc_name}' ({ev.clause_section or 'Section'}, Page {ev.page or 1}): \"{ev.extracted_text.strip()}\"",
                    "grounded": True,
                    "confidence": "Medium",
                    "citations": [{
                        "document_name": doc_name,
                        "page_number": ev.page or 1,
                        "clause_title": ev.clause_section or "Policy Clause",
                        "clause_reference": ev.clause_section or "Clause",
                        "verbatim_text": ev.extracted_text,
                    }],
                }

        # Not determined for unstated terms
        return {
            "answer": f"The active policy document ({doc_name}) does not establish terms or clauses for '{question.strip()}'. Coverage details are Not Determined.",
            "grounded": False,
            "confidence": "Low",
            "citations": [],
            "uncertainty_reason": f"Information not established in active policy ({doc_name}).",
        }

    def format_conversation_response(
        self, conv: PolicyConversation
    ) -> ConversationResponse:
        """Convert PolicyConversation model to clean Pydantic response."""
        messages: List[ConversationMessageResponse] = []
        for m in (conv.messages or []):
            evidence_list = [
                ConversationEvidenceResponse(
                    id=e.id,
                    document_source=e.document_source,
                    page=e.page,
                    clause_section=e.clause_section,
                    extracted_text=e.extracted_text,
                    interpretation=e.interpretation,
                    confidence=e.confidence,
                )
                for e in (m.evidence_references or [])
            ]
            messages.append(
                ConversationMessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    confidence=m.confidence,
                    is_grounded=m.is_grounded,
                    uncertainty_reason=m.uncertainty_reason,
                    missing_information=m.missing_information,
                    treatment_scenario=m.treatment_scenario,
                    cost_estimate=m.cost_estimate,
                    evidence_references=evidence_list,
                    created_at=m.created_at,
                )
            )

        return ConversationResponse(
            id=conv.id,
            policy_id=conv.policy_id,
            title=conv.title,
            context_metadata=conv.context_metadata,
            messages=messages,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )


# Default singleton instance
default_conversation_service = ConversationService()


def get_conversation_service() -> ConversationService:
    return default_conversation_service
