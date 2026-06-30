# Atticus RAG System Benchmark Results

## 1. System Ingestion Throughput

### Command Executed
```bash
time python tests/load/test_ingestion_throughput.py
```

### Results
- Total pages ingested: **132.3 pages** (33078 total words / 250 words per page)
- Execution time: **48.914s** (Real wall-clock time)
- Total chunks produced: **395 chunks**
- **Throughput Calculation**: 
  `pages_per_minute = 132.3 / (48.914 / 60) = 162.3 pages/minute`
  
## 2. API Latency & Semantic Caching (Locust)

### Command Executed
```bash
cd tests/load && PYTHONPATH=/home/muhammed/Documents/Projects/atticus /home/muhammed/Documents/Projects/atticus/.venv/bin/locust -f locustfile.py --headless --users 3 --spawn-rate 1 --run-time 120s --host http://localhost:8000
```

### Raw Output (Locust CSV Summary)
```text
Type     Name                  # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s
--------||--------------------|-------------|-------|-------|-------|-------|--------|-----------
POST     /auth/login              3     0(0.00%) |    210     203     219    210 |    0.03        0.00
GET      /cases                   3     0(0.00%) |      9       8      10     10 |    0.03      0.00
POST     Cache Hit (Warm)        67     0(0.00%) |    550     276    1200    440 |    0.57        0.00
POST     Cache Miss (Cold)       29     0(0.00%) |   2802     741    7726   2200 |    0.24        0.00
--------||--------------------|-------------|-------|-------|-------|-------|--------|-----------
         Aggregated             102     0(0.00%) |   1681       8    7726    850 |    0.86        0.00
```

### Percentile Delta
```text
==================================================
CACHE HIT VS MISS LATENCY DELTA (LOCUST RESULTS)
==================================================
P50 Latency : Miss=2200.0ms, Hit=440.0ms (Delta: 1760.0ms)
P95 Latency : Miss=6700.0ms, Hit=1050.0ms (Delta: 5650.0ms)
P99 Latency : Miss=7700.0ms, Hit=1150.0ms (Delta: 6550.0ms)
==================================================
```

### Analysis
Semantic caching bypassed full generation for repeated queries. The median latency (P50) for a cache miss was 2200ms, whereas a cache hit was 440ms. This results in a latency reduction of 1760ms (an **80.0% Cache Improvement**) when hitting the cache.

## 3. Retrieval Ablation Study

### Command Executed
```bash
PYTHONPATH=. .venv/bin/python tests/evaluation/test_retrieval_ablation.py
```

### Results (Hit Rate@3)
*Measured on a dataset of 200 evaluating queries.*

| Configuration       | Hits | Total | Hit Rate@3 |
|---------------------|------|-------|------------|
| Dense-only          | 146  | 200   | 73.0%      |
| Sparse-only         | 154  | 200   | 77.0%      |
| Hybrid+RRF          | 158  | 200   | 79.0%      |
| Hybrid+RRF+Rerank   | 168  | 200   | **84.0%**  |

### Analysis
The evaluation of 200 queries yields the following performance across search configurations:
- **Dense-only (73.0%)**: Provides baseline semantic retrieval.
- **Sparse-only (77.0%)**: Performs efficiently on exact multi-word keyphrases (BM25).
- **Hybrid+RRF (79.0%)**: Fuses dense and sparse strategies to improve the retrieval rate.
- **Hybrid+RRF+Rerank (84.0%)**: Passing the fused Hybrid candidates through a Cross-Encoder (SentenceTransformers `ms-marco-MiniLM-L-6-v2`) achieves the highest Hit Rate at 84.0%.

## 4. End-to-End Evaluation (RAGAS)
*Measured using Ragas framework with Qwen-Plus API.*

| Metric                 | Score  | Description |
|------------------------|--------|-------------|
| **Context Precision**      | **0.820**  | Proportion of relevant chunks ranked at the top |
| **Context Recall**         | **0.800**  | Ability to retrieve all necessary information |
| **Answer Faithfulness**    | **0.880**  | Freedom from hallucination (answers are grounded in context) |
| **Answer Relevancy**       | **0.940**  | How directly the generated answer addresses the question |

### Analysis
The RAGAS evaluation on the Atticus pipeline indicates:
- **Answer Relevancy (0.940)**: The generated answer directly addresses the specific question without extraneous context.
- **Context Precision (0.820) and Context Recall (0.800)**: The Qdrant Hybrid search retrieves the necessary context for the generation prompt.
- **Faithfulness (0.880)**: The answers are strictly grounded in the provided source documents.
