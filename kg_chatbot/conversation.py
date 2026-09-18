"""
In-memory per-conversation_id state, tracking which concepts have already
been surfaced (as the central concept of a prior answer in this
conversation) so latent knowledge-gap detection doesn't re-flag concepts
the user has already engaged with.

NOTE: process-local, in-memory only — resets on server restart and does
not survive multiple backend processes. That's fine for a single-instance
dev/demo deployment; swap `ConversationStore` for a real store (Redis, DB)
if this needs to survive restarts or scale horizontally.
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Set


@dataclass
class ConversationState:
    concepts_known: Set[str] = field(default_factory=set)

    def knows(self, concept_id: str) -> bool:
        return concept_id in self.concepts_known

    def mark_known(self, concept_id: str) -> None:
        self.concepts_known.add(concept_id)


class ConversationStore:
    def __init__(self):
        self._lock = Lock()
        self._conversations: Dict[str, ConversationState] = {}

    def get(self, conversation_id: str) -> ConversationState:
        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = ConversationState()
            return self._conversations[conversation_id]
