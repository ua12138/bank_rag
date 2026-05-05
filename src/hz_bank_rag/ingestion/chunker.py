from __future__ import annotations

import re
from typing import Literal

from langchain_text_splitters import RecursiveCharacterTextSplitter

ChunkStrategy = Literal["semantic", "recursive"]


class Chunker:
    """文档切分器。

    1. semantic 适合结构较强的运维手册。
    2. recursive 适合通用场景，稳定性更好。
    """

    def __init__(self, chunk_size: int = 450, overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", "。", "；", "，", " ", ""],
            keep_separator=True,
        )

    def split(self, text: str, strategy: ChunkStrategy = "recursive") -> list[str]:
        if strategy == "semantic":
            return self.semantic_chunk(text)
        return self.recursive_chunk(text)

    def recursive_chunk(self, text: str) -> list[str]:
        # 递归切分会优先按较大的语义边界拆分，不够时再继续细分。
        return [chunk.strip() for chunk in self.recursive_splitter.split_text(text) if chunk.strip()]

    def semantic_chunk(self, text: str) -> list[str]:
        # 先按标题和空行切段，尽量保留原始文档结构。
        blocks = [block.strip() for block in re.split(r"\n(?=#{1,6}\s)|\n\n", text) if block.strip()]
        chunks: list[str] = []
        current = ""
        for block in blocks:
            candidate = f"{current}\n{block}".strip() if current else block
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(block) <= self.chunk_size:
                current = block
                continue

            # 单段过长时退化为滑动窗口，避免直接截断关键信息。
            start = 0
            while start < len(block):
                end = min(start + self.chunk_size, len(block))
                chunks.append(block[start:end])
                if end >= len(block):
                    break
                start = max(end - self.overlap, 0)
            current = ""

        if current:
            chunks.append(current)
        return chunks


def semantic_chunk(text: str, chunk_size: int = 450, overlap: int = 80) -> list[str]:
    return Chunker(chunk_size=chunk_size, overlap=overlap).semantic_chunk(text)
