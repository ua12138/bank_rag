from __future__ import annotations

import json
import re
from collections import Counter

import jieba

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient, SiliconFlowError


RULE_KEYWORDS = [
    "数据库",
    "连接池",
    "告警",
    "超时",
    "主备切换",
    "回滚",
    "线程池",
    "网关",
    "认证服务",
    "交易系统",
    "核心账务",
]


def _extract_rule_keywords(text: str) -> list[str]:
    hits: list[str] = []
    lowered = text.lower()

    # 捕获告警码、错误码、系统代号等强语义词。
    for token in re.findall(r"[A-Z]{2,}[A-Z0-9_\-]{1,}|[A-Z]{1,}\d{2,}", text):
        if token not in hits:
            hits.append(token)

    for token in RULE_KEYWORDS:
        if token in text and token not in hits:
            hits.append(token)

    # 兜底提取高频中文词，增强没有显式告警码的运维文本覆盖率。
    words = [w.strip() for w in jieba.cut(lowered) if len(w.strip()) >= 2]
    for word, _ in Counter(words).most_common(20):
        if re.fullmatch(r"[\u4e00-\u9fff0-9a-zA-Z_\-]+", word) and word not in hits:
            hits.append(word)

    return hits[: settings.keyword_model_max_terms]


def _extract_model_keywords(text: str) -> list[str]:
    if not settings.keyword_model_enabled:
        return []

    client = SiliconFlowClient()
    prompt = (
        "你是运维文档关键词抽取器。"
        "请从输入文本中抽取最关键的关键词列表，返回 JSON 数组字符串。"
        "关键词优先包括：系统名、告警码、错误码、组件名、库表名、核心动作。"
        f"最多返回 {settings.keyword_model_max_terms} 个词。"
    )
    snippet = text[:2000]
    try:
        raw = client.chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": snippet},
            ],
            model=settings.keyword_model_name,
            temperature=0.0,
            max_tokens=200,
        )
    except SiliconFlowError:
        return []

    raw = raw.strip()
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if str(x).strip()][: settings.keyword_model_max_terms]
    except Exception:
        pass
    return []


def extract_keywords(text: str) -> list[str]:
    rule_terms = _extract_rule_keywords(text)
    model_terms = _extract_model_keywords(text)
    merged: list[str] = []
    for term in rule_terms + model_terms:
        if term and term not in merged:
            merged.append(term)
    return merged[: settings.keyword_model_max_terms]


def extract_chunk_keywords(chunks: list[str]) -> list[list[str]]:
    return [extract_keywords(chunk) for chunk in chunks]
