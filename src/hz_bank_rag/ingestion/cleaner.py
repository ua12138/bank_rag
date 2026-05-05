from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """对原始文本做轻量清洗。"""

    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
