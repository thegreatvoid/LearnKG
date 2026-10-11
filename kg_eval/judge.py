"""LLM judge (Ollama) used for both support labelling (A) and educational-importance ratings (B).

Each judgement is conditioned on the top-k retrieved textbook passages for that edge.
Results are appended to a JSONL cache keyed by (task, edge, rep) so reruns resume.
"""

import json
import os
from pathlib import Path

import requests

from .data import RELATION_SEMANTICS

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_JUDGE_MODEL", "qwen2.5:7b-instruct")
NUM_CTX = 4096
TOP_K = 8  # retrieved textbook passages per edge; the full book (~6k tokens) is too slow on CPU
SUPPORT_LABELS = ["Supported", "Contradicted", "Insufficient evidence", "Ambiguous"]

SUPPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": SUPPORT_LABELS},
        "quote": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["label", "quote", "rationale"],
    "additionalProperties": False,
}
RATING_SCHEMA = {
    "type": "object",
    "properties": {"rating": {"type": "integer", "enum": [1, 2, 3, 4, 5]}, "rationale": {"type": "string"}},
    "required": ["rating", "rationale"],
    "additionalProperties": False,
}

SUPPORT_TASK = """You are auditing a knowledge-graph triple against the textbook excerpts.
Judge ONLY from the textbook excerpts; ignore your outside knowledge when the textbook is silent.
Relation semantics: {semantics}.
Labels:
- Supported: the textbook states or directly entails the triple, including the stated direction.
- Contradicted: the textbook states something incompatible (including the reverse direction for a Prerequisite).
- Insufficient evidence: the textbook neither supports nor contradicts it.
- Ambiguous: the triple is vague or the textbook admits several readings.
Give the shortest verbatim textbook quote that decides it (empty string if none)."""

RATING_TASK = """You are rating how educationally important the following relation is for building a localized
concept graph around a learner's knowledge gap (i.e., would a tutor following this textbook need this link to
explain the target concept, or to decide what to review first?).
Scale: 1 = trivial or misleading link, 2 = marginal, 3 = useful, 4 = important, 5 = essential.
Judge from the textbook excerpts. Rate importance, not factual confidence."""


class Judge:
    """Ollama-backed judge. The model name is part of every cache key so judgements from different judges
    never mix; temperature 0 and a JSON-schema `format` keep outputs deterministic and parseable."""

    def __init__(self, source_text: str, cache_path: Path, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        self.model, self.host = model, host.rstrip("/")
        from sentence_transformers import SentenceTransformer
        from .data import split_sentences
        self.sentences = split_sentences(source_text)
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.sent_emb = self.embedder.encode(self.sentences, normalize_embeddings=True)
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.cache[r["key"]] = r
        tags = requests.get(f"{self.host}/api/tags", timeout=5).json().get("models", [])
        if not any(m["name"] == model or m["name"].split(":")[0] == model for m in tags):
            raise SystemExit(f"Ollama model {model!r} not installed. Run `ollama pull {model}` "
                             f"or set OLLAMA_JUDGE_MODEL. Installed: {[m['name'] for m in tags]}")

    def _context(self, edge) -> str:
        """Top-k textbook sentences closest to the edge, in textbook order, as the admissible source."""
        q = self.embedder.encode([f'{edge["source_name"]} {edge["target_name"]} {edge["evidence"]}'],
                                 normalize_embeddings=True)[0]
        idx = sorted((self.sent_emb @ q).argsort()[::-1][:TOP_K])
        return "TEXTBOOK EXCERPTS (the only admissible source):\n" + "\n".join(f"- {self.sentences[i]}" for i in idx)

    def _call(self, prompt: str, schema: dict, edge) -> dict:
        last = None
        for _ in range(3):  # a stuck/looping generation times out; retry, then give up on this edge
            try:
                r = requests.post(f"{self.host}/api/chat", timeout=240, json={
                    "model": self.model, "stream": False, "format": schema,
                    "options": {"temperature": 0, "num_ctx": NUM_CTX, "num_predict": 400},
                    "messages": [{"role": "system", "content": self._context(edge)},
                                 {"role": "user", "content": prompt}],
                })
                r.raise_for_status()
                return json.loads(r.json()["message"]["content"])
            except (requests.exceptions.RequestException, json.JSONDecodeError) as exc:
                last = exc
        raise RuntimeError(f"judge failed after retries: {last}")


    def _cached(self, key: str, fn) -> dict:
        if key not in self.cache:
            rec = {"key": key, **fn()}
            self.cache[key] = rec
            with self.cache_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        return self.cache[key]

    def support(self, edge) -> dict:
        prompt = (
            SUPPORT_TASK.format(semantics=RELATION_SEMANTICS.get(edge["relation_type"], ""))
            + f'\n\nTriple: {edge["source_name"]} --[{edge["relation_type"]}]--> {edge["target_name"]}'
            + f'\nExtraction evidence sentence: "{edge["evidence"]}"'
        )
        return self._cached(f'support:{self.model}:{edge["relation_id"]}', lambda: self._call(prompt, SUPPORT_SCHEMA, edge))

    def rate(self, edge, rep: int = 0) -> dict:
        # Deliberately blind to the edge weight and to the support label.
        prompt = (
            RATING_TASK
            + f'\n\nRelation ({edge["relation_type"]}: {RELATION_SEMANTICS.get(edge["relation_type"], "")}):'
            + f'\n{edge["source_name"]} --> {edge["target_name"]}'
            + f'\nEvidence sentence: "{edge["evidence"]}"'
        )
        return self._cached(f'rate:{self.model}:{edge["relation_id"]}:{rep}', lambda: self._call(prompt, RATING_SCHEMA, edge))
