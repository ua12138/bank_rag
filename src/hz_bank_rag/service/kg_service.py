from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass


@dataclass
class KGNode:
    node_id: str
    label: str
    freq: int


@dataclass
class KGEdge:
    source: str
    target: str
    relation: str
    weight: int


class KnowledgeGraphService:
    """Lightweight in-memory KG built from chunk text."""

    def __init__(self) -> None:
        self._graph: dict[str, dict] = {}

    @staticmethod
    def _extract_entities(text: str) -> list[str]:
        candidates = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9_\-]{2,}", text or "")
        stop = {"this", "that", "with", "from", "have", "will", "the", "and", "for", "are"}
        out: list[str] = []
        for c in candidates:
            token = c.strip()
            if not token:
                continue
            if token.lower() in stop:
                continue
            if token not in out:
                out.append(token)
        return out[:20]

    def rebuild(self, kb_id: str, chunks: list[dict]) -> dict:
        node_freq: dict[str, int] = {}
        edge_freq: dict[tuple[str, str], int] = {}
        for chunk in chunks:
            ents = self._extract_entities(chunk.get("text", ""))
            for ent in ents:
                node_freq[ent] = node_freq.get(ent, 0) + 1
            for i in range(len(ents)):
                for j in range(i + 1, len(ents)):
                    a, b = sorted((ents[i], ents[j]))
                    edge_freq[(a, b)] = edge_freq.get((a, b), 0) + 1

        nodes = [{"id": k, "label": k, "freq": v} for k, v in node_freq.items()]
        edges = [{"source": a, "target": b, "relation": "co_occurrence", "weight": w} for (a, b), w in edge_freq.items()]

        adj: dict[str, set[str]] = {}
        for e in edges:
            adj.setdefault(e["source"], set()).add(e["target"])
            adj.setdefault(e["target"], set()).add(e["source"])

        self._graph[kb_id] = {
            "nodes": nodes,
            "edges": edges,
            "adj": {k: sorted(v) for k, v in adj.items()},
        }
        return {"kb_id": kb_id, "nodes": len(nodes), "edges": len(edges)}

    def entities_search(self, kb_id: str, keyword: str, limit: int = 20) -> list[dict]:
        g = self._graph.get(kb_id, {})
        nodes = g.get("nodes", [])
        key = (keyword or "").lower()
        matched = [n for n in nodes if key in n["label"].lower()]
        matched.sort(key=lambda x: x.get("freq", 0), reverse=True)
        return matched[: max(1, min(limit, 200))]

    def subgraph(self, kb_id: str, entity: str, hop: int = 2) -> dict:
        g = self._graph.get(kb_id, {})
        adj = g.get("adj", {})
        if entity not in adj:
            return {"nodes": [], "edges": []}
        q = deque([(entity, 0)])
        seen = {entity}
        while q:
            cur, d = q.popleft()
            if d >= hop:
                continue
            for nxt in adj.get(cur, []):
                if nxt in seen:
                    continue
                seen.add(nxt)
                q.append((nxt, d + 1))
        nodes = [n for n in g.get("nodes", []) if n["id"] in seen]
        edge_set = set()
        edges = []
        for e in g.get("edges", []):
            if e["source"] in seen and e["target"] in seen:
                k = (e["source"], e["target"])
                if k not in edge_set:
                    edge_set.add(k)
                    edges.append(e)
        return {"nodes": nodes, "edges": edges}

    def shortest_path(self, kb_id: str, source: str, target: str) -> dict:
        g = self._graph.get(kb_id, {})
        adj = g.get("adj", {})
        if source not in adj or target not in adj:
            return {"path": [], "hops": -1}
        q = deque([source])
        prev: dict[str, str | None] = {source: None}
        while q:
            cur = q.popleft()
            if cur == target:
                break
            for nxt in adj.get(cur, []):
                if nxt in prev:
                    continue
                prev[nxt] = cur
                q.append(nxt)
        if target not in prev:
            return {"path": [], "hops": -1}
        path = []
        p = target
        while p is not None:
            path.append(p)
            p = prev[p]
        path.reverse()
        return {"path": path, "hops": max(0, len(path) - 1)}

