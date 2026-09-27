# CoverWise AI — AI/ML Module (`ai/`)

> **Component**: Policy-to-Patient Insurance Coverage & Treatment Cost Intelligence  
> **Role**: Member 3 — AI/ML Architecture & Engineering  
> **Python Version**: Python 3.11+  
> **Frameworks**: Pydantic v2, PyMuPDF, Ollama (Qwen 2.5), Sentence Transformers (BGE-M3), pytest

---

## 1. Overview & Architecture

The `ai/` package provides the intelligence backbone for CoverWise AI. Its role is to ingest complex health insurance policy documents (Summary of Benefits and Coverage - SBC), extract clauses while strictly preserving page-level auditability, interface with vector stores (PostgreSQL + pgvector), and provide structured, grounded outputs to the FastAPI backend without hallucinations.

```
                           +-------------------------------------+
                           | Policy PDF Document (e.g. SBC/Plan) |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |   ai.extraction.PDFExtractor        |
                           |   (PyMuPDF / fitz, 1-indexed pages) |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           | ExtractedDocument & ExtractedPage   |
                           | (Character offsets, metadata hash)  |
                           +-------------------------------------+
                                              |
                  +---------------------------+---------------------------+
                  |                                                       |
                  v                                                       v
+-----------------------------------+               +-----------------------------------+
| ai.retrieval (Interfaces)         |               | ai.schemas (Pydantic v2 Models)   |
| - PolicyChunker                   |               | - Deductibles (defaults to None)  |
| - EmbeddingModel (BGE-M3 1024-dim)|               | - Copays (defaults to None)       |
| - PgVectorStore / InMemoryStore   |               | - Coinsurance (defaults to None)  |
| - PolicyRetriever                 |               | - EvidenceSpan (page + citations) |
+-----------------------------------+               +-----------------------------------+
                  |                                                       |
                  +---------------------------+---------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           | ai.llm.OllamaClient (Qwen 2.5 7B)   |
                           | & Deterministic Calculation Models  |
                           +-------------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           | TreatmentCostEstimate               |
                           | - Insurer vs. Patient Breakdown     |
                           | - Supporting Policy Clauses         |
                           | - Caveats & Prior Auth Warnings     |
                           +-------------------------------------+
```

---

## 2. Directory Structure

```
ai/
├── __init__.py                # Package initialization and version definition
├── config.py                  # Pydantic Settings v2 configuration & structured logging
├── main.py                    # CLI entry point (info, extract, health, verify)
├── requirements.txt           # Core, test, and deferred dependencies
├── .env.example               # Environment variables template
├── pytest.ini                 # Pytest configuration
├── README.md                  # Comprehensive AI module documentation
│
├── extraction/                # Document text extraction layer
│   ├── __init__.py
│   ├── pdf_extractor.py       # Working PyMuPDF extractor with page preservation
│   └── ocr_extractor.py       # Optional PaddleOCR interface with graceful degradation
│
├── retrieval/                 # Retrieval & Vector Database Interfaces
│   ├── __init__.py
│   ├── chunking.py            # PolicyChunk models preserving page & char offsets
│   ├── embeddings.py          # EmbeddingModelInterface for BGE-M3 (1024-dim)
│   ├── retriever.py           # PolicyRetrieverInterface contract
│   └── vector_store.py        # PostgreSQL/pgvector interface & InMemoryVectorStore
│
├── schemas/                   # Validated Pydantic v2 Domain Models
│   ├── __init__.py
│   ├── evidence.py            # EvidenceSpan, Citation, ExtractedPage, ExtractedDocument
│   ├── policy.py              # Deductibles, Copays, Coinsurance, BenefitItems (null defaults)
│   └── cost.py                # TreatmentCostEstimate & CostBreakdownItem
│
├── llm/                       # LLM Orchestration
│   ├── __init__.py
│   └── client.py              # OllamaClient (health checks, JSON mode, Qwen support)
│
├── prompts/                   # Extraction & Reasoning Prompts
│   ├── __init__.py
│   └── templates.py           # Few-shot prompts enforcing JSON & verbatim citations
│
├── sample_policies/           # Synthetic policy fixtures (NO real patient data)
│   ├── README.md              # Compliance and synthetic fixture documentation
│   ├── generate_sample_pdf.py # Deterministic PDF generator script
│   └── sample_health_policy.pdf # 4-page test fixture with benefits & exclusions
│
└── tests/                     # Automated Test Suite (pytest)
    ├── __init__.py
    ├── conftest.py            # Pytest fixtures and factory functions
    ├── test_config.py         # Config validation and env override tests
    ├── test_schemas.py        # Schema nullability, validation, and serialization tests
    ├── test_pdf_extractor.py  # PyMuPDF page preservation and error handling tests
    ├── test_vector_store_interface.py # pgvector DDL and InMemory store tests
    └── test_llm_client.py     # Ollama client configuration and error handling tests
```

