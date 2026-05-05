from __future__ import annotations

import json
import statistics
from typing import Any

# 评估模块：支持 lightweight（LLM judge）与 official（RAGAS）两条评估链路。

import pandas as pd

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError


class RagasRunner:
    """RAGAS 评估执行器。"""
    REQUIRED_COLUMNS = ["question", "answer", "contexts", "ground_truth"]
    METRIC_NAMES = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    METRIC_DESCRIPTIONS = {
        "faithfulness": "Whether the answer is grounded in retrieved contexts.",
        "answer_relevancy": "Whether the answer addresses the question directly.",
        "context_precision": "How much retrieved context is useful instead of noisy.",
        "context_recall": "How well retrieved context covers ground-truth facts.",
    }

    def __init__(self) -> None:
        self.client = SiliconFlowClient()

    def evaluate(self, dataset: list[dict[str, Any]], pipeline: str = "lightweight") -> dict[str, Any]:
        checked = self._validate_dataset(dataset)
        if checked["status"] != "ok":
            return checked

        if pipeline == "official":
            return self.evaluate_official(dataset)
        return self.evaluate_lightweight(dataset)

    def evaluate_ab(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        lightweight = self.evaluate_lightweight(dataset)
        official = self.evaluate_official(dataset)

        delta: dict[str, Any] = {}
        light_metrics = lightweight.get("metrics", {})
        off_metrics = official.get("metrics", {})
        for metric in self.METRIC_NAMES:
            lv = light_metrics.get(metric)
            ov = off_metrics.get(metric)
            if isinstance(lv, (int, float)) and isinstance(ov, (int, float)):
                delta[metric] = round(float(ov) - float(lv), 4)

        return {
            "status": "ok",
            "metric_descriptions": self.METRIC_DESCRIPTIONS,
            "lightweight": lightweight,
            "official": official,
            "delta_official_minus_lightweight": delta,
        }

    def evaluate_lightweight(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        rows_result: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for idx, row in enumerate(dataset):
            try:
                metrics = self._score_single_row_with_llm_judge(row)
                rows_result.append({"index": idx, "question": row["question"], "metrics": metrics})
            except Exception as exc:
                errors.append({"index": idx, "error": str(exc)})

        if not rows_result:
            return {
                "status": "error",
                "pipeline": "lightweight",
                "reason": "all rows failed",
                "metric_descriptions": self.METRIC_DESCRIPTIONS,
                "errors": errors,
            }

        agg = {metric: self._avg([x["metrics"][metric] for x in rows_result]) for metric in self.METRIC_NAMES}

        return {
            "status": "ok" if not errors else "partial",
            "pipeline": "lightweight",
            "rows": len(dataset),
            "scored_rows": len(rows_result),
            "failed_rows": len(errors),
            "metrics": agg,
            "metric_descriptions": self.METRIC_DESCRIPTIONS,
            "row_details": rows_result[:20],
            "errors": errors[:20],
        }

    def evaluate_official(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            from datasets import Dataset
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            from ragas import evaluate as ragas_evaluate
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from ragas.llms import LangchainLLMWrapper
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        except Exception as exc:
            return {
                "status": "error",
                "pipeline": "official",
                "reason": "official ragas dependencies are missing",
                "error": str(exc),
                "hint": "Install extras: pip install -e .[ragas]",
            }

        if not settings.siliconflow_api_key:
            return {
                "status": "error",
                "pipeline": "official",
                "reason": "HZ_RAG_SILICONFLOW_API_KEY is empty",
            }

        try:
            llm = ChatOpenAI(
                model=settings.siliconflow_chat_model,
                api_key=settings.siliconflow_api_key,
                base_url=settings.siliconflow_base_url,
                temperature=0.0,
                timeout=settings.siliconflow_timeout_seconds,
            )
            embeddings = OpenAIEmbeddings(
                model=settings.siliconflow_embedding_model,
                api_key=settings.siliconflow_api_key,
                base_url=settings.siliconflow_base_url,
                request_timeout=settings.siliconflow_timeout_seconds,
            )

            llm_wrapper = LangchainLLMWrapper(llm)
            emb_wrapper = LangchainEmbeddingsWrapper(embeddings)
            hf_dataset = Dataset.from_list(dataset)

            result = ragas_evaluate(
                dataset=hf_dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=llm_wrapper,
                embeddings=emb_wrapper,
            )

            metrics = self._extract_official_metrics(result)
            return {
                "status": "ok",
                "pipeline": "official",
                "rows": len(dataset),
                "metrics": metrics,
                "metric_descriptions": self.METRIC_DESCRIPTIONS,
            }
        except Exception as exc:
            return {
                "status": "error",
                "pipeline": "official",
                "reason": "official ragas evaluation failed",
                "error": str(exc),
            }

    def _score_single_row_with_llm_judge(self, row: dict[str, Any]) -> dict[str, float]:
        question = row["question"]
        answer = row["answer"]
        contexts = row["contexts"]
        ground_truth = row["ground_truth"]

        contexts_text = "\n".join([f"- {c}" for c in contexts])

        faithfulness = self._judge_score(
            task="faithfulness",
            instruction="Judge whether the answer is supported by context.",
            question=question,
            answer=answer,
            contexts=contexts_text,
            ground_truth=ground_truth,
        )
        answer_relevancy = self._judge_score(
            task="answer_relevancy",
            instruction="Judge whether the answer directly addresses the question.",
            question=question,
            answer=answer,
            contexts=contexts_text,
            ground_truth=ground_truth,
        )
        context_precision = self._judge_score(
            task="context_precision",
            instruction="Judge whether retrieved contexts are useful and not noisy.",
            question=question,
            answer=answer,
            contexts=contexts_text,
            ground_truth=ground_truth,
        )
        context_recall = self._judge_score(
            task="context_recall",
            instruction="Judge whether contexts cover key facts in ground truth.",
            question=question,
            answer=answer,
            contexts=contexts_text,
            ground_truth=ground_truth,
        )

        return {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }

    def _judge_score(self, task: str, instruction: str, question: str, answer: str, contexts: str, ground_truth: str) -> float:
        system_prompt = "You are a RAG evaluator. Return JSON only: {\"score\": 0.0-1.0, \"reason\": \"...\"}."
        user_prompt = (
            f"Metric: {task}\n"
            f"Instruction: {instruction}\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n"
            f"Ground Truth: {ground_truth}\n"
            f"Contexts:\n{contexts}\n"
        )

        try:
            content = self.client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=settings.siliconflow_chat_model,
                temperature=0.0,
                max_tokens=256,
            )
        except SiliconFlowError as exc:
            raise RuntimeError(f"Evaluation model call failed: {exc}") from exc

        score = self._parse_score(content)
        return max(0.0, min(1.0, score))

    def _extract_official_metrics(self, result: Any) -> dict[str, float]:
        if hasattr(result, "to_pandas"):
            df = result.to_pandas()
            if isinstance(df, pd.DataFrame):
                out: dict[str, float] = {}
                for metric in self.METRIC_NAMES:
                    if metric in df.columns:
                        vals = [float(v) for v in df[metric].dropna().tolist()]
                        out[metric] = round(float(statistics.mean(vals)), 4) if vals else 0.0
                if out:
                    return out

        for method in ("to_dict", "dict"):
            fn = getattr(result, method, None)
            if callable(fn):
                try:
                    obj = fn()
                    return self._extract_metrics_from_obj(obj)
                except Exception:
                    pass

        text = str(result)
        try:
            obj = json.loads(text)
            return self._extract_metrics_from_obj(obj)
        except Exception:
            return {metric: 0.0 for metric in self.METRIC_NAMES}

    def _extract_metrics_from_obj(self, obj: Any) -> dict[str, float]:
        out = {metric: 0.0 for metric in self.METRIC_NAMES}
        if isinstance(obj, dict):
            for metric in self.METRIC_NAMES:
                val = obj.get(metric)
                if isinstance(val, (int, float)):
                    out[metric] = round(float(val), 4)
            return out
        return out

    def _validate_dataset(self, dataset: list[dict[str, Any]]) -> dict[str, Any]:
        if not dataset:
            return {"status": "error", "reason": "empty dataset", "expected_columns": self.REQUIRED_COLUMNS}

        missing = []
        for idx, row in enumerate(dataset):
            for col in self.REQUIRED_COLUMNS:
                if col not in row:
                    missing.append({"row": idx, "column": col})
            if "contexts" in row and not isinstance(row["contexts"], list):
                return {"status": "error", "reason": "contexts must be list[str]", "row": idx}

        if missing:
            return {
                "status": "error",
                "reason": "missing required columns",
                "missing": missing,
                "expected_columns": self.REQUIRED_COLUMNS,
            }
        return {"status": "ok"}

    @staticmethod
    def _parse_score(content: str) -> float:
        text = content.strip()
        if not text:
            return 0.0

        try:
            obj = json.loads(text)
            return float(obj.get("score", 0.0))
        except Exception:
            pass

        for token in text.replace("：", " ").replace(":", " ").split():
            try:
                value = float(token)
                if 0.0 <= value <= 1.0:
                    return value
            except Exception:
                continue
        return 0.0

    @staticmethod
    def _avg(values: list[float]) -> float:
        if not values:
            return 0.0
        return round(float(statistics.mean(values)), 4)
