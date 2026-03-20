# Atticus — Legal Intelligence Platform

> "Atticus Finch won his cases by reading every document carefully and finding the truth others missed. That's exactly what this platform does for your firm."

---

## The Idea

Law firms are drowning in documents. A single case can have thousands of pages — contracts, court filings, correspondence, witness statements, expert reports. Junior associates spend a significant portion of their billable hours not practicing law, just finding information inside documents they already have.

Consumer AI tools like ChatGPT are legally forbidden — bar association ethics rules explicitly prohibit uploading client documents to third-party servers. Enterprise tools like Harvey AI and Thomson Reuters CoCounsel cost thousands per month per user, pricing out mid-size firms. Generic RAG systems have the wrong failure modes for legal work — retrieving from the wrong client's contract is not a bad user experience, it is potential malpractice.

Atticus is a private, self-hosted legal intelligence platform. It ingests a law firm's documents, understands them with legal domain awareness, and lets lawyers query their own case documents in plain English — receiving direct, cited, case-scoped answers in seconds. Everything runs on the firm's own infrastructure. Client documents never leave the firm's servers.

---

## Core Features

- Two portals: Admin (upload, manage, assign) and Lawyer (query, chat)
- Role-based access control at two levels: role (admin/lawyer/paralegal) + case ownership (assigned_lawyers per case)
- Case management: documents belong to cases, active and closed cases
- Multi-turn conversation with session memory
- Answers with exact citations: document name, version, page, highlighted paragraph
- Document versioning with full audit trail
- Async ingestion: admin gets 202 Accepted immediately, processing happens in background
- Semantic cache with context-aware expansion: similar queries return instantly
- Full observability: every query traced with cost, latency, chunks used, scores
- Dual processing for ambiguous documents: low confidence classification processed with both chunkers, flagged for awareness

---

## Supported File Types

| File Type | Parser | Legal Use |
|-----------|--------|-----------|
| PDF (native only) | pdfplumber | Contracts, court filings, expert reports |
| DOCX | python-docx | Legal briefs, draft contracts, memos |
| EML | Python email stdlib | Client correspondence, case discussions |
| TXT | Plain read | Notes, summaries, quick observations |

No OCR support. Scanned PDFs are flagged as needs_review. No spreadsheet support — legal firms deal in narrative documents, not tabular data.

---

## Two-Phase Detection

Every uploaded file goes through two completely independent detection phases. They answer different questions and are not interchangeable.

### Phase 1 — File Type Detection
Determined by file extension. Decides which parser to use.

```
.pdf  → pdfplumber       → raw text
.docx → python-docx      → raw text (heading structure preserved)
.eml  → email stdlib     → raw text per reply + metadata
.txt  → plain read       → raw text

Output: raw text string
All files become plain text after this step.
```

### Phase 2 — Document Type Detection
Determined by content of the extracted text. Decides which chunking strategy to use.

Uses confidence scoring across multiple signals combined into a score per type:

```python
def detect_document_type(text, filename, file_type, page_count):

    # EML files are always emails
    if file_type == "eml":
        return "email", high_confidence

    # TXT files are always notes
    if file_type == "txt":
        return "note", high_confidence

    scores = { "contract": 0, "legal_brief": 0, "email": 0, "note": 0 }
    first_500 = text[:500].lower()

    # Signal 1 — filename
    if any(w in filename.lower() for w in ["nda", "agreement", "contract", "retainer"]):
        scores["contract"] += 3
    if any(w in filename.lower() for w in ["motion", "filing", "brief", "complaint"]):
        scores["legal_brief"] += 3
    if any(w in filename.lower() for w in ["note", "summary", "memo"]):
        scores["note"] += 2

    # Signal 2 — email headers
    if all(w in first_500 for w in ["from:", "to:", "subject:"]):
        scores["email"] += 4

    # Signal 3 — contract vocabulary
    contract_keywords = ["agreement", "clause", "termination", "party",
                         "liability", "whereas", "hereinafter", "indemnify"]
    scores["contract"] += sum(2 for w in contract_keywords if w in first_500)

    # Signal 4 — legal brief vocabulary
    brief_keywords = ["plaintiff", "defendant", "court", "motion",
                      "judgment", "jurisdiction", "hereby", "petition"]
    scores["legal_brief"] += sum(2 for w in brief_keywords if w in first_500)

    # Signal 5 — structural signals
    if page_count < 2:
        scores["note"] += 2

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    second_score = sorted(scores.values(), reverse=True)[1]
    confidence_gap = best_score - second_score

    return best_type, confidence_gap
```