---

## 3. Key Design Decisions & Compliance Rules

1. **Unknown Policy Fields Default to `None` (Null in JSON)**:
   - In healthcare insurance modeling, hallucinating a `$0` copay when unspecified is a severe liability. All numerical fields (deductibles, copays, coinsurance percentages) strictly default to `None`.
2. **Strict Evidence & Page Traceability**:
   - Every benefit, clause, and cost line item binds to an `EvidenceSpan` with 1-indexed `page_number`, text snippet, and optional character start/end coordinates.
3. **Optional OCR Architecture**:
   - `PaddleOCRExtractor` is decoupled and strictly optional (`ENABLE_OCR=false` by default). The system will not crash if heavy OCR dependencies are omitted.
4. **PostgreSQL / pgvector Integration Interface**:
   - `PgVectorStore` generates standard PostgreSQL DDL schemas utilizing the `vector(1024)` data type and HNSW cosine distance indexing (`vector_cosine_ops`), accompanied by an `InMemoryVectorStore` for isolated automated unit tests.
5. **Data Protection & Privacy**:
   - No real Protected Health Information (PHI) or proprietary insurer contracts are stored or committed. All sample policies are programmatically generated synthetic fixtures.

---

## 4. Windows PowerShell Setup Instructions

Follow these exact steps in Windows PowerShell to set up and verify the environment:

### Step 1: Open PowerShell and Navigate to the Repository Root
```powershell
cd Desktop\coverwise-ai
# Or: cd <path-to-coverwise-ai>
```

### Step 2: Create a Python 3.11+ Virtual Environment
Using Python directly:
```powershell
python -m venv .venv
```
*(Or using `uv` if installed)*:
```powershell
uv venv .venv --python 3.11
```

### Step 3: Activate the Virtual Environment
If execution policy prevents script activation:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
*(Verify active Python)*:
```powershell
python --version
```

### Step 4: Install Dependencies
```powershell
pip install -r ai/requirements.txt
```

### Step 5: Configure Environment Variables
Copy the template environment file:
```powershell
Copy-Item ai\.env.example ai\.env
```

### Step 6: Run the Test Suite
Set `PYTHONPATH` to the repository root and run `pytest`:
```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest ai/tests -v
```

### Step 7: Execute CLI Commands
Inspect configuration:
```powershell
python ai/main.py info
```

Extract raw PDF text (preserves page numbers):
```powershell
python ai/main.py extract ai/sample_policies/sample_health_policy.pdf
```

Extract structured policy intelligence (Phase 2A for Member 2):
```powershell
python ai/main.py extract-policy ai/sample_policies/sample_health_policy.pdf -o ai/sample_policies/extracted_policy.json
```

Index policy PDF into vector store (Phase 2B RAG):
```powershell
python ai/main.py index ai/sample_policies/sample_health_policy.pdf --policy-id APEX-2024
```

