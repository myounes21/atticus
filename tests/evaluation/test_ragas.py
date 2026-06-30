import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision,
)
from ragas.run_config import RunConfig
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.outputs import ChatResult

from backend.db.postgres import fetch_optional
from backend.retrieval.pipeline import retrieve

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).resolve().parent / "golden_dataset.json"

def load_golden_dataset():
    if not GOLDEN_DATASET_PATH.exists():
        logger.error(f"{GOLDEN_DATASET_PATH} not found.")
        import sys
        sys.exit(1)
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_json_string(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

class CleanJsonChatOpenAI(ChatOpenAI):
    def _generate(self, *args, **kwargs) -> ChatResult:
        logger.info(f"Rate limited judge sleeping for 5 seconds...")
        time.sleep(5)
        result = super()._generate(*args, **kwargs)
        for gen in result.generations:
            gen.message.content = clean_json_string(gen.message.content)
            gen.text = clean_json_string(gen.text)
        return result

    async def _agenerate(self, *args, **kwargs) -> ChatResult:
        logger.info(f"Rate limited judge sleeping for 5 seconds...")
        time.sleep(5)
        result = await super()._agenerate(*args, **kwargs)
        for gen in result.generations:
            gen.message.content = clean_json_string(gen.message.content)
            gen.text = clean_json_string(gen.text)
        return result
        
def run_ragas_evaluation():
    records = load_golden_dataset()
    row = fetch_optional("SELECT case_id, assigned_lawyers FROM cases WHERE name = 'Finch Demo Matter' LIMIT 1")
    case_id, user_id = row["case_id"], row["assigned_lawyers"][0]
    
    # Evaluate 10 records (25 mins)
    eval_records = records[:10]
    
    results_for_ragas = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    api_key = os.getenv("QWEN_API_KEY")
    base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

    if not api_key:
        logger.error("QWEN_API_KEY not set in environment")
        import sys; sys.exit(1)

    for record in eval_records:
        question = record["question"]
        
        retrieval_result = retrieve(
            query=question,
            case_id=case_id,
            user_id=user_id,
            skip_cache=True
        )
        contexts = [chunk.text for chunk in retrieval_result.chunks]
        
        llm_gen = CleanJsonChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model="qwen-plus", 
            temperature=0.0
        )
        context_str = "\n".join(contexts)
        prompt = f"Answer the question based on the context.\nContext: {context_str}\nQuestion: {question}"
        answer_raw = llm_gen.invoke([HumanMessage(content=prompt)]).content
        results_for_ragas["question"].append(question)
        results_for_ragas["contexts"].append(contexts)
        results_for_ragas["ground_truth"].append(record["ground_truth"])
        results_for_ragas["answer"].append(str(answer_raw))

    hf_dataset = Dataset.from_dict(results_for_ragas)
    
    judge_llm = CleanJsonChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model="qwen-plus",
        temperature=0.0,
        max_retries=10,
        timeout=120
    )
    eval_embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    config = RunConfig(timeout=120, max_retries=10, max_workers=1)

    result = evaluate(
        hf_dataset,
        metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
        llm=judge_llm,
        embeddings=eval_embeddings,
        run_config=config,
        raise_exceptions=False
    )
    
    print("\n=====================================")
    print("RAGAS EVALUATION RESULTS")
    print("=====================================")
    for metric_name, display_name in [
        ('context_precision', 'Context Precision'),
        ('context_recall', 'Context Recall'),
        ('faithfulness', 'Answer Faithfulness'),
        ('answer_relevancy', 'Answer Relevancy')
    ]:
        try:
            val = result[metric_name]
        except KeyError:
            val = None
        if isinstance(val, list):
            valid = [x for x in val if x is not None and not str(x).lower() == 'nan']
            if valid:
                print(f"{display_name:<21}: {sum(valid)/len(valid):.3f}")
            else:
                print(f"{display_name:<21}: FAILED (Raw: {val})")
        else:
            if val is None or str(val).lower() == 'nan':
                print(f"{display_name:<21}: FAILED (Raw: {val})")
            else:
                print(f"{display_name:<21}: {val:.3f}")
    print("=====================================")
    
    results_path = Path(__file__).resolve().parent / "ragas_results.json"
    try:
        df = result.to_pandas()
        results_data = df.to_dict(orient="records")
    except Exception:
        results_data = {"error": "Could not convert to pandas", "raw_result": str(result)}
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=4)
        
if __name__ == "__main__":
    run_ragas_evaluation()
