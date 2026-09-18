"""
Generates the natural-language answer text. Two implementations:

  - TemplateAnswerGenerator: composes the answer deterministically from the
    central concept's definition plus its strongest relation evidence —
    fully offline, always available, genuinely grounded in source text
    (no hallucination risk since nothing is invented).
  - OllamaAnswerGenerator: asks a local Ollama model to phrase a more
    natural answer from the same grounded context. get_answer_generator()
    probes the server once at startup; kg_chatbot/main.py also wraps each
    per-request call so a mid-session Ollama failure falls back to the
    template generator instead of erroring the request.
"""

import os
from typing import Callable, List, Optional, Protocol

from .kg_adapter import KGEdge, KGNode


class AnswerGenerator(Protocol):
    name: str

    def generate(
        self,
        question: str,
        center: KGNode,
        edges: List[KGEdge],
        kg_lookup: Callable[[str], Optional[KGNode]],
    ) -> str:
        ...


class TemplateAnswerGenerator:
    name = "template"

    def generate(self, question, center, edges, kg_lookup) -> str:
        parts = []
        if center.description:
            parts.append(center.description.strip())

        best_edge = max(edges, key=lambda e: e.weight, default=None)
        if best_edge and best_edge.evidence:
            evidence = best_edge.evidence.strip()
            if evidence and evidence not in (center.description or ""):
                parts.append(evidence)

        if not parts:
            return (
                f"{center.label} is a concept in this knowledge graph, but no "
                "grounded definition was extracted for it yet."
            )
        return " ".join(parts)


class OllamaAnswerGenerator:
    name = "ollama"

    def __init__(self, model: str, base_url: Optional[str] = None, timeout: float = 12.0):
        self.model = model
        self.base_url = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout

    def generate(self, question, center, edges, kg_lookup) -> str:
        import requests

        context_lines = [f"Concept: {center.label}", f"Definition: {center.description}"]
        for e in sorted(edges, key=lambda e: -e.weight)[:5]:
            other_id = e.target if e.source == center.id else e.source
            other = kg_lookup(other_id)
            if other:
                context_lines.append(f"- {e.relation_type} relation with '{other.label}': {e.evidence}")

        prompt = (
            "You are a concise teaching assistant. Using ONLY the knowledge-graph "
            "context below, answer the user's question in 2-4 sentences. Do not "
            "invent facts not supported by the context.\n\n"
            f"Context:\n{chr(10).join(context_lines)}\n\n"
            f"Question: {question}\n\nAnswer:"
        )

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        text = (resp.json().get("response") or "").strip()
        if not text:
            raise ValueError("Empty response from Ollama")
        return text


def get_answer_generator() -> AnswerGenerator:
    """Selects Ollama if OLLAMA_MODEL is set, the server is reachable, and
    that model is actually pulled — else falls back to the template
    generator so the app always works end-to-end offline."""
    model = os.environ.get("OLLAMA_MODEL")
    if not model:
        return TemplateAnswerGenerator()

    base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import requests

        resp = requests.get(f"{base_url}/api/tags", timeout=2.0)
        resp.raise_for_status()
        available = {m["name"] for m in resp.json().get("models", [])}
        if model not in available and f"{model}:latest" not in available:
            print(
                f"[kg_chatbot] OLLAMA_MODEL={model!r} not found on {base_url} "
                f"(available: {sorted(available) or 'none'}); using template answers."
            )
            return TemplateAnswerGenerator()
        return OllamaAnswerGenerator(model=model, base_url=base_url)
    except Exception as exc:
        print(f"[kg_chatbot] Ollama unreachable at {base_url} ({exc}); using template answers.")
        return TemplateAnswerGenerator()
