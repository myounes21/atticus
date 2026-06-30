"""
Retrieval Ablation Test: Dense-only vs Sparse-only vs Hybrid+RRF vs Hybrid+RRF+Rerank
Measures Hit Rate@3 across 4 configurations using the golden dataset.

A query is a "hit" if at least one of the top-3 retrieved chunks contains ALL
expected_keywords (case-insensitive) for that query.

Uses real expected_keywords from golden_dataset.json — ONLY records that have
multi-word, specific keyphrases are used to discriminate between configs.
Single-word generic keywords are excluded from the discriminating set.
"""
import json
import sys
import uuid
import logging
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PYTHONPATH_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PYTHONPATH_root))

from backend.models.embedder import embed_texts
from backend.retrieval.dense_search import search as dense_search
from backend.retrieval.sparse_search import search as sparse_search
from backend.retrieval.rrf import fuse
from backend.retrieval.reranker import rerank

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1000)
def cached_embed(question: str):
    return embed_texts([question])[0]

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "golden_dataset.json"


def load_dataset():
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def is_hit(chunks, expected_keywords: list[str]) -> bool:
    """Return True if any chunk text contains ALL expected_keywords (case-insensitive)."""
    for chunk in chunks:
        text_lower = chunk.payload.get("text", "").lower() if hasattr(chunk, "payload") else ""
        # For RerankedChunk from dense/sparse, text is in payload or text attr
        if not text_lower:
            # Try other common attributes
            if hasattr(chunk, "text"):
                text_lower = chunk.text.lower()
            else:
                continue
        if all(kw.lower() in text_lower for kw in expected_keywords):
            return True
    return False


def is_hit_sparse(chunks, expected_keywords: list[str]) -> bool:
    """Sparse search returns dicts with 'text' key."""
    for chunk in chunks:
        text_lower = ""
        if isinstance(chunk, dict):
            text_lower = chunk.get("text", "").lower()
        elif hasattr(chunk, "payload"):
            text_lower = chunk.payload.get("text", "").lower()
        elif hasattr(chunk, "text"):
            text_lower = chunk.text.lower()
        if all(kw.lower() in text_lower for kw in expected_keywords):
            return True
    return False


def run_ablation():
    records = load_dataset()
    case_id = uuid.UUID("99074b44-e2d8-497f-bb06-9be6b87e171c")
    user_id = uuid.UUID("ac64fa53-0aa3-4094-aec4-0f1dd6fd91af")  # actual admin user

    # Use all records with multi-word expected_keywords for proper discrimination
    discriminating = []
    for r in records:
        kws = r.get("expected_keywords", [])
        # Include if has any multi-word keyword (more specific)
        if any(len(kw.split()) > 1 for kw in kws):
            discriminating.append(r)

    print(f"\nTotal dataset records: {len(records)}")
    print(f"Discriminating records (with multi-word keywords): {len(discriminating)}")

    configs = {
        "Dense-only": {"use_dense": True, "use_sparse": False, "use_rrf": False, "use_rerank": False},
        "Sparse-only": {"use_dense": False, "use_sparse": True, "use_rrf": False, "use_rerank": False},
        "Hybrid+RRF": {"use_dense": True, "use_sparse": True, "use_rrf": True, "use_rerank": False},
        "Hybrid+RRF+Rerank": {"use_dense": True, "use_sparse": True, "use_rrf": True, "use_rerank": True},
    }

    results = {}

    for config_name, config in configs.items():
        hits = 0
        total = 0
        per_query = []

        for record in discriminating:
            question = record["question"]
            keywords = record.get("expected_keywords", [])
            if not keywords:
                continue

            try:
                query_embedding = cached_embed(question)
            except Exception as e:
                print(f"  [WARN] Embedding failed for '{question[:40]}': {e}")
                continue

            dense_chunks = []
            sparse_chunks = []

            if config["use_dense"]:
                try:
                    dense_chunks = dense_search(
                        query_vector=query_embedding,
                        case_id=case_id,
                        user_id=user_id,
                        top_k=12,
                    )
                except Exception as e:
                    print(f"  [WARN] Dense search failed: {e}")

            if config["use_sparse"]:
                try:
                    sparse_chunks = sparse_search(
                        query_text=question,
                        case_id=case_id,
                        user_id=user_id,
                        top_k=12,
                    )
                except Exception as e:
                    print(f"  [WARN] Sparse search failed: {e}")

            if config["use_rrf"]:
                fused_chunks = fuse(dense_chunks, sparse_chunks, top_k=10)
                candidates = fused_chunks
            elif config["use_dense"]:
                candidates = dense_chunks[:10]
            else:
                candidates = sparse_chunks[:10]

            if config["use_rerank"] and candidates:
                final_chunks = rerank(question, candidates, top_k=3)
            else:
                final_chunks = candidates[:3]

            hit = is_hit(final_chunks, keywords) or is_hit_sparse(final_chunks, keywords)
            hits += int(hit)
            total += 1
            per_query.append({"question": question[:60], "hit": hit, "keywords": keywords})

        hit_rate = (hits / total * 100) if total > 0 else 0
        results[config_name] = {"hits": hits, "total": total, "hit_rate_at_3": hit_rate}

    print("\n" + "=" * 60)
    print("RETRIEVAL ABLATION: Hit Rate@3")
    print("=" * 60)
    print(f"{'Configuration':<25} {'Hits':>6} {'Total':>7} {'Hit Rate@3':>12}")
    print("-" * 60)
    for config_name, r in results.items():
        print(f"{config_name:<25} {r['hits']:>6} {r['total']:>7} {r['hit_rate_at_3']:>11.1f}%")
    print("=" * 60)

    # Flag if all configs are too close (test is not discriminating)
    rates = [r["hit_rate_at_3"] for r in results.values()]
    if max(rates) - min(rates) < 10:
        print("\n⚠️  WARNING: Max spread is < 10 percentage points.")
        print("   The test may not be discriminating between configurations.")
        print("   Consider using harder, more specific expected_keywords.")

    # Save results
    out_path = Path(__file__).parent / "ablation_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    return results


if __name__ == "__main__":
    run_ablation()
