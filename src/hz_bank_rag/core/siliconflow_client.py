from __future__ import annotations

"""SiliconFlow 客户端：封装 embeddings/rerank/chat/vision 调用。"""

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from hz_bank_rag.core.config import settings


class SiliconFlowError(RuntimeError):
    """SiliconFlow API 错误。"""


class SiliconFlowClient:
    """轻量 HTTP 客户端（兼容 OpenAI 风格接口）。"""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.siliconflow_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.siliconflow_api_key
        self.timeout_seconds = timeout_seconds or settings.siliconflow_timeout_seconds

    def _headers(self) -> dict[str, str]:
        """构建鉴权请求头。"""
        if not self.api_key:
            raise SiliconFlowError("Missing SiliconFlow API key: set HZ_RAG_SILICONFLOW_API_KEY")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """执行 POST 请求并统一处理 HTTP/JSON 异常。"""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(url, headers=self._headers(), json=payload)
        except Exception as exc:
            raise SiliconFlowError(f"Request to SiliconFlow failed: {exc}") from exc

        if response.status_code >= 400:
            raise SiliconFlowError(f"SiliconFlow error status={response.status_code}, body={response.text}")

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise SiliconFlowError(f"SiliconFlow returned non-JSON body: {response.text[:400]}") from exc

    def embeddings(self, texts: list[str], model: str) -> list[list[float]]:
        """批量生成文本向量。"""
        if not texts:
            return []

        batch_size = max(1, settings.siliconflow_embedding_batch_size)
        vectors: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            body = {"model": model, "input": batch, "encoding_format": "float"}
            data = self._post("/embeddings", body)
            items = data.get("data", [])
            if not items:
                raise SiliconFlowError("Embedding response missing data")

            items = sorted(items, key=lambda x: x.get("index", 0))
            for item in items:
                emb = item.get("embedding")
                if not isinstance(emb, list) or not emb:
                    raise SiliconFlowError("Embedding item is invalid")
                vectors.append([float(v) for v in emb])

        if len(vectors) != len(texts):
            raise SiliconFlowError(f"Embedding count mismatch: expect={len(texts)}, got={len(vectors)}")
        return vectors

    def rerank(self, query: str, documents: list[str], model: str, top_n: int) -> list[dict[str, Any]]:
        """对候选文档进行相关性重排。"""
        body = {"model": model, "query": query, "documents": documents, "top_n": top_n}
        data = self._post("/rerank", body)
        results = data.get("results") if data.get("results") is not None else data.get("data", [])
        if not isinstance(results, list):
            raise SiliconFlowError("Rerank response is invalid")

        normalized: list[dict[str, Any]] = []
        for row in results:
            idx = row.get("index")
            score = row.get("relevance_score", row.get("score", 0.0))
            if idx is None:
                continue
            normalized.append({"index": int(idx), "score": float(score)})
        return normalized

    def chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """普通（非流式）对话调用。"""
        body = {
            "model": model,
            "messages": messages,
            "temperature": settings.siliconflow_chat_temperature if temperature is None else temperature,
            "max_tokens": settings.siliconflow_chat_max_tokens if max_tokens is None else max_tokens,
        }
        data = self._post("/chat/completions", body)
        choices = data.get("choices", [])
        if not choices:
            raise SiliconFlowError("Chat response missing choices")
        content = choices[0].get("message", {}).get("content", "")
        if not isinstance(content, str):
            raise SiliconFlowError("Chat response content is invalid")
        return content.strip()

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """流式对话调用，逐 token 输出。"""
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": settings.siliconflow_chat_temperature if temperature is None else temperature,
            "max_tokens": settings.siliconflow_chat_max_tokens if max_tokens is None else max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                with client.stream("POST", url, headers=self._headers(), json=body) as response:
                    if response.status_code >= 400:
                        raise SiliconFlowError(
                            f"SiliconFlow streaming error status={response.status_code}, body={response.text}"
                        )
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if isinstance(line, bytes):
                            line = line.decode("utf-8", errors="ignore")
                        if not line.startswith("data:"):
                            continue
                        payload = line[len("data:") :].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            obj = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
        except SiliconFlowError:
            raise
        except Exception as exc:
            raise SiliconFlowError(f"Streaming request to SiliconFlow failed: {exc}") from exc

    def vision_ocr(self, image_path: str, prompt: str | None = None) -> str:
        """视觉 OCR：把图片转 base64 后调用多模态模型识别文字。"""
        path = Path(image_path)
        mime = _guess_mime(path.suffix.lower())
        image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        image_url = f"data:{mime};base64,{image_b64}"
        text_prompt = prompt or "Extract all readable text from this image."

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        return self.chat(messages=messages, model=settings.siliconflow_vision_model, temperature=0.0, max_tokens=1024)


def _guess_mime(suffix: str) -> str:
    """按文件后缀推断 MIME 类型。"""
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".bmp":
        return "image/bmp"
    if suffix in {".tif", ".tiff"}:
        return "image/tiff"
    return "application/octet-stream"
