from __future__ import annotations

import pathlib
import tempfile
from functools import lru_cache
from typing import Final

from hz_bank_rag.core.config import settings
from hz_bank_rag.core.siliconflow_client import SiliconFlowClient

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # pragma: no cover
    RapidOCR = None

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover
    pytesseract = None
    Image = None

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
except Exception:  # pragma: no cover
    torch = None
    CLIPModel = None
    CLIPProcessor = None


OCR_LANG: Final[str] = "chi_sim+eng"


def image_to_text(image_path: str) -> str:
    """Extract text from image by multi-stage OCR pipeline."""

    path = pathlib.Path(image_path)
    blocks: list[str] = []

    # Stage 1: local OCR with RapidOCR (better Chinese support without tesseract binary).
    rapid_text = _ocr_image_rapid(str(path))
    if rapid_text:
        blocks.append(f"[image-ocr-rapid] file={path.name}\n{rapid_text}")

    # Stage 2: local OCR with pytesseract as fallback.
    local_text = _ocr_image_local(str(path))
    if local_text:
        blocks.append(f"[image-ocr-local] file={path.name}\n{local_text}")

    # Stage 3: vision model with table-first prompt to improve table extraction.
    table_text = _ocr_table_with_vision_model(str(path))
    if table_text:
        blocks.append(f"[image-table-vlm] file={path.name}\n{table_text}")

    # Stage 4: vision model general OCR fallback.
    general_text = _ocr_general_with_vision_model(str(path))
    if general_text:
        blocks.append(f"[image-ocr-vlm] file={path.name}\n{general_text}")

    if not blocks:
        blocks.append(f"[image-caption] file={path.name}, no readable text.")

    # Stage 5: CLIP embedding summary for multimodal semantic retrieval extension.
    clip_info = _clip_embedding_summary(str(path))
    if clip_info:
        blocks.append(clip_info)

    return "\n".join(blocks)


def image_bytes_to_text(image_bytes: bytes, suffix: str = ".png") -> str:
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(image_bytes)
        tmp.flush()
        return image_to_text(tmp.name)


def clip_embedding_hint() -> str:
    return "CLIP image embedding is enabled for multimodal retrieval extension."


def _ocr_image_rapid(image_path: str) -> str:
    if RapidOCR is None:
        return ""
    try:
        engine = _get_rapid_ocr_runtime()
        result, _ = engine(image_path)
        if not result:
            return ""
        lines = []
        for row in result:
            if len(row) >= 2 and row[1]:
                lines.append(str(row[1]).strip())
        return "\n".join([line for line in lines if line]).strip()
    except Exception:
        return ""


def _ocr_image_local(image_path: str) -> str:
    if pytesseract is None or Image is None:
        return ""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=OCR_LANG)
        return (text or "").strip()
    except Exception:
        return ""


def _ocr_table_with_vision_model(image_path: str) -> str:
    prompt = (
        "请优先识别图片中的表格。"
        "如果存在表格，请输出标准 Markdown 表格；"
        "如果没有表格，则返回空字符串。"
    )
    try:
        client = SiliconFlowClient()
        text = client.vision_ocr(image_path=image_path, prompt=prompt)
        out = (text or "").strip()
        if "|" in out and "---" in out:
            return out
        return ""
    except Exception:
        return ""


def _ocr_general_with_vision_model(image_path: str) -> str:
    prompt = "请提取图片中的所有可见文字，按原有结构尽量输出，避免遗漏数字、字段名和关键术语。"
    try:
        client = SiliconFlowClient()
        text = client.vision_ocr(image_path=image_path, prompt=prompt)
        return (text or "").strip()
    except Exception:
        return ""


def _clip_embedding_summary(image_path: str) -> str:
    if not settings.enable_clip:
        return "[image-clip] disabled"
    try:
        vec = _clip_image_embedding(image_path)
        if vec is None:
            return "[image-clip] unavailable"
        head = ", ".join([f"{v:.4f}" for v in vec[:8]])
        return f"[image-clip] dim={len(vec)}, head=[{head}]"
    except Exception:
        return "[image-clip] unavailable"


def _clip_image_embedding(image_path: str) -> list[float] | None:
    if torch is None or CLIPModel is None or CLIPProcessor is None or Image is None:
        return None

    processor, model = _get_clip_runtime()
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
        features = features / features.norm(p=2, dim=-1, keepdim=True)
    return [float(v) for v in features[0].detach().cpu().tolist()]


@lru_cache(maxsize=1)
def _get_clip_runtime():
    processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
    model = CLIPModel.from_pretrained(settings.clip_model_name)
    model.eval()
    return processor, model


@lru_cache(maxsize=1)
def _get_rapid_ocr_runtime():
    return RapidOCR()