### Low Confidence Handling

Low confidence does not mean stop processing. It means process with both chunkers and flag the result.

```python
CONFIDENCE_THRESHOLD = 3

if confidence_gap < CONFIDENCE_THRESHOLD:
    # dual processing — defer ambiguity to reranker
    contract_chunks = contract_chunker(text)
    paragraph_chunks = paragraph_chunker(text)
    all_chunks = mark_as_low_confidence(contract_chunks + paragraph_chunks)
    # reranker will decide which chunks are actually relevant at query time
else:
    chunks = chunker_for(best_type)(text)
```

Exception: for contracts specifically, if confidence is very low (gap < 1), flag as needs_review and notify admin. A contract chunked incorrectly has higher legal risk than a delayed ingestion.

---

## Document Types & Chunking Strategy

Chunking is one of the most consequential decisions in the pipeline. Bad chunking produces bad retrieval regardless of how sophisticated everything downstream is. Atticus uses adaptive chunking — the strategy depends entirely on document type, not file type.

The same PDF can be a contract, a brief, an email printout, or a note. Each gets chunked differently. Chunking complexity is fully isolated in the ingestion pipeline — once chunks are stored, the retrieval pipeline treats every chunk identically.

### Contract — Section-Based Chunking

Contracts are organized by clauses and articles. Each clause is a self-contained legal unit of meaning. Splitting mid-clause destroys legal meaning and makes retrieval unreliable.

```
Article 1 — Definitions        → chunk 1
Article 2 — Payment Terms       → chunk 2
Article 3 — Termination         → chunk 3
Article 4 — Liability           → chunk 4

If a clause exceeds 700 tokens, split with overlap:
  Article 3.1 → chunk 3a
  Article 3.2 → chunk 3b

Target: 300-700 tokens
Rule: meaning > token count
Overlap: 50 tokens on sub-chunks only
Small 20-30 token overlap between clauses allowed
when a clause references the previous one
```

### Legal Brief — Paragraph-Based Chunking

Briefs are narrative arguments without clean clause structure. Paragraph boundaries are the natural semantic unit. Small paragraphs are grouped until hitting the size limit.

```
Target: 300-400 tokens (stricter than contracts — dense arguments)
Overlap: 50 tokens
Group small paragraphs together until size limit
```

### Email — One Chunk Per Reply

Each reply in a thread is a self-contained message with its own intent, sender, and date. Merging replies destroys conversational context and temporal reasoning.

```
Each reply → one chunk
Hard cap: 500 tokens per reply
If reply > 500 tokens → split into sub-chunks, same metadata preserved
No overlap between replies — each is independent
```

Attachments inside EML files are extracted separately and processed as their own document through the full pipeline. A contract attached to an email is chunked as a contract.

### Note — Single Chunk

Notes, meeting summaries, and short observations are self-contained. The whole document is one chunk. If a note exceeds 500 tokens, fall back to paragraph-based chunking.

### Summary Table

| Document Type | Strategy | Target Size | Overlap | source_type |
|---------------|----------|-------------|---------|-------------|
| Contract | Section/clause boundaries | 300-700 tokens | 20-50 tokens | contract_clause |
| Legal Brief | Paragraph boundaries | 300-400 tokens | 50 tokens | paragraph |
| Email | One chunk per reply (hard cap 500t) | Natural size | None | email_reply |
| Note | Single chunk | Full document | None | note |

