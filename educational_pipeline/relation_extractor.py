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
        # Explicit prerequisite cues
        "prerequisite", "required for", "requires", "depends on", "dependency",
        "foundation for", "understood before", "prior to", "must understand",
        "basis for", "underlying", "governs", "guided by",
        "before continuing", "origin of", "precondition",
        # Textbook recall/review cues common in geometry textbooks
        "recall that", "recall from", "as we learned", "building on",
        "using what we know", "using the fact that", "we need to know",
        "using our knowledge of", "in order to understand",
        "using properties of", "relies on", "apply our knowledge",
    ],
    "Part-of": [
        "part of", "component of", "element of", "consists of", "comprises",
        "includes", "subsystem of", "constituent of",
        "composed of", "subset of", "contained in",
        "is a type of", "is a kind of",
    ],
    "Application": [
        "applied to", "applied in", "used in", "used for", "used to",
        "serves to", "aims to", "implements", "solves", "utilized in",
        "operates on", "application of", "delivers", "provides",
        "computes", "calculates", "measures", "determines",
        "find the", "can be used to find",
    ],
    "Extension": [
        "extends", "extended by", "builds upon", "advancement of", "variant of",
        "generalization of", "improvement of", "modification of", "evolved from",
        "derived from", "expansion of", "evolves into", "extension to",
        "extension of", "special case of",
    ],
    "Similarity": [
        "similar to", "analogous to", "resembles", "comparable to",
        "contrasted with", "equivalent to", "closely related",
        "like", "same as", "congruent to",
    ],
}

# AHP-derived factor weights (see project report, CR = 0.022):
#   Weight = 0.52*SemanticSimilarity + 0.24*Co-occurrence
#          + 0.09*ChapterProximity  + 0.15*EducationalContext
AHP_FACTOR_WEIGHTS = {
    "semantic_similarity": 0.52,
    "cooccurrence": 0.24,
    "chapter_proximity": 0.09,
    "educational_context": 0.15,
}


def _word_set(text: str) -> Set[str]:
    return set(re.findall(r"[a-zA-Z]{3,}", str(text).lower()))


def semantic_similarity(c1: NormalizedConcept, c2: NormalizedConcept) -> float:
    """Jaccard overlap of definition (falling back to name) word sets — a
    dependency-free proxy for embedding cosine similarity."""
    w1 = _word_set(c1.definition) or _word_set(c1.concept_name)
    w2 = _word_set(c2.definition) or _word_set(c2.concept_name)
    if not w1 or not w2:
        return 0.0
    union = len(w1 | w2)
    return len(w1 & w2) / union if union else 0.0


def chapter_proximity(c1: NormalizedConcept, c2: NormalizedConcept) -> float:
    try:
        dist = abs(int(c1.chapter or 0) - int(c2.chapter or 0))
    except (TypeError, ValueError):
        dist = 0
    return 1.0 / (1.0 + dist)


def educational_context_score(c1: NormalizedConcept, c2: NormalizedConcept) -> float:
    score = 0.0
    if c1.chapter and c1.chapter == c2.chapter:
        score += 0.6
    if c1.section and c1.section == c2.section:
        score += 0.4
    return score if score else 0.3


def calculate_ahp_weight(
    c1: NormalizedConcept,
    c2: NormalizedConcept,
    cooccurrence: float,
) -> float:
    """
    Combines the four AHP-weighted factors into an educational edge weight.
    Each factor is itself normalized to [0, 1] and the AHP_FACTOR_WEIGHTS sum
    to 1, so the result is a true relevance score in [0, 1] rather than an
    arbitrary integer scale (see AHP_FACTOR_WEIGHTS for the derived priority
    vector, CR = 0.022).
    """
    sem_sim = semantic_similarity(c1, c2)
    cooc = max(0.0, min(1.0, cooccurrence))
    prox = chapter_proximity(c1, c2)
    edu = educational_context_score(c1, c2)

    score = (
        AHP_FACTOR_WEIGHTS["semantic_similarity"] * sem_sim
        + AHP_FACTOR_WEIGHTS["cooccurrence"] * cooc
        + AHP_FACTOR_WEIGHTS["chapter_proximity"] * prox
        + AHP_FACTOR_WEIGHTS["educational_context"] * edu
    )
    return round(max(0.0, min(1.0, score)), 4)


