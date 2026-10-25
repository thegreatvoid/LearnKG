"""Ollama chat backend: JSON-schema output, retries, explicit counters. Never fails silently."""

import json
import os
from collections import Counter
from typing import Optional

try:
    import requests
    RequestException = requests.exceptions.RequestException
except ImportError:
    import httpx
    requests = httpx
    RequestException = (httpx.RequestError, httpx.HTTPStatusError)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class BackendError(RuntimeError):
    pass


class OllamaBackend:
    def __init__(self, model: str, host: str = OLLAMA_HOST, num_ctx: int = 4096, timeout: int = 300, retries: int = 3):
        self.model, self.host = model, host.rstrip("/")
        self.num_ctx, self.timeout, self.retries = num_ctx, timeout, retries
        self.counters = Counter()
        tags = requests.get(f"{self.host}/api/tags", timeout=10).json().get("models", [])
        names = [m["name"] for m in tags]
        if not any(n == model or n.split(":")[0] == model for n in names):
            raise BackendError(f"model {model!r} is not installed on {self.host}; installed: {names}")

    def chat_json(self, system: str, user: str, schema: dict, temperature: float = 0.0, seed: Optional[int] = None) -> dict:
        """One structured completion. Raises BackendError after `retries` failures; every outcome is counted."""
        options = {"temperature": temperature, "num_ctx": self.num_ctx, "num_predict": 600}
        if seed is not None:
            options["seed"] = seed
        last = None
        for _ in range(self.retries):
            self.counters["llm_calls"] += 1
            try:
                r = requests.post(f"{self.host}/api/chat", timeout=self.timeout, json={
                    "model": self.model, "stream": False, "format": schema, "options": options,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                })
                r.raise_for_status()
                out = json.loads(r.json()["message"]["content"])
                self.counters["llm_ok"] += 1
                return out
            except (RequestException, json.JSONDecodeError, KeyError) as exc:
                self.counters["llm_fail"] += 1
                last = exc
        self.counters["llm_gave_up"] += 1
        raise BackendError(f"{self.model}: failed after {self.retries} attempts: {last}")