### Contextual Prefix

Every chunk gets a prefix before embedding. The embedding captures both the semantic content and where the chunk sits in the document. This dramatically improves retrieval accuracy when similar clauses appear across multiple contracts in the same case.

```
Contract chunk:
"Document Type: Contract | Document: NDA Acme Corp v2 | Case: Acme v Smith | Section: Termination | Clause: 3.2
Either party may terminate this agreement upon 30 days written notice..."

Legal brief chunk:
"Document Type: Legal Brief | Document: Motion to Dismiss | Case: Acme v Smith | Section: Argument
The plaintiff fails to establish jurisdiction because..."

Email chunk:
"Document Type: Email | Case: Acme v Smith | From: client@acme.com | Date: Jan 3 2024 | Subject: Re: Settlement
I wanted to discuss the settlement terms you proposed..."

Note chunk:
"Document Type: Note | Document: Meeting Notes Jan 2024 | Case: Acme v Smith
Discussed strategy with client. Key points: timeline is aggressive..."
```

---

## Three Core Pipelines

### Pipeline 1 — Ingestion

```
Admin uploads file(s) — one or many simultaneously
        │
        ↓
FastAPI
  • Validates file type (.pdf, .docx, .eml, .txt only)
  • Generates file_id (UUID4)
  • Saves document metadata to PostgreSQL (status: "processing")
  • Uploads raw file to AWS S3
  • Fires Celery task per file — one independent task per file
  • Returns 202 Accepted immediately — admin never waits
        │
        ↓ (Celery background worker)
━━━━━━━━━━━━━━━━━━
PHASE 1 — FILE TYPE DETECTION + PARSING
  .pdf  → pdfplumber  → raw text
  .docx → python-docx → raw text (heading structure preserved)
  .eml  → email lib   → raw text per reply + metadata (from/to/subject/date)
  .txt  → plain read  → raw text

  Output: raw text string — all files become plain text here
━━━━━━━━━━━━━━━━━━
        │
        ↓
PHASE 2 — DOCUMENT TYPE DETECTION
  Confidence scoring:
    filename + email headers + vocabulary + page count + first 500 chars

  High confidence  → single chunker for detected type
  Low confidence   → dual processing (both chunkers), mark low_confidence = True
  Very low (contracts) → status: "needs_review", notify admin, stop
━━━━━━━━━━━━━━━━━━
        │
        ↓
CHUNKING (adaptive per document type)
  contract     → section/clause boundaries, 300-700t, meaning > token count
  legal_brief  → paragraph boundaries, 300-400t, 50t overlap
  email        → one chunk per reply, 500t hard cap
  note         → single chunk

  → contextual prefix added to each chunk before embedding
  → source_type assigned per chunk
  → section_path and hierarchy metadata computed
━━━━━━━━━━━━━━━━━━
        │
        ↓
EMBEDDING
  BGE-M3 (self-hosted) embeds each chunk with its contextual prefix
━━━━━━━━━━━━━━━━━━
        │
        ↓
INDEXING
  ├── Qdrant        ← chunk vectors + full payload (no text)
  └── Elasticsearch ← chunk text + full payload

  PostgreSQL ← document metadata only (no chunks)
━━━━━━━━━━━━━━━━━━
        │
        ↓
Update PostgreSQL status → "ready"
Admin portal: ✅ ready
```

### Pipeline 2 — Retrieval

