# Atticus Benchmarks and Evaluation

This document outlines the evaluation methodology and benchmark results for the Atticus RAG system.
These metrics justify the architectural decisions made in the system, specifically the use of hybrid search, cross-encoder reranking, and semantic caching.

## Methodology

### 1. Golden Dataset
- **Size**: 30 Q&A pairs
- **Source**: Curated manually using the demo dataset (`demo_data/`).
- **Disclaimer**: Due to the confidential nature of legal documents, real-world case files could not be used. A diverse dataset was curated based on mock legal scenarios (e.g., depositions, briefs) to approximate real-world complexity.

### 2. Metrics
Evaluated using the [Ragas](https://docs.ragas.io/en/stable/) framework measuring:
- **Context Precision**: The signal-to-noise ratio of the retrieved chunks.
- **Context Recall**: The extent to which the retrieved chunks contain all the necessary information to answer the query.
- **Answer Relevancy**: How well the generated answer addresses the question.
- **Faithfulness**: The extent to which the generated answer can be logically derived from the context (hallucination rate).

---

## Results

*(Run the evaluation scripts to populate these numbers)*

### Architecture A/B Comparison (Ragas)
| Configuration | Context Precision | Context Recall | Notes |
| :--- | :--- | :--- | :--- |
| **Dense Only (Qdrant)** | `0.XX` | `0.XX` | Baseline using only BGE-m3 embeddings |
| **Hybrid (Dense + Sparse/ES + RRF)** | `0.XX` | `0.XX` | Adds exact keyword matching for legal terms |
| **Hybrid + CrossEncoder Reranker** | `0.XX` | `0.XX` | Final architecture. Maximizes precision at top-K. |

### Chunking Strategy Comparison
| Strategy | Context Recall | Notes |
| :--- | :--- | :--- |
| **Fixed-Size (500 tokens)** | `0.XX` | Standard naive chunking |
| **Document-Specific (Email/Deposition)** | `0.XX` | Preserves structural boundaries and speaker cadence |

### API Load Testing & Caching (Locust)
| Scenario | Average Latency | P95 Latency | Max Concurrent Users |
| :--- | :--- | :--- | :--- |
| **Scenario A: Cache Misses** (Full LLM Generation) | `XX.X s` | `XX.X s` | Bottlenecked by local 70B parameter LLM |
| **Scenario B: Cache Hits** (Redis Semantic Cache) | `XXX ms` | `XXX ms` | Bypasses embedding, retrieval, and generation entirely |

### Ingestion Throughput
- **Throughput**: `[X]` documents per minute
- **Test Set**: `demo_data/` text and PDF documents processing via Celery pipeline (detect → parse → chunk → embed → index).