@dataclass
class ExtractedRelation:
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: float
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


class RelationManager:
    """Manages relation creation, classification, and ID assignment."""

    def __init__(self, normalizer: ConceptNormalizer):
        self.normalizer = normalizer
        self.relations: List[ExtractedRelation] = []
        self._next_id = 1
        # Track unique (source_id, target_id, relation_type) triplets to avoid duplicates
        self._seen: Set[Tuple[str, str, str]] = set()
        # Counts how many times each concept pair co-occurs in a sentence,
        # used as the Co-occurrence factor in the AHP edge-weight formula
        self._pair_cooccurrence: Dict[Tuple[str, str], int] = {}

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
        weight: Optional[float] = None,
    ) -> Optional[ExtractedRelation]:
        """Validates, classifies, and records an educational relation."""
        src_id = self.normalizer.find_match(source_name)
        tgt_id = self.normalizer.find_match(target_name)

        if not src_id or not tgt_id or src_id == tgt_id:
            return None

        # Classify into controlled ontology
        norm_type = classify_relation(relation_type)

        pair_key = (src_id, tgt_id)
        self._pair_cooccurrence[pair_key] = self._pair_cooccurrence.get(pair_key, 0) + 1
        cooc_score = min(1.0, self._pair_cooccurrence[pair_key] / 3.0)
        c1 = self.normalizer.concepts_by_id[src_id]
        c2 = self.normalizer.concepts_by_id[tgt_id]

        key = (src_id, tgt_id, norm_type)
        if key in self._seen:
            # If already exists, bump weight if higher
            for r in self.relations:
                if (r.source_id, r.target_id, r.relation_type) == key:
                    new_w = weight if weight is not None and 0.0 <= weight <= 1.0 else calculate_ahp_weight(c1, c2, cooc_score)
                    r.weight = max(r.weight, new_w)
                    return r
            return None

        self._seen.add(key)
        final_weight = weight if weight is not None and 0.0 <= weight <= 1.0 else calculate_ahp_weight(c1, c2, cooc_score)

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

        # Explicit high-confidence pedagogical patterns for geometry textbook exposition
        pedagogical_rules = [
            # ── Triangle prerequisites ──────────────────────────────────────────────
            (re.compile(r"pythagorean theorem", re.I), "Pythagorean Theorem", "Right Triangle", "Prerequisite"),
            (re.compile(r"converse of the pythagorean theorem", re.I), "Right Triangle", "Pythagorean Theorem", "Extension"),
            (re.compile(r"special right triangles.*45.*60|45.*60.*special right", re.I), "Special Right Triangles", "Right Triangle", "Extension"),
            (re.compile(r"triangle inequality", re.I), "Triangle", "Line Segment", "Prerequisite"),
            (re.compile(r"congruent triangles|triangle congruence", re.I), "Congruence", "Triangle", "Application"),
            (re.compile(r"similar triangles|triangle similarity", re.I), "Similarity", "Triangle", "Application"),
            # ── Angle prerequisites ─────────────────────────────────────────────────
            (re.compile(r"sum of interior angles.*polygon|polygon.*sum of interior angles", re.I), "Interior Angle", "Polygon", "Part-of"),
            (re.compile(r"exterior angle.*triangle|remote interior", re.I), "Exterior Angle", "Triangle", "Part-of"),
            (re.compile(r"parallel lines.*transversal|transversal.*parallel", re.I), "Parallel", "Transversal", "Prerequisite"),
            (re.compile(r"alternate interior angles", re.I), "Alternate Interior Angles", "Parallel", "Prerequisite"),
            (re.compile(r"corresponding angles", re.I), "Corresponding Angles", "Parallel", "Prerequisite"),
            (re.compile(r"supplementary angles", re.I), "Supplementary", "Angle", "Part-of"),
            (re.compile(r"complementary angles", re.I), "Complementary", "Angle", "Part-of"),
            (re.compile(r"vertical angles", re.I), "Vertical Angles", "Angle", "Part-of"),
            (re.compile(r"linear pair", re.I), "Linear Pair", "Angle", "Part-of"),
            # ── Circles ─────────────────────────────────────────────────────────────
            (re.compile(r"inscribed angle.*central angle|central angle.*arc", re.I), "Inscribed Angle", "Central Angle", "Prerequisite"),
            (re.compile(r"arc length.*circumference|circumference.*arc", re.I), "Arc", "Circumference", "Prerequisite"),
            (re.compile(r"tangent.*radius.*perpendicular|radius.*tangent", re.I), "Tangent", "Radius", "Prerequisite"),
            (re.compile(r"secant.*chord|chord.*secant", re.I), "Secant", "Chord", "Similarity"),
            (re.compile(r"diameter.*radius|two times.*radius", re.I), "Diameter", "Radius", "Part-of"),
            # ── Quadrilaterals ───────────────────────────────────────────────────────
            (re.compile(r"rectangle.*parallelogram|rhombus.*parallelogram|square.*parallelogram", re.I), "Parallelogram", "Rectangle", "Extension"),
            (re.compile(r"isosceles trapezoid", re.I), "Isosceles Triangle", "Trapezoid", "Similarity"),
            (re.compile(r"kite.*perpendicular diagonals", re.I), "Kite", "Perpendicular", "Prerequisite"),
            # ── Similarity & proportionality ─────────────────────────────────────────
            (re.compile(r"scale factor.*dilation|dilation.*scale factor", re.I), "Scale Factor", "Dilation", "Part-of"),
            (re.compile(r"aa similarity|sas similarity|sss similarity", re.I), "Similarity", "Triangle", "Application"),
            # ── Coordinate geometry ──────────────────────────────────────────────────
            (re.compile(r"slope.*parallel|parallel.*slope", re.I), "Slope", "Parallel", "Prerequisite"),
            (re.compile(r"slope.*perpendicular|perpendicular.*slope", re.I), "Slope", "Perpendicular", "Prerequisite"),
            (re.compile(r"distance formula", re.I), "Distance Formula", "Coordinate Plane", "Application"),
            (re.compile(r"midpoint formula", re.I), "Midpoint Formula", "Coordinate Plane", "Application"),
            # ── 3D geometry ──────────────────────────────────────────────────────────
            (re.compile(r"surface area.*prism|volume.*prism", re.I), "Prism", "Area", "Prerequisite"),
            (re.compile(r"surface area.*cylinder|volume.*cylinder", re.I), "Cylinder", "Circle", "Prerequisite"),
            (re.compile(r"surface area.*sphere|volume.*sphere", re.I), "Sphere", "Circle", "Prerequisite"),
            (re.compile(r"cross.?section", re.I), "Cross Section", "Plane", "Prerequisite"),
            # ── Proofs & reasoning ───────────────────────────────────────────────────
            (re.compile(r"two.?column proof|paragraph proof|flow proof", re.I), "Proof", "Theorem", "Application"),
            (re.compile(r"inductive reasoning.*conjecture|conjecture.*inductive", re.I), "Inductive Reasoning", "Conjecture", "Prerequisite"),
            (re.compile(r"deductive reasoning", re.I), "Deductive Reasoning", "Proof", "Prerequisite"),
            (re.compile(r"trigonometric ratio|sine.*cosine|cosine.*sine", re.I), "Trigonometry", "Right Triangle", "Prerequisite"),
            (re.compile(r"fractal.*self.?similar|self.?similar.*fractal", re.I), "Fractal", "Self Similarity", "Part-of"),
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