```
Query + user context (user_id, role, case_id)
        │
        ↓
Redis semantic cache check
  Key: hash(query_embedding + case_id + user_id)
  Scoped by case and user — prevents cross-case or cross-user cache leakage
  Similarity > 0.95 → return cached answer instantly ⚡
        │
        ↓ (cache miss)
━━━━━━━━━━━━━━━━━━
QUERY HANDLING
  Original query is always preserved.
  Two parallel retrieval paths:

  ├── Rewritten query → BGE-M3 embed → Qdrant dense search   → top 40
  │     (benefits from semantic expansion)
  └── Original query  → Elasticsearch BM25                   → top 40
        (benefits from exact legal keywords)

  Results merged before reranking.
  Prevents loss of user intent while benefiting from query expansion.

Both paths filtered by: { assigned_lawyers: [user.id], case_id, is_latest: true }
━━━━━━━━━━━━━━━━━━
        │
        ↓
RRF FUSION → unified top 20
        │
        ↓
RERANKER (bge-reranker-base, self-hosted)
  Scores each chunk against query
  Returns top 5 with scores
        │
        ↓
CONTEXT EXPANSION (score-based, not rank-based)

  MAX_CONTEXT_TOKENS = 1500

  top1, top2 = results[0], results[1]
  gap = top1.score - top2.score

  if top1.score > 0.8 and gap < 0.05:
      # ambiguous — both chunks matter equally
      candidates = [top1, top2]
      for chunk in candidates:
          neighbors = get_neighbors_same_section(chunk)
          if not neighbors:
              neighbors = get_neighbors_global(chunk)  # fallback
          selected.extend([chunk] + neighbors)
      return trim_to_token_budget(selected, MAX_CONTEXT_TOKENS)

  elif top1.score > 0.8 and gap >= 0.05:
      # confident — top1 clearly wins
      neighbors = get_neighbors_same_section(top1)
      if not neighbors:
          neighbors = get_neighbors_global(top1)  # fallback
      selected = [top1] + neighbors
      return trim_to_token_budget(selected, MAX_CONTEXT_TOKENS)

  else:
      # low confidence — no expansion, use top-k as is
      return results[:5]

Neighbor selection:
  Primary:  same section_path, chunk_index ± 1
  Fallback: global_index ± 1 (when section has insufficient context)
━━━━━━━━━━━━━━━━━━
        │
        ↓
Top chunks (with expansion where applicable) → Generation pipeline
```

### Context Expansion Philosophy

Retrieval operates on small, precise chunks. Generation requires complete context. Therefore:

> **Retrieval unit ≠ Reasoning unit**

Chunks are retrieved individually for precision, then expanded using section hierarchy, neighboring chunks, and a hard token budget. This allows precise retrieval while preserving full legal meaning for the LLM.

### Pipeline 3 — Generation

```
Expanded chunks + query + chat history
        │
        ↓
PROMPT BUILDER (LangChain ChatPromptTemplate)
  System: "You are a legal document assistant.
           Answer ONLY from the provided context.
           If the answer is not in the context, say:
           'I don't have that information in the available documents.'
           Cite every claim: [Source: {doc_name}, v{version}, p{page}, {section_title}]
           If the question is clearly general knowledge, answer directly."

  Context: expanded chunks labeled by source and section
  History: last N turns via LangChain ConversationBufferWindowMemory
  Query:   rewritten user question
        │
        ↓
LLM CLIENT (LangChain ChatOpenAI + ChatGroq)
  Primary:  GPT-4o via ChatOpenAI
  Fallback: Llama-3 via ChatGroq (70% cheaper, used for non-critical queries)
  Swapping between models requires only changing the LangChain client — no prompt changes
        │
        ↓
STREAMER
  Streams tokens via WebSocket
  Citations rendered inline as answer streams
        │
        ↓
CACHE WRITER (Redis)
  Key: hash(query_embedding + case_id + user_id)
  Stores: { answer, chunks_used, file_ids, case_id, created_at }
  TTL: 1 hour
  On document delete: invalidate all entries with matching file_id
        │
        ↓
Langfuse logs full trace:
  query, rewritten_query, user_id, case_id,
  retrieved_chunks with scores and ranks,
  expansion_decision, model_used, tokens, cost, latency_ms, answer
```

---

## Storage Architecture

Each store has a single well-defined responsibility. No store does another store's job.

