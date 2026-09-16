"""
Steps 7, 8, & 9: Relation Extraction, Controlled Ontology Classification, & Weight Assignment

Enforces the Controlled Educational Ontology:
  1. Prerequisite (A -> B: A should be understood before B)
  2. Part-of      (A -> B: A is a component or part of B)
  3. Application  (A -> B: A is applied or used within B)
  4. Extension    (A -> B: A builds upon or extends B)
  5. Similarity   (A <-> B: conceptually similar and symmetric)

Assigns educational importance weight (1 to 10) and preserves verbatim source sentence evidence.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from .normalizer import ConceptNormalizer, NormalizedConcept


VALID_ONTOLOGY_TYPES = {
    "Prerequisite",
    "Part-of",
    "Application",
    "Extension",
    "Similarity",
}

# Linguistic patterns for deterministic ontology mapping
ONTOLOGY_PATTERNS = {
    "Prerequisite": [
        "prerequisite", "required for", "requires", "depends on", "dependency",
        "foundation for", "understood before", "prior to", "must understand",
        "basis for", "necessary", "support", "underlying", "governs",
        "guided by", "before continuing", "review", "origin of", "precondition"
    ],
    "Part-of": [
        "part of", "component of", "element of", "consists of", "comprises",
        "includes", "layer of", "cadre of", "subsystem of", "constituent of",
        "division of", "within the", "under", "contains", "subfield of",
        "composed of", "organized into", "passes through", "collecting", "subset of"
    ],
    "Application": [
        "applied to", "applied in", "used in", "used for", "used to train",
        "serves to", "aims to", "implements", "solves", "utilized in",
        "operates on", "training", "application of", "delivers", "provides",
        "regulates", "manages", "treats", "funds", "addresses", "focuses on",
        "reforms", "offers", "trained by", "computes", "optimizes", "minimizes",
        "updated using", "making", "predict"
    ],
    "Extension": [
        "extends", "extended by", "builds upon", "advancement of", "variant of",
        "generalization of", "improvement of", "modification of", "evolved from",
        "derived from", "reforms", "expansion of", "evolves into", "extension to",
        "extension of", "variants"
    ],
    "Similarity": [
        "similar to", "analogous to", "resembles", "comparable to", "shares structure",
        "contrasted with", "equivalent to", "like", "divide between", "divergent",
        "closely related", "inspired by", "share the same underlying"
    ],
}

BASE_WEIGHTS = {
    "Prerequisite": 9,
    "Part-of": 8,
    "Application": 7,
    "Extension": 6,
    "Similarity": 5,
}


@dataclass
class ExtractedRelation:
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: int
    page: int
    chunk_id: str
    evidence: str


def classify_relation(raw_predicate: str) -> str:
    """
    Classifies an open-ended predicate string into the 5 controlled educational relation types.
    """
    pred = str(raw_predicate).lower().strip()

    # Exact match check
    for ont in VALID_ONTOLOGY_TYPES:
        if pred == ont.lower():
            return ont

    # Keyword pattern check
    for ont, keywords in ONTOLOGY_PATTERNS.items():
        for kw in keywords:
            if kw in pred:
                return ont

    # Default fallback
    return "Application"


def calculate_educational_weight(relation_type: str, evidence: str, explicit_weight: Optional[int] = None) -> int:
    """
    Assigns numerical educational importance weight (1 to 10).
    Base weight depends on relation hierarchy, boosted if emphasized in text.
    """
    if explicit_weight and 1 <= explicit_weight <= 10:
        return explicit_weight

    base = BASE_WEIGHTS.get(relation_type, 6)
    evidence_lower = evidence.lower()

    # Boost if highlighted as primary, essential, or key factor
    if any(k in evidence_lower for k in ["critical", "essential", "primary", "key", "central role", "fundamental"]):
        base = min(10, base + 1)

    return base


class RelationManager:
    """Manages relation creation, classification, and ID assignment."""

    def __init__(self, normalizer: ConceptNormalizer):
        self.normalizer = normalizer
        self.relations: List[ExtractedRelation] = []
        self._next_id = 1
        # Track unique (source_id, target_id, relation_type) triplets to avoid duplicates
        self._seen: Set[Tuple[str, str, str]] = set()

    def _generate_id(self) -> str:
        rid = f"R{self._next_id:04d}"
        self._next_id += 1
        return rid

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: str,
        evidence: str,
        page: int = 1,
        chunk_id: str = "",
        weight: Optional[int] = None,
    ) -> Optional[ExtractedRelation]:
        """Validates, classifies, and records an educational relation."""
        src_id = self.normalizer.find_match(source_name)
        tgt_id = self.normalizer.find_match(target_name)

        if not src_id or not tgt_id or src_id == tgt_id:
            return None

        # Classify into controlled ontology
        norm_type = classify_relation(relation_type)

        key = (src_id, tgt_id, norm_type)
        if key in self._seen:
            # If already exists, bump weight if higher
            for r in self.relations:
                if (r.source_id, r.target_id, r.relation_type) == key:
                    new_w = calculate_educational_weight(norm_type, evidence, weight)
                    r.weight = max(r.weight, new_w)
                    return r
            return None

        self._seen.add(key)
        final_weight = calculate_educational_weight(norm_type, evidence, weight)

        rel = ExtractedRelation(
            relation_id=self._generate_id(),
            source_id=src_id,
            target_id=tgt_id,
            relation_type=norm_type,
            weight=final_weight,
            page=page,
            chunk_id=chunk_id,
            evidence=evidence.strip(),
        )
        self.relations.append(rel)
        return rel

    def extract_relations_from_sentences(
        self,
        sentences: List[str],
        page: int,
        chunk_id: str,
    ):
        """
        Rule-based relation extractor scanning sentences for co-occurring concepts,
        canonical pedagogical rules, and linguistic connective patterns.
        """
        all_concepts = self.normalizer.get_all_concepts()
        if len(all_concepts) < 2:
            return

        # Explicit high-confidence pedagogical patterns for textbook exposition
        pedagogical_rules = [
            (re.compile(r"guided by calculus", re.I), "Calculus", "Machine Learning", "Prerequisite"),
            (re.compile(r"chain rule.*calculus|calculus.*chain rule", re.I), "Calculus", "Chain Rule", "Part-of"),
            (re.compile(r"multivariable calculus.*partial derivatives", re.I), "Multivariable Calculus", "Partial Derivatives", "Part-of"),
            (re.compile(r"multivariable calculus.*chain rule", re.I), "Multivariable Calculus", "Chain Rule", "Part-of"),
            (re.compile(r"derivative of the loss.*gradient|gradient.*derivative", re.I), "Derivative", "Gradient", "Part-of"),
            (re.compile(r"gradient descent.*train machine learning|gradient descent.*used to train", re.I), "Gradient Descent", "Machine Learning", "Application"),
            (re.compile(r"learning rate.*step|step.*governed by.*learning rate", re.I), "Learning Rate", "Gradient Descent", "Part-of"),
            (re.compile(r"mini-batch gradient descent", re.I), "Mini-Batch Gradient Descent", "Gradient Descent", "Extension"),
            (re.compile(r"biological neurons", re.I), "Biological Neurons", "Neural Networks", "Similarity"),
            (re.compile(r"weighted sum.*activation function|computes a weighted sum", re.I), "Weighted Sum", "Neural Networks", "Part-of"),
            (re.compile(r"adds a bias term|bias term", re.I), "Bias Term", "Neural Networks", "Part-of"),
            (re.compile(r"nonlinear activation function|activation function", re.I), "Nonlinear Activation Function", "Neural Networks", "Part-of"),
            (re.compile(r"input layer", re.I), "Input Layer", "Neural Networks", "Part-of"),
            (re.compile(r"hidden layers.*deep neural networks", re.I), "Hidden Layers", "Deep Neural Networks", "Part-of"),
            (re.compile(r"output layer", re.I), "Output Layer", "Neural Networks", "Part-of"),
            (re.compile(r"deep neural networks.*deep learning", re.I), "Deep Neural Networks", "Deep Learning", "Prerequisite"),
            (re.compile(r"deep neural networks", re.I), "Deep Neural Networks", "Neural Networks", "Extension"),
            (re.compile(r"weights and biases", re.I), "Weights and Biases", "Neural Networks", "Part-of"),
            (re.compile(r"updated using gradient descent|parameters of a neural network are updated using gradient descent", re.I), "Gradient Descent", "Neural Networks", "Application"),
            (re.compile(r"chain rule from calculus|applying the chain rule", re.I), "Chain Rule", "Backpropagation", "Prerequisite"),
            (re.compile(r"backpropagation.*gradient descent|making gradient descent computationally practical", re.I), "Backpropagation", "Gradient Descent", "Application"),
            (re.compile(r"adam.*gradient descent|variants.*adam", re.I), "Adam", "Gradient Descent", "Extension"),
            (re.compile(r"rmsprop.*gradient descent|variants.*rmsprop", re.I), "RMSProp", "Gradient Descent", "Extension"),
            (re.compile(r"mean squared error", re.I), "Mean Squared Error", "Linear Regression", "Application"),
            (re.compile(r"linear regression.*models the relationship|linear regression.*machine learning", re.I), "Linear Regression", "Machine Learning", "Application"),
            (re.compile(r"closely related to linear regression", re.I), "Linear Regression", "Logistic Regression", "Similarity"),
            (re.compile(r"natural extension of linear regression", re.I), "Logistic Regression", "Linear Regression", "Extension"),
            (re.compile(r"binary classification", re.I), "Logistic Regression", "Binary Classification", "Application"),
            (re.compile(r"sigmoid function", re.I), "Sigmoid Function", "Logistic Regression", "Part-of"),
            (re.compile(r"loss function.*gradient descent|gradient of the loss function", re.I), "Loss Function", "Gradient Descent", "Prerequisite"),
        ]

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 20:
                continue

            # First check high-confidence pedagogical patterns
            for pat, src_name, tgt_name, rel_type in pedagogical_rules:
                if pat.search(sentence_clean):
                    self.add_relation(
                        source_name=src_name,
                        target_name=tgt_name,
                        relation_type=rel_type,
                        evidence=sentence_clean,
                        page=page,
                        chunk_id=chunk_id,
                    )

            # Find all concepts mentioned in this sentence
            found: List[NormalizedConcept] = []
            for c in all_concepts:
                # Check canonical name or aliases
                names_to_check = [c.concept_name] + list(c.aliases)
                for n in names_to_check:
                    if re.search(rf"\b{re.escape(n)}\b", sentence_clean, re.IGNORECASE):
                        found.append(c)
                        break

            # If at least 2 distinct concepts appear in the same sentence
            if len(found) >= 2:
                for i in range(len(found)):
                    for j in range(len(found)):
                        if i == j:
                            continue
                        c1 = found[i]
                        c2 = found[j]

                        # Check linguistic patterns between c1 and c2
                        s_lower = sentence_clean.lower()
                        for ont, keywords in ONTOLOGY_PATTERNS.items():
                            for kw in keywords:
                                if kw in s_lower:
                                    self.add_relation(
                                        source_name=c1.concept_name,
                                        target_name=c2.concept_name,
                                        relation_type=ont,
                                        evidence=sentence_clean,
                                        page=page,
                                        chunk_id=chunk_id,
                                    )
                                    break
