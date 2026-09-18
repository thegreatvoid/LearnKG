"""
Latent knowledge-gap detection: for each prerequisite/related concept in
the localized subgraph, infers whether the user likely already understands
it (based on conversation history) and, if not, assigns a confidence level.
Per project spec sections 4/19: an inferred gap is always phrased as
"possible", never as a confirmed fact about the user.
"""

from typing import List

from .conversation import ConversationState
from .schemas import ConceptRef, KnowledgeGap
from .subgraph_builder import RankedConcept

MAX_GAPS = 4
# A "related" concept only becomes a gap candidate if it scores highly
# enough to plausibly be assumed background knowledge — most related
# concepts (an application/example) aren't things you need beforehand.
RELATED_GAP_THRESHOLD = 0.5


def detect_knowledge_gaps(
    prerequisites: List[RankedConcept],
    related: List[RankedConcept],
    conversation: ConversationState,
) -> List[KnowledgeGap]:
    candidates = list(prerequisites) + [c for c in related if c.score >= RELATED_GAP_THRESHOLD]

    gaps: List[KnowledgeGap] = []
    for c in candidates:
        if conversation.knows(c.node.id):
            continue  # already discussed/surfaced in this conversation

        confidence_score = c.score + (0.2 if c.direction == "prerequisite" else 0.0)
        if confidence_score >= 0.65:
            confidence = "High"
        elif confidence_score >= 0.4:
            confidence = "Medium"
        else:
            confidence = "Low"

        reason = (
            "This concept is a prerequisite for understanding what you asked about."
            if c.direction == "prerequisite"
            else "This concept is closely related and may be assumed knowledge for the answer."
        )

        gaps.append(KnowledgeGap(
            concept=ConceptRef(id=c.node.id, label=c.node.label),
            reason=reason,
            confidence=confidence,
        ))

    order = {"High": 0, "Medium": 1, "Low": 2}
    gaps.sort(key=lambda g: order[g.confidence])
    return gaps[:MAX_GAPS]