| Store | Responsibility | What It Holds |
|-------|---------------|---------------|
| AWS S3 | Source of truth | Original files forever. If all DBs are lost, re-ingestion rebuilds everything from S3. |
| Qdrant | Dense vector search | Chunk vectors + full payload. No text stored. |
| Elasticsearch | Sparse keyword search (BM25) | Chunk text + full payload. BM25 needs actual text. |
| PostgreSQL | Structured metadata only | Cases, documents, users, conversations, messages. No chunks. |
| Redis | Semantic cache + task queue | Cached answers (TTL 1hr) + Celery broker. |

### Qdrant Payload (per chunk, no text)

```python
{
    # identity
    "chunk_id":       "uuid",
    "file_id":        "uuid",
    "case_id":        "uuid",

    # access control
    "assigned_lawyers": ["uuid1", "uuid2"],
    "is_latest":        True,

    # document structure
    "doc_type":         "contract",
    "source_type":      "contract_clause",
    "section_path":     "article_3.termination",
    "section_title":    "Termination",
    "parent_section":   "article_3",
    "chunk_index":      2,
    "global_index":     14,

    # quality flags
    "low_confidence":   False,

    # location
    "page":             4,

    # type-specific metadata
    "meta": {
        # contract
        "clause_number": "3.2"

        # email (when doc_type is email)
        # "from":    "client@firm.com",
        # "to":      "lawyer@firm.com",
        # "subject": "Re: Settlement",
        # "date":    "2024-01-03"

        # brief
        # "paragraph_id": 12
    }
}
```

### Elasticsearch Document (Qdrant payload + text)

```python
{
    # everything from Qdrant payload
    # plus:
    "text": "chunk text with contextual prefix"
}
```

### Elasticsearch Index Mapping (email metadata)

Email metadata fields must be explicitly mapped for structured filtering:

```json
{
    "mappings": {
        "properties": {
            "meta.from":    { "type": "keyword" },
            "meta.to":      { "type": "keyword" },
            "meta.subject": { "type": "text" },
            "meta.date":    { "type": "date" }
        }
    }
}
```

This enables structured queries such as:
- "emails from client@acme.com in January"
- "messages about settlement"

### Redis Cache Entry

```python
{
    "answer":      "...",
    "chunks_used": ["chunk_id1", "chunk_id2"],
    "file_ids":    ["uuid"],
    "case_id":     "uuid",
    "created_at":  timestamp
}

# Key: hash(query_embedding + case_id + user_id)
# Scoped by case and user — prevents cross-case and cross-user cache leakage
# TTL: 1 hour
```

### Uniform Schema

All four document types produce identical schema in every store. Chunking strategy affects content, size, and source_type — never the schema structure. Complexity is fully isolated in the ingestion pipeline.

### Delete Cascade

```python
async def delete_document(file_id: str):
    await asyncio.gather(
        s3.delete_object(key=f"documents/{file_id}"),
        qdrant.delete(filter={"file_id": file_id}),
        elasticsearch.delete_by_query({"file_id": file_id}),
        postgres.execute("DELETE FROM documents WHERE file_id = %s", file_id),
        redis.invalidate_by_file(file_id)
    )
```

---

## PostgreSQL Schema

