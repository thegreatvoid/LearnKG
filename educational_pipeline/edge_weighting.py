"""
Relation-Aware Edge-Weight Calculation and Factor Calibration.

Decouples four distinct edge fields:
  1. extraction_confidence: Confidence score of the extractor (e.g. LLM or classifier).
  2. evidence_support: Textual grounding and verification support.
  3. relation_weight: Final educational relevance weight in [0, 1] for graph traversal.
  4. verification_status: Result of independent verification (e.g. VERIFIED_SUPPORTED).

Maintains established baselines:
  - unweighted: Constant 1.0 weight for all edges
  - ahp: Original Saaty AHP formula (0.52 S + 0.24 C + 0.09 P + 0.15 E)
  - cooc_only: Co-occurrence only (1.0 C)
  - cooc_struct_a0.8: Cross-validated structural (0.8 C + 0.2 E)
  - relation_aware: Relation-tailored weighting:
      * Similarity:  0.60 S + 0.40 C
      * Part-of:     0.50 C + 0.30 E + 0.20 S
      * Application: 0.50 C + 0.30 E + 0.20 S
      * Extension:   0.40 C + 0.30 E + 0.30 P
      * Prerequisite: AHP baseline or 0.8 C + 0.2 E
"""

from typing import Any, Dict, Optional
from .normalizer import NormalizedConcept


RELATION_AWARE_COEFFICIENTS: Dict[str, Dict[str, float]] = {
    "Prerequisite": {
        "semantic_similarity": 0.52,
        "cooccurrence": 0.24,
        "chapter_proximity": 0.09,
        "educational_context": 0.15,
    },
    "Similarity": {
        "semantic_similarity": 0.60,
        "cooccurrence": 0.40,
        "chapter_proximity": 0.00,
        "educational_context": 0.00,
    },
    "Part-of": {
        "semantic_similarity": 0.20,
        "cooccurrence": 0.50,
        "chapter_proximity": 0.00,
        "educational_context": 0.30,
    },
    "Application": {
        "semantic_similarity": 0.20,
        "cooccurrence": 0.50,
        "chapter_proximity": 0.00,
        "educational_context": 0.30,
    },
    "Extension": {
        "semantic_similarity": 0.00,
        "cooccurrence": 0.40,
        "chapter_proximity": 0.30,
        "educational_context": 0.30,
    },
}


def calculate_evidence_support(
    cooccurrence_count: int,
    evidence_sentences_count: int,
    is_verified: bool,
    quote_length: int = 0,
) -> float:
    """
    Computes evidence_support in [0, 1].
    Reflects the strength of textual evidence independent of model confidence.
    """
    # Base from co-occurrence and distinct evidence sentences
    base_cooc = min(1.0, cooccurrence_count / 3.0)
    base_ev = min(1.0, evidence_sentences_count / 2.0)
    support = 0.5 * base_cooc + 0.5 * base_ev

    # Bonus for verified verbatim quote
    if is_verified:
        support = min(1.0, support + 0.2)
    else:
        support = support * 0.5

    return round(max(0.0, min(1.0, support)), 4)


def compute_relation_weight(
    factors: Dict[str, float],
    relation_type: str,
    scheme: str = "ahp",
) -> float:
    """
    Computes relation_weight in [0, 1] according to the selected scheme.
    """
    if scheme == "unweighted":
        return 1.0

    if scheme == "cooc_only":
        return round(max(0.0, min(1.0, factors.get("cooccurrence", 0.0))), 4)

    if scheme == "cooc_struct_a0.8":
        c = factors.get("cooccurrence", 0.0)
        e = factors.get("educational_context", 0.0)
        return round(max(0.0, min(1.0, 0.8 * c + 0.2 * e)), 4)

    if scheme == "relation_aware":
        weights = RELATION_AWARE_COEFFICIENTS.get(
            relation_type,
            RELATION_AWARE_COEFFICIENTS["Prerequisite"],
        )
        score = sum(weights[k] * factors.get(k, 0.0) for k in weights)
        return round(max(0.0, min(1.0, score)), 4)

    # Default to AHP formula
    s = factors.get("semantic_similarity", 0.0)
    c = factors.get("cooccurrence", 0.0)
    p = factors.get("chapter_proximity", 0.0)
    e = factors.get("educational_context", 0.0)
    ahp_score = 0.52 * s + 0.24 * c + 0.09 * p + 0.15 * e
    return round(max(0.0, min(1.0, ahp_score)), 4)
