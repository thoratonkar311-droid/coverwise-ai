"""CLI entry point for the CoverWise AI AI/ML module.

Provides diagnostic and operational commands to:
- Inspect active runtime configuration
- Execute PDF text extraction on sample or target policies
- Verify schemas and system readiness
- Test Ollama LLM connectivity
"""

import argparse
import json
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.config import get_settings, setup_logging
from ai.extraction.pdf_extractor import PDFExtractor, ExtractionError
from ai.llm.client import OllamaClient
from ai.schemas.policy import PolicyAnalysis

logger = setup_logging()


def cmd_info(args: argparse.Namespace) -> int:
    """Print active configuration and environment parameters."""
    settings = get_settings()
    print("=" * 60)
    print(" CoverWise AI - AI/ML Module Configuration")
    print("=" * 60)
    print(f" Environment         : {settings.environment}")
    print(f" Log Level           : {settings.log_level}")
    print(f" LLM Base URL        : {settings.ollama_base_url}")
    print(f" LLM Model           : {settings.llm_model}")
    print(f" Embedding Model     : {settings.embedding_model}")
    print(f" Vector Table        : {settings.vector_table_name}")
    print(f" Vector Dimension    : {settings.vector_dimension}")
    print(f" Database Configured : {bool(settings.database_url)}")
    print(f" OCR Enabled         : {settings.enable_ocr} (Engine: {settings.ocr_engine})")
    print("=" * 60)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Execute PDF text extraction preserving page evidence."""
    pdf_path = Path(args.path)
    if not pdf_path.exists():
        logger.error("Specified PDF file does not exist: %s", pdf_path)
        return 1

    extractor = PDFExtractor(clean_text=not args.raw)
    try:
        doc = extractor.extract(pdf_path)
    except ExtractionError as exc:
        logger.error("Extraction failed: %s", exc)
        return 1

    print("\n" + "=" * 60)
    print(f" Successfully Extracted: {doc.filename}")
    print("=" * 60)
    print(f" Document ID   : {doc.document_id}")
    print(f" Total Pages   : {doc.total_pages}")
    print(f" File Size     : {doc.file_size_bytes} bytes")
    print(f" Title Metadata: {doc.metadata.get('title') or 'None'}")
    print("-" * 60)

    for page in doc.pages:
        preview = page.text[:120].replace("\n", " ") + ("..." if len(page.text) > 120 else "")
        print(f" Page {page.page_number:02d} | Words: {page.word_count:4d} | Chars: {page.char_count:5d} | Preview: {preview}")

    print("=" * 60)
    if args.json:
        print(doc.model_dump_json(indent=2))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Check Ollama service connectivity."""
    settings = get_settings()
    client = OllamaClient()
    print(f"Connecting to Ollama at {settings.ollama_base_url}...")
    is_up = client.check_health()
    if not is_up:
        print(f"[-] Ollama server is NOT reachable at {settings.ollama_base_url}.")
        print("    Ensure Ollama is installed and running (`ollama serve`).")
        return 1

    print("[+] Ollama server is ONLINE.")
    try:
        models = client.list_models()
        print(f"[+] Available models ({len(models)}): {', '.join(models) if models else 'None pulled yet'}")
        if settings.llm_model in models:
            print(f"[+] Target model '{settings.llm_model}' is available.")
        else:
            print(f"[!] Target model '{settings.llm_model}' is not yet pulled.")
            print(f"    Run: ollama pull {settings.llm_model}")
    except Exception as exc:
        print(f"[!] Could not list models: {exc}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify that schemas enforce null for unknown policy fields and extractor works."""
    print("Running CoverWise AI diagnostic verification...")
    # 1. Verify schema nullability
    analysis = PolicyAnalysis()
    assert analysis.deductibles.individual_in_network is None
    assert analysis.copays.primary_care is None
    assert analysis.coinsurance.in_network_percentage is None
    assert analysis.metadata.insurer_name is None
    print("[+] Schemas strictly default unknown policy fields to None/null.")

    # 2. Verify PDF extraction on sample policy
    sample_pdf = Path(__file__).parent / "sample_policies" / "sample_health_policy.pdf"
    if sample_pdf.exists():
        extractor = PDFExtractor()
        doc = extractor.extract(sample_pdf)
        assert doc.total_pages == 4
        assert doc.pages[0].page_number == 1
        assert "APEX HEALTH PLAN" in doc.pages[0].text
        print(f"[+] Sample policy extracted successfully ({doc.total_pages} pages, evidence preserved).")
    else:
        print("[!] Sample policy PDF not found at default location.")

    print("[+] System diagnostic check passed.")
    return 0


def cmd_extract_policy(args: argparse.Namespace) -> int:
    """Extract structured policy data with Pydantic validation (Phase 2A)."""
    from ai.extraction.policy_extractor import extract_policy

    pdf_path = Path(args.path)
    if not pdf_path.exists():
        logger.error("Specified PDF file does not exist: %s", pdf_path)
        return 1

    try:
        policy = extract_policy(pdf_path)
    except Exception as exc:
        logger.error("Policy extraction failed: %s", exc)
        return 1

    print("\n" + "=" * 65)
    print(f" Structured Policy Extraction: {pdf_path.name}")
    print("=" * 65)
    print(f" Insurer Name           : {policy.metadata.insurer_name}")
    print(f" Policy ID              : {policy.metadata.policy_id}")
    print(f" Plan Name              : {policy.metadata.policy_name}")
    print(f" Effective Date         : {policy.metadata.effective_date}")
    print(f" Currency               : {policy.currency}")
    print("-" * 65)
    print(f" In-Network Deductible  : ${policy.deductibles.individual_in_network:,.2f}" if policy.deductibles.individual_in_network is not None else " In-Network Deductible  : None")
    print(f" Out-of-Network Ded.    : ${policy.deductibles.individual_out_of_network:,.2f}" if policy.deductibles.individual_out_of_network is not None else " Out-of-Network Ded.    : None")
    print(f" In-Network Coinsurance : {policy.coinsurance.in_network_percentage}%" if policy.coinsurance.in_network_percentage is not None else " In-Network Coinsurance : None")
    print(f" Out-of-Network Coins.  : {policy.coinsurance.out_of_network_percentage}%" if policy.coinsurance.out_of_network_percentage is not None else " Out-of-Network Coins.  : None")
    print(f" In-Network OOP Maximum : ${policy.out_of_pocket_max.individual_in_network:,.2f}" if policy.out_of_pocket_max.individual_in_network is not None else " In-Network OOP Maximum : None")
    print("-" * 65)
    print(f" Primary Care Copay     : ${policy.copays.primary_care:,.2f}" if policy.copays.primary_care is not None else " Primary Care Copay     : None")
    print(f" Specialist Copay       : ${policy.copays.specialist:,.2f}" if policy.copays.specialist is not None else " Specialist Copay       : None")
    print(f" Urgent Care Copay      : ${policy.copays.urgent_care:,.2f}" if policy.copays.urgent_care is not None else " Urgent Care Copay      : None")
    print(f" Emergency Room Copay   : ${policy.copays.emergency_room:,.2f}" if policy.copays.emergency_room is not None else " Emergency Room Copay   : None")
    print("-" * 65)
    print(f" Prior Authorizations   : {len(policy.prior_authorizations)} rule(s)")
    for pa in policy.prior_authorizations:
        print(f"   • {pa.service_or_procedure} [{pa.timeline_requirement}]")
    print(f" Exclusions Extracted   : {len(policy.exclusions)} item(s)")
    for ex in policy.exclusions[:3]:
        print(f"   • {ex}")
    if len(policy.exclusions) > 3:
        print(f"     ... (+{len(policy.exclusions) - 3} more)")
    print(f" Waiting Periods        : {len(policy.waiting_periods)} stated (None assumed)")
    print(f" Conflicting Evidence   : {len(policy.conflicting_evidence)} item(s)")
    print("=" * 65)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
        print(f"[+] Saved structured policy JSON to {out_p}")

    if args.json:
        print(policy.model_dump_json(indent=2))

    return 0


def cmd_index(args: argparse.Namespace) -> int:
    """Index a policy document into the vector store."""
    from ai.retrieval.retriever import index_policy

    pdf_path = Path(args.path)
    if not pdf_path.exists():
        logger.error("Specified PDF file does not exist: %s", pdf_path)
        return 1

    try:
        count = index_policy(pdf_path, policy_id=args.policy_id)
        pid = args.policy_id or pdf_path.stem
        print("\n" + "=" * 60)
        print(" Policy Indexing Completed")
        print("=" * 60)
        print(f" PDF Source        : {pdf_path.name}")
        print(f" Policy Identifier : {pid}")
        print(f" Indexed Chunks    : {count}")
        print("=" * 60)
        return 0
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        return 1


def cmd_retrieve(args: argparse.Namespace) -> int:
    """Retrieve relevant clauses using hybrid semantic-plus-keyword search."""
    from ai.retrieval.retriever import retrieve_clauses

    results = retrieve_clauses(policy_id=args.policy_id, query=args.query, top_k=args.top_k)

    if args.json:
        out = [
            {
                "chunk_id": r.chunk.chunk_id,
                "document_id": r.chunk.document_id,
                "page_number": r.chunk.page_number,
                "section_title": r.chunk.section_title,
                "similarity_score": round(r.similarity_score, 4),
                "text": r.chunk.text,
            }
            for r in results
        ]
        print(json.dumps(out, indent=2))
        return 0

    print("\n" + "=" * 65)
    print(f" Hybrid Retrieval Results for '{args.policy_id}'")
    print(f" Query: \"{args.query}\" | Matches: {len(results)}")
    print("=" * 65)

    if not results:
        print(" No matching policy clauses found.")
        print("=" * 65)
        return 0

    for i, item in enumerate(results, 1):
        c = item.chunk
        preview = c.text.strip().replace("\n", " ")
        if len(preview) > 160:
            preview = preview[:160] + "..."
        print(f" [{i}] Score: {item.similarity_score:.4f} | Page {c.page_number:02d} | Section: {c.section_title or 'N/A'}")
        print(f"     ID: {c.chunk_id}")
        print(f"     Quote: \"{preview}\"")
        print("-" * 65)

    print("=" * 65)
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    """Answer an insurance question strictly grounded in policy text and citations."""
    from ai.retrieval.retriever import answer_policy_question

    res = answer_policy_question(policy_id=args.policy_id, question=args.question)

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("\n" + "=" * 65)
    print(" CoverWise AI Grounded Policy Q&A")
    print("=" * 65)
    print(f" Policy ID   : {res['policy_id']}")
    print(f" Question    : {res['question']}")
    print(f" Grounded    : {'[+] Yes (Evidence-backed)' if res['grounded'] else '[-] No (Unstated/Missing)'}")
    print(f" Clauses Used: {res['retrieved_clauses_count']}")
    print("-" * 65)
    print(f" Answer:\n {res['answer']}")
    print("-" * 65)
    if res.get("citations"):
        print(" Verbatim Citations & Evidence:")
        for c in res["citations"]:
            print(f"   • Page {c['page_number']} [{c.get('clause_title') or 'Clause'}]: \"{c['verbatim_text']}\"")
    else:
        print(" Citations: None (query rejected to avoid hallucination)")
    print("=" * 65)
    return 0


def main() -> int:
    """Parse arguments and route to appropriate command."""
    parser = argparse.ArgumentParser(
        prog="coverwise-ai",
        description="CoverWise AI - Policy-to-Patient Intelligence Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # info command
    subparsers.add_parser("info", help="Show active configuration and environment")

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Extract raw text and evidence from PDF")
    extract_parser.add_argument("path", help="Path to policy PDF file")
    extract_parser.add_argument("--raw", action="store_true", help="Preserve unnormalized raw text")
    extract_parser.add_argument("--json", action="store_true", help="Dump ExtractedDocument JSON")

    # extract-policy command (Phase 2A)
    p_extract_parser = subparsers.add_parser("extract-policy", help="Extract structured policy intelligence with Pydantic validation")
    p_extract_parser.add_argument("path", help="Path to policy PDF file")
    p_extract_parser.add_argument("--output", "-o", help="Path to save validated JSON output")
    p_extract_parser.add_argument("--json", action="store_true", help="Print JSON output to stdout")

    # index command (Phase 2B)
    index_parser = subparsers.add_parser("index", help="Index policy PDF into vector store")
    index_parser.add_argument("path", help="Path to policy PDF file")
    index_parser.add_argument("--policy-id", help="Override document/policy ID")

    # retrieve command (Phase 2B)
    ret_parser = subparsers.add_parser("retrieve", help="Retrieve policy clauses using hybrid search")
    ret_parser.add_argument("policy_id", help="Target policy ID")
    ret_parser.add_argument("query", help="Treatment, coverage term, or search query")
    ret_parser.add_argument("--top-k", type=int, default=5, help="Maximum number of clauses to retrieve (default: 5)")
    ret_parser.add_argument("--json", action="store_true", help="Print JSON output to stdout")

    # ask command (Phase 2B)
    ask_parser = subparsers.add_parser("ask", help="Ask grounded question against an indexed policy")
    ask_parser.add_argument("policy_id", help="Target policy ID")
    ask_parser.add_argument("question", help="Question regarding policy coverage or conditions")
    ask_parser.add_argument("--json", action="store_true", help="Print JSON output to stdout")

    # health command
    subparsers.add_parser("health", help="Check Ollama connection and model status")

    # verify command
    subparsers.add_parser("verify", help="Run quick diagnostic self-test")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "info": cmd_info,
        "extract": cmd_extract,
        "extract-policy": cmd_extract_policy,
        "index": cmd_index,
        "retrieve": cmd_retrieve,
        "ask": cmd_ask,
        "health": cmd_health,
        "verify": cmd_verify,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