```sql
CREATE TABLE users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'lawyer', 'paralegal')),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cases (
    case_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    client_name      TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('active', 'closed')),
    closed_at        TIMESTAMP,
    created_by       UUID NOT NULL REFERENCES users(user_id),
    created_at       TIMESTAMP DEFAULT NOW(),
    assigned_lawyers UUID[] NOT NULL DEFAULT '{}'
);

CREATE TABLE documents (
    file_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id        UUID NOT NULL REFERENCES cases(case_id),
    name           TEXT NOT NULL,
    version        INTEGER NOT NULL DEFAULT 1,
    is_latest      BOOLEAN NOT NULL DEFAULT TRUE,
    status         TEXT NOT NULL CHECK (status IN ('processing', 'ready', 'failed', 'needs_review')),
    doc_type       TEXT CHECK (doc_type IN ('contract', 'legal_brief', 'email', 'note')),
    low_confidence BOOLEAN NOT NULL DEFAULT FALSE,
    s3_key         TEXT NOT NULL,
    uploaded_by    UUID NOT NULL REFERENCES users(user_id),
    uploaded_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id),
    case_id         UUID NOT NULL REFERENCES cases(case_id),
    title           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id),
    query           TEXT NOT NULL,
    answer          TEXT NOT NULL,
    chunks_used     JSONB NOT NULL DEFAULT '[]',
    model_used      TEXT NOT NULL,
    latency_ms      INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### `chunks_used` JSONB Structure

```json
[
    {
        "chunk_id":      "uuid",
        "file_id":       "uuid",
        "section_path":  "article_3.termination",
        "section_title": "Termination",
        "score":         0.94,
        "rank":          1,
        "expanded":      true
    }
]
```

---

## Two-Level RBAC

```
Level 1 — Role
  admin      → full access, upload, delete, case management
  lawyer     → query only, assigned cases only
  paralegal  → query only, explicitly assigned cases only

Level 2 — Case Ownership
  assigned_lawyers: ["lawyer_id_1", "lawyer_id_2"]

At query time — both filters apply simultaneously:
  query_filter = {
    "must": [
      { "key": "assigned_lawyers", "match": { "any": [user.id] } },
      { "key": "case_id",          "match": { "value": selected_case_id } }
    ]
  }
```

Filtering at vector DB level — not application code. Two lawyers with identical roles cannot see each other's cases.

---

## Case Management

- Cases have status: active or closed
- Closed cases stay indexed (institutional memory) but excluded from default search
- Lawyer portal has two tabs: Active Cases / Closed Cases
- Documents belong to cases — access to a case = access to all its documents
- Evidence files, witness reports, expert testimony all map to existing 4 document types

---

## API Endpoints

```
# Auth
POST   /auth/login
POST   /auth/logout
GET    /auth/me

# Cases (Admin)
POST   /cases
GET    /cases
GET    /cases/{case_id}
PATCH  /cases/{case_id}
DELETE /cases/{case_id}

# Documents (Admin)
POST   /cases/{case_id}/documents/upload
GET    /cases/{case_id}/documents
GET    /cases/{case_id}/documents/{file_id}
PATCH  /cases/{case_id}/documents/{file_id}
DELETE /cases/{case_id}/documents/{file_id}

# Chat (Lawyer)
POST   /chat
GET    /chat/conversations
GET    /chat/conversations/{id}
DELETE /chat/conversations/{id}
```

---

## Technology Stack

| Layer | Technology | Hosting |
|-------|-----------|---------|
| API | FastAPI | Self-hosted |
| LLM Primary | GPT-4o | OpenAI API |
| LLM Fallback | Llama-3 via Groq | Groq API |
| Embedder | BGE-M3 | Self-hosted |
| Reranker | bge-reranker-base | Self-hosted |
| Vector DB | Qdrant | Docker |
| Keyword Search | Elasticsearch | Docker |
| Relational DB | PostgreSQL | Docker |
| Cache + Queue | Redis | Docker |
| File Storage | AWS S3 | AWS |
| Task Queue | Celery | Self-hosted |
| PDF Parser | pdfplumber | Self-hosted |
| DOCX Parser | python-docx | Self-hosted |
| EML Parser | Python email stdlib | Self-hosted |
| Prompt Templates | LangChain (ChatPromptTemplate) | Self-hosted |
| Conversation Memory | LangChain (ConversationBufferWindowMemory) | Self-hosted |
| LLM Client | LangChain (ChatOpenAI + ChatGroq) | Self-hosted |
| Observability | Langfuse | Self-hosted |
| Evaluation | RAGAS + DeepEval | Self-hosted |
| CI/CD | GitHub Actions | GitHub |
| Containerization | Docker Compose | Self-hosted |
| Package Manager | uv | Self-hosted |

### LangChain Usage

LangChain is used deliberately and minimally — only where it genuinely reduces boilerplate without conflicting with custom logic. All retrieval, chunking, and expansion logic is pure Python.

```python
# Prompt templating
from langchain.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("placeholder", "{history}"),
    ("human", "{query}")
])

