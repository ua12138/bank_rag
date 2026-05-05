from __future__ import annotations

"""文本清洗模块：对解析后的原始文本做轻量标准化。"""

import re


def clean_text(text: str) -> str:
    """清洗文本。

    处理内容:
    - 全角空格替换为半角空格
    - 连续空白压缩
    - 过多空行压缩到两行
    """
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