Retrieve policy clauses with hybrid semantic-plus-keyword search:
```powershell
python ai/main.py retrieve APEX-2024 "deductible" --top-k 5
```

Ask grounded insurance questions against indexed policy:
```powershell
python ai/main.py ask APEX-2024 "What is the individual in-network deductible?"
python ai/main.py ask APEX-2024 "What is the in-network coinsurance?"
python ai/main.py ask APEX-2024 "Is cosmetic surgery covered?"
python ai/main.py ask APEX-2024 "What are the prior authorization requirements for elective surgery?"
python ai/main.py ask APEX-2024 "Is cryo-ablation for migraine covered?"
```

Run diagnostic system verification:
```powershell
python ai/main.py verify
```

Check local Ollama server status and model availability:
```powershell
python ai/main.py health
```

---

## 5. Implementation & Quality Benchmark Status (Member 3)

- [x] **Live LLM Inference & Verification**: Verified local Ollama server running with `qwen3:4b` (`http://localhost:11434`), supporting direct model inference, JSON mode, reasoning trace extraction, and high-performance deterministic fallback.
- [x] **Clause-Aware PDF Chunking**: `ClauseAwareChunker` preserves 1-indexed page boundaries, section headings, and character coordinates with stable deterministic chunk IDs (`{doc_id}_p{page}_c{index}`).
- [x] **Dense Embeddings (1024-dim)**: `BGEM3EmbeddingModel` lazy-loads `BAAI/bge-m3` using `sentence-transformers`, strictly producing 1024-dimensional normalized vector representations, with deterministic 1024-dim semantic embedder fallback.
- [x] **In-Memory & PgVector Storage**: `InMemoryVectorStore` with cosine similarity and disk persistence cache (`.vector_cache.json`) for seamless CLI usage, plus `PgVectorStore` adapter generating production PostgreSQL DDL and HNSW indices.
- [x] **Multi-Currency Support**: Full automated extraction and validation across `USD` ($), `INR` (₹), and `EUR` (€) policies.
- [x] **Cross-User Tenant Isolation**: Vector and hybrid queries enforce strict multi-tenant filtering (`user_id` and `document_id`), strictly preventing cross-user clause leakage.
- [x] **Duplicate Indexing Prevention**: SHA-256 document checksums skip redundant embedding generation for previously indexed policies.
- [x] **Safe PDF Upload Validation**: Multi-layer upload security checks for path traversal (`..`, null bytes), file size limit (25MB), `.pdf` extension, magic bytes (`%PDF-`), and PyMuPDF structural integrity.
- [x] **Sensitive Data & PHI Redaction**: `SensitiveDataFilter` and `mask_sensitive_phi` scrub SSNs, MRNs, credit cards, phones, emails, and bearer tokens from all logs.
- [x] **Policy Deletion**: `delete_policy` interface purges document chunks from vector index.
- [x] **Strictly Grounded Q&A**: `answer_policy_question` enforces zero hallucination—refuses unknown treatments without guessing, and mandates verbatim quotations and 1-indexed page citations.
- [x] **Quality Benchmark Metrics (Measured on 24 Domain Questions & 4 Policies)**:
  - Exact Numeric Accuracy: **100.0%** (Deductibles, Copays, Coinsurance, OOP Max)
  - Currency Detection: **100.0%** (USD, INR, EUR)
  - Top-3 Retrieval Recall: **100.0%** (21/21 grounded questions)
  - Top-5 Retrieval Recall: **100.0%** (21/21 grounded questions)
  - Ungrounded Refusal Accuracy: **100.0%** (3/3 unknown procedures refused)
  - Live `qwen3:4b` JSON Validity: **100.0%**
  - Live Model Latency: **~5.10s** | Deterministic Synthesizer Latency: **~4.0ms**
  - OCR Status: Optional PaddleOCR uninstalled; graceful degradation verified.
- [x] **Automated Test Suite**: **68 tests passing** (48 unit + 11 integration contract + 9 quality benchmark tests, 0 failed).