# Conversation memory
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(k=10, return_messages=True)

# LLM client — swap GPT-4o and Groq with no prompt changes
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

llm = ChatOpenAI(model="gpt-4o")       # primary
llm = ChatGroq(model="llama3-8b-8192") # fallback
```

Everything else in the pipeline — retrieval, context expansion, caching, indexing — is pure Python with direct client libraries.

### Privacy Architecture

- BGE-M3 and bge-reranker-base run entirely on firm's server
- Only top 5 retrieved chunks (after expansion) sent to GPT-4o
- S3 bucket configurable to private VPC
- Documents never leave firm infrastructure during ingestion or retrieval

---

## Debugging a Wrong Answer

When the system gives a wrong answer, the schema enables full traceability:

```
Wrong answer received
        │
        ↓
messages table
  → chunks_used: chunk_ids, section_paths, scores, ranks, expanded flags
  → model_used, latency_ms, query, answer
        │
        ↓
Was it a cache hit?
  → Redis chunks_used → if cached answer was wrong → invalidate entry
        │
        ↓ (not cache hit)
Fetch chunks from Elasticsearch by chunk_id → read actual text
        │
        ├── Text irrelevant → retrieval problem
        │     → check section_path → was chunking correct?
        │     → check low_confidence flag → was detection uncertain?
        │     → check doc_type → was document classified correctly?
        │     → check source_type → was chunk type assigned correctly?
        │
        └── Text relevant → generation problem
              → check prompt in Langfuse trace
              → check model_used → was it Groq fallback?
              → check if LLM ignored context and hallucinated
        │
        ↓
Langfuse full trace
  → rewritten query, retrieval scores, reranker scores,
    expansion decision, exact prompt sent to LLM,
    tokens used, cost, latency breakdown
```

---

## Evaluation & Quality Gating

### RAGAS Metrics

| Metric | Target |
|--------|--------|
| Faithfulness | > 0.92 |
| Context Precision | > 0.88 |
| Answer Relevancy | > 0.90 |
| Citation Accuracy | > 0.95 |

### Legal Safety Tests (100-question golden dataset)

- Cross-contract contamination: 0 failures allowed
- Case isolation: 0 failures allowed
- RBAC enforcement: 0 failures allowed
- Version accuracy: 0 failures allowed
- Citation precision: 0 failures allowed
- Low confidence chunk handling: verified not surfaced as high-confidence answers

### CI/CD Gate

```yaml
# .github/workflows/eval_gate.yml
- name: Run RAGAS Evaluation
  run: pytest tests/evaluation/ --threshold=0.90

- name: Run Legal Safety Tests
  run: pytest tests/legal_safety/
  # cross-contract contamination: 0 failures
  # RBAC enforcement: 0 failures
  # version accuracy: 0 failures
  # case isolation: 0 failures

- name: Block Deployment on Failure
  if: failure()
  run: |
    echo "Quality gate failed. Deployment blocked."
    exit 1
