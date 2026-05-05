from __future__ import annotations

from pathlib import Path

from hz_bank_rag.core.config import settings
from hz_bank_rag.examples.seed_demo import seed_demo_data


class DummyRepo:
    def __init__(self) -> None:
        self.ingested_file_paths: list[str] = []

    def bulk_ingest(self, kb_id: str, file_paths: list[str], chunk_strategy: str | None = None) -> dict:
        self.ingested_file_paths = file_paths
        return {
            "kb_id": kb_id,
            "documents": [{"file_path": p} for p in file_paths],
            "count": len(file_paths),
        }


def test_seed_excludes_eval_samples(tmp_path: Path) -> None:
    demo = tmp_path / "demo_kb"
    eval_dir = demo / "eval_samples"
    demo.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    (demo / "ops_manual.md").write_text("hello", encoding="utf-8")
    (demo / "ragas_dataset_samples.json").write_text("[]", encoding="utf-8")
    (eval_dir / "tickets.md").write_text("should be excluded", encoding="utf-8")

    settings.chunk_strategy = "recursive"
    repo = DummyRepo()
    result = seed_demo_data(repo=repo, kb_id="kb1", data_dir=demo)

    assert result["count"] == 1
    assert any("ragas_dataset_samples.json" in x for x in result["skipped_files"])
    assert all("eval_samples" not in p for p in repo.ingested_file_paths)
    assert repo.ingested_file_paths[0].endswith("ops_manual.md")