```

---

## Open Problems

| Problem | Impact | Status |
|---------|--------|--------|
| EML attachments | Contracts attached to emails need separate pipeline processing | Open |
| Contract confidence threshold calibration | Exact gap threshold for needs_review not calibrated | Needs real document testing |
| Suggested follow-up questions | Generation mechanism not designed | Open |
| Conversation sharing | Sharing within case access group not designed | Open |
| Non-English documents | Chunking rules assume English legal vocabulary | Known limitation |
| Multi-hop reasoning | Queries requiring synthesis across 3+ documents | GraphRAG extension planned |
| Complex table reasoning | Heavily formatted tables misread by pdfplumber | GPT-4o Vision extension planned |
| Answer validation layer | No confidence scoring on generated answers | Known weakness |
| Context expansion token budget | Now partially addressed: MAX_CONTEXT_TOKENS = 1500 enforced during expansion. Still requires tuning based on real usage. | Partially addressed |
| Historical version queries | Retrieval always filters is_latest=True | version_override parameter needed |

---

## 6-Week Implementation Roadmap

| Week | Focus | Deliverable |
|------|-------|-------------|
| Week 1 | Core ingestion + storage | Parser routing, Qdrant + Elasticsearch + PostgreSQL + Redis setup, AWS S3, Celery async, basic end-to-end ingestion working for one document type |
| Week 2 | Detection + chunking | Two-phase detection with confidence scoring, adaptive chunking per document type, dual processing for low confidence, contextual prefix, section hierarchy metadata, needs_review status |
| Week 3 | RBAC + case management | Two-level access control, admin portal, case status (active/closed), document versioning, delete cascade across all stores |
| Week 4 | Hybrid search + generation | BGE-M3 self-hosted, BM25, RRF, bge-reranker-base, score-based context expansion, FastAPI streaming + WebSockets, multi-turn conversation, citation enforcement |
| Week 5 | Evaluation pipeline | 100-question golden dataset, RAGAS scoring, legal safety tests, CI/CD quality gate, semantic cache with invalidation |
| Week 6 | Observability + deployment | Langfuse full tracing, Docker Compose complete stack, README benchmark table, documented failure modes, demo video |

---

## File Structure

```
Atticus/
│
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── config.py
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── documents.py
│   │   │   └── chat.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth_middleware.py
│   │       └── rbac_middleware.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py
│   │   └── dependencies.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── case.py
│   │   ├── document.py
│   │   ├── user.py
│   │   └── chat.py
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── eml_parser.py
│   │   │   └── txt_parser.py
│   │   ├── detection/
│   │   │   ├── __init__.py
│   │   │   ├── file_type_detector.py
│   │   │   └── doc_type_detector.py
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── contract_chunker.py
│   │   │   ├── brief_chunker.py
│   │   │   ├── email_chunker.py
│   │   │   └── note_chunker.py
│   │   ├── enrichment/
│   │   │   ├── __init__.py
│   │   │   └── prefix_enricher.py
│   │   └── indexers/
│   │       ├── __init__.py
│   │       ├── qdrant_indexer.py
│   │       └── elastic_indexer.py
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── query_rewriter.py
│   │   ├── dense_search.py
│   │   ├── sparse_search.py
│   │   ├── rrf.py
│   │   ├── reranker.py
│   │   ├── context_expander.py
│   │   └── cache/
│   │       ├── __init__.py
│   │       ├── semantic_cache.py
│   │       └── cache_invalidator.py
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── prompt_builder.py
│   │   ├── chat_history.py
│   │   ├── llm_client.py
│   │   └── streamer.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   └── reranker.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py
│   │   ├── qdrant.py
│   │   ├── elastic.py
│   │   └── redis.py
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── s3.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── ingest_task.py
│   │
│   └── migrations/
│       └── 001_initial.sql
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── app/
│       │   ├── admin/
│       │   └── lawyer/
│       ├── components/
│       │   ├── chat/
│       │   ├── cases/
│       │   └── documents/
│       └── lib/
│           ├── api.ts
│           └── auth.ts
│
├── tests/
│   ├── evaluation/
│   │   ├── golden_dataset.json
│   │   └── test_ragas.py
│   ├── legal_safety/
│   │   ├── test_rbac.py
│   │   ├── test_case_isolation.py
│   │   ├── test_versioning.py
│   │   └── test_citations.py
│   └── unit/
│       ├── test_parsers.py
│       ├── test_detectors.py
│       └── test_chunkers.py
│
└── .github/
    └── workflows/
        └── eval_gate.yml
```