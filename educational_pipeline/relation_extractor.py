"""
Steps 7, 8, & 9: Relation Extraction, Controlled Ontology Classification, & Weight Assignment

Enforces the Controlled Educational Ontology:
  1. Prerequisite (A -> B: A should be understood before B)
  2. Part-of      (A -> B: A is a component or part of B)
  3. Application  (A -> B: A is applied or used within B)
  4. Extension    (A -> B: A builds upon or extends B)
  5. Similarity   (A <-> B: conceptually similar and symmetric)

Assigns an AHP-derived educational relevance weight in [0, 1] (see docs/ahp_weights.md) and preserves
verbatim source sentence evidence. Weights are computed once, after all relations are collected, by
RelationManager.finalize_weights(chunks), because the co-occurrence and section factors need the whole text.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple
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

# Keyword matching is on whole words/phrases ("like" must not match "unlike").
KEYWORD_RES = {ont: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", re.I)
               for ont, kws in ONTOLOGY_PATTERNS.items()}

# For Part-of / Application / Extension the sentence must say which concept is the source. In "X <keyword> Y"
# the concept before the keyword is the source, except for these keywords, where the roles are reversed
# ("a polygon consists of segments" -> segment Part-of polygon; "X is extended by Y" -> Y Extension X).
REVERSED_KEYWORDS = {
    "Part-of": {"consists of", "comprises", "includes", "composed of"},
    "Application": {"application of"},
    "Extension": {"extended by", "evolves into"},
}
DIRECTIONAL_TYPES = ("Part-of", "Application", "Extension")


# AHP-derived factor weights (see project report, CR = 0.022):
#   Weight = 0.52*SemanticSimilarity + 0.24*Co-occurrence
#          + 0.09*ChapterProximity  + 0.15*EducationalContext
AHP_FACTOR_WEIGHTS = {
    "semantic_similarity": 0.52,
    "cooccurrence": 0.24,
    "chapter_proximity": 0.09,
    "educational_context": 0.15,
}


# Weighting schemes (frozen 2026-10-15; see docs/ahp_weights.md and kg_eval/README.md section 5.11).
# Every scheme is a convex combination of the same pair factors (pair_factors), so all are evaluated identically.
#   ahp               the original expert (AHP) coefficients: the documented baseline
#   cooc_only         W = C
#   cooc_struct_a0.8  W = 0.8 C + 0.2 E. alpha = 0.8 is the value chosen in 4 of 5 training folds of the
#                     2026-10-14 cross-validation on CK-12 geometry; a candidate, not an established optimum,
#                     and NOT independent of the CK-12 evaluation that suggested it.
WEIGHTING_SCHEMES: Dict[str, Dict[str, float]] = {
    "ahp": dict(AHP_FACTOR_WEIGHTS),
    "cooc_only": {"cooccurrence": 1.0},
    "cooc_struct_a0.8": {"cooccurrence": 0.8, "educational_context": 0.2},
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


def chapter_number(chapter: str) -> Optional[int]:
    """Chapter number from a parser label like "Chapter 5: Relationships with Triangles" (None if absent)."""
    m = re.search(r"\d+", chapter or "")
    return int(m.group()) if m else None


def chapter_proximity(c1: NormalizedConcept, c2: NormalizedConcept) -> float:
    n1, n2 = chapter_number(c1.chapter), chapter_number(c2.chapter)
    if n1 is None or n2 is None:
        return 0.5  # unknown distance: neutral rather than "same chapter"
    return 1.0 / (1.0 + abs(n1 - n2))


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
    return ahp_components(c1, c2, cooccurrence)[1]


def ahp_components(
    c1: NormalizedConcept,
    c2: NormalizedConcept,
    cooccurrence: float,
) -> Tuple[Dict[str, float], float]:
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
    components = {
        "semantic_similarity": sem_sim,
        "cooccurrence": cooc,
        "chapter_proximity": prox,
        "educational_context": edu,
    }
    return components, round(max(0.0, min(1.0, score)), 4)


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
    # Provenance of the weight, so weighting ablations can be recomputed exactly.
    weight_source: str = "ahp"  # "ahp" = AHP formula with corrected factors (see finalize_weights)
    cooccurrence_count: int = 0  # sentences that mention both concepts (factor C = min(1, count/3))
    semantic_similarity: float = 0.0  # factor S: Jaccard of validated definitions (see finalize_weights)
    chapter_proximity: float = 0.0  # factor P
    educational_context: float = 0.0  # factor E: Jaccard of the sections in which each concept is mentioned
    # Inspection / audit fields
    n_proposals: int = 1  # distinct (sentence, source) proposals of this exact directed typed edge
    sources: Set[str] = field(default_factory=set)  # rule / keyword / llm / neural / graph_csv / unspecified
    evidence_all: List[str] = field(default_factory=list)  # every distinct evidence sentence, in order
    extractor_scores: Dict[str, float] = field(default_factory=dict)  # raw extractor scores, never mixed into weight
    s_jaccard_raw: float = 0.0  # legacy S: Jaccard of stored definitions, unvalidated
    s_embedding: float = float("nan")  # cosine of definition embeddings (NaN if not computed)
    definitions_valid: str = ""  # "both" / "one" / "none": were both concepts' definitions validated?
    chapter_missing: bool = False  # P fell back to 0.5 because a chapter number is unknown
    educational_context_legacy: float = 0.0  # legacy E: 0.6 same chapter + 0.4 same section, else 0.3
    weight_legacy: float = 0.0  # original formula: legacy S, C = min(1, n_proposals/3), P, legacy E
    weight_scheme: str = "ahp"  # WEIGHTING_SCHEMES key used for `weight`
    scheme_weights: Dict[str, float] = field(default_factory=dict)  # weight under every scheme, for comparison


# ---------------------------------------------------------------------------------------------------------
# Factor helpers used by finalize_weights (pair functions, also usable for pairs that have no edge).
# ---------------------------------------------------------------------------------------------------------

def _name_pattern(name: str) -> Optional[re.Pattern]:
    words = re.findall(r"[a-z0-9]+", str(name).lower())
    if not words:
        return None
    return re.compile(r"\b" + r"[\s\-]+".join(re.escape(w) for w in words) + r"(?:s|es)?\b", re.I)


def definition_is_valid(concept: NormalizedConcept) -> bool:
    """A definition counts as the concept's own only if the concept (name or alias) is the subject of a defining
    clause: "[A/An/The] <concept> is/are/has/have/uses/refers to/means/is defined as ...", or "<concept>: ...". A sentence that
    merely mentions the concept (e.g. "A linear pair ... form a straight line." for Line) is rejected."""
    text = (concept.definition or "").strip()
    if not text:
        return False
    first = text.split("\n")[-1] if re.match(r"^\d+(?:\.\d+)*\s", text) and "\n" in text else text
    for name in [concept.concept_name, *concept.aliases]:
        body = r"[\s\-]+".join(re.escape(w) for w in re.findall(r"[a-z0-9]+", name.lower()))
        if not body:
            continue
        if re.match(rf"^\s*(?:(?:a|an|the)\s+)?{body}(?:s|es)?\s+(?:is|are|has|have|uses|refers\s+to|means|is\s+defined\s+as)\b",
                    first, re.I) or re.match(rf"^\s*{body}\s*:", first, re.I):
            return True
    return False


def jaccard(a: Set[str], b: Set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


class MentionIndex:
    """Which sentences / sections mention each concept (name or alias, whole word, plural-tolerant).
    The co-occurrence unit is the sentence, split after . ? or ! (same rule as the pipeline), inside each chunk."""

    def __init__(self, concepts: Iterable[NormalizedConcept], chunks):
        self.sentences: Dict[str, Set[int]] = {}
        self.sections: Dict[str, Set[str]] = {}
        pats = {c.concept_id: [p for p in map(_name_pattern, [c.concept_name, *c.aliases]) if p] for c in concepts}
        sid = 0
        for ch in chunks:
            section = (getattr(ch, "section", "") or "").strip()
            for sent in re.split(r"(?<=[.?!])\s+", ch.text):
                for cid, ps in pats.items():
                    if any(p.search(sent) for p in ps):
                        self.sentences.setdefault(cid, set()).add(sid)
                        if section:
                            self.sections.setdefault(cid, set()).add(section)
                sid += 1

    def cooccurrence(self, a: str, b: str) -> int:
        return len(self.sentences.get(a, set()) & self.sentences.get(b, set()))

    def section_jaccard(self, a: str, b: str) -> float:
        sa, sb = self.sections.get(a, set()), self.sections.get(b, set())
        return jaccard(sa, sb) if sa and sb else float("nan")


def pair_factors(c1: NormalizedConcept, c2: NormalizedConcept, index: MentionIndex,
                 valid: Optional[Dict[str, bool]] = None) -> Dict[str, float]:
    """All factor values for one concept pair. S uses a concept's definition only if it was validated; otherwise
    its name (the same fallback the legacy code used for an empty definition)."""
    valid = valid if valid is not None else {}
    def words(c):
        if valid.get(c.concept_id, definition_is_valid(c)):
            return _word_set(c.definition)
        return _word_set(c.concept_name)
    n = index.cooccurrence(c1.concept_id, c2.concept_id)
    e = index.section_jaccard(c1.concept_id, c2.concept_id)
    n1, n2 = chapter_number(c1.chapter), chapter_number(c2.chapter)
    return {
        "semantic_similarity": jaccard(words(c1), words(c2)),
        "s_jaccard_raw": semantic_similarity(c1, c2),
        "cooccurrence_count": n,
        "cooccurrence": min(1.0, n / 3.0),
        "chapter_proximity": chapter_proximity(c1, c2),
        "chapter_missing": n1 is None or n2 is None,
        "educational_context": 0.0 if math.isnan(e) else e,
        "educational_context_missing": math.isnan(e),
        "educational_context_legacy": educational_context_score(c1, c2),
    }


def combine(factors: Dict[str, float], coefficients: Optional[Dict[str, float]] = None) -> float:
    """sum_k w_k * factor_k, clipped to [0, 1]. Factors absent from `coefficients` get weight 0."""
    w = coefficients or AHP_FACTOR_WEIGHTS
    score = sum(w[k] * factors[k] for k in w)
    return round(max(0.0, min(1.0, score)), 4)


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
        self._by_key: Dict[Tuple[str, str, str], ExtractedRelation] = {}
        self._proposals: Set[Tuple[Tuple[str, str, str], str, str]] = set()
        self.stats: Counter = Counter()  # extraction / weighting diagnostics, printed by the pipeline

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
        source: str = "unspecified",
    ) -> Optional[ExtractedRelation]:
        """Validates, classifies and records one proposal of a directed, typed relation.

        `weight` is an extractor's own score. It is stored raw in `extractor_scores[source]` and NOT used as the edge
        weight: extractor scales are not comparable (neural: rescaled cross-encoder logit in [0.2, 1]; LLM: integer
        1-10). The edge weight is the AHP formula, computed for every edge by finalize_weights().
        A repeated proposal with the same evidence sentence from the same source is ignored (it is the same rule
        firing twice on one sentence); proposals from other sentences or other sources add evidence and count.
        """
        src_id = self.normalizer.find_match(source_name)
        tgt_id = self.normalizer.find_match(target_name)

        if not src_id or not tgt_id or src_id == tgt_id:
            return None

        norm_type = classify_relation(relation_type)
        key = (src_id, tgt_id, norm_type)  # direction matters: (a, b) and (b, a) are different edges
        ev = evidence.strip()
        proposal = (key, ev, source)
        if proposal in self._proposals:
            self.stats["duplicate_proposals_ignored"] += 1
            return self._by_key.get(key)
        self._proposals.add(proposal)

        rel = self._by_key.get(key)
        if rel is None:
            rel = ExtractedRelation(
                relation_id=self._generate_id(), source_id=src_id, target_id=tgt_id, relation_type=norm_type,
                weight=0.0, page=page, chunk_id=chunk_id, evidence=ev, n_proposals=0)
            self.relations.append(rel)
            self._by_key[key] = rel
            self._seen.add(key)
        rel.n_proposals += 1
        rel.sources.add(source)
        if ev and ev not in rel.evidence_all:
            rel.evidence_all.append(ev)
        if weight is not None:
            try:
                score = float(weight)
            except (TypeError, ValueError):
                self.stats[f"invalid_extractor_score_{source}"] += 1
            else:
                prev = rel.extractor_scores.get(source)
                rel.extractor_scores[source] = score if prev is None else max(prev, score)
        return rel

    def finalize_weights(self, chunks, compute_embeddings: bool = False, scheme: str = "ahp") -> None:
        """Computes every factor and the edge weight once, from the full text.

        S  Jaccard of the two concepts' definition word sets, using a definition only if it is the concept's own
           (definition_is_valid); otherwise the concept name. `s_jaccard_raw` keeps the legacy, unvalidated value.
           Lexical overlap, not semantic understanding.
        C  min(1, n/3), n = sentences (pipeline sentence split, all chunks) that mention both concepts.
           Undirected and independent of how many times a rule proposed the edge.
        P  1 / (1 + |chapter_a - chapter_b|) from the parsed chapter of each concept's first mention;
           0.5 with chapter_missing=True if either chapter number is unknown.
        E  Jaccard of the sets of parsed sections in which each concept is mentioned (0 if a concept has no
           section label; flagged in stats). `educational_context_legacy` keeps the old constants.
        weight = sum of WEIGHTING_SCHEMES[scheme] coefficients x factors; default "ahp" =
        0.52 S + 0.24 C + 0.09 P + 0.15 E (expert judgement, docs/ahp_weights.md). All schemes are stored too.
        weight_legacy = the original formula (legacy S, C = min(1, n_proposals/3), P, legacy E), for comparison.
        """
        if scheme not in WEIGHTING_SCHEMES:
            raise ValueError(f"unknown weighting scheme {scheme!r}; known: {sorted(WEIGHTING_SCHEMES)}")
        concepts = self.normalizer.get_all_concepts()
        index = MentionIndex(concepts, chunks)
        valid = {c.concept_id: definition_is_valid(c) for c in concepts}
        self.stats["concepts_definition_valid"] = sum(valid.values())
        self.stats["concepts_definition_invalid_or_empty"] = len(valid) - sum(valid.values())
        emb = None
        if compute_embeddings:
            emb = self._definition_embeddings(concepts, valid)
        by_id = self.normalizer.concepts_by_id
        for r in self.relations:
            c1, c2 = by_id[r.source_id], by_id[r.target_id]
            f = pair_factors(c1, c2, index, valid)
            r.semantic_similarity = round(f["semantic_similarity"], 4)
            r.s_jaccard_raw = round(f["s_jaccard_raw"], 4)
            r.cooccurrence_count = f["cooccurrence_count"]
            r.chapter_proximity = round(f["chapter_proximity"], 4)
            r.chapter_missing = f["chapter_missing"]
            r.educational_context = round(f["educational_context"], 4)
            r.educational_context_legacy = f["educational_context_legacy"]
            r.definitions_valid = {2: "both", 1: "one", 0: "none"}[valid[c1.concept_id] + valid[c2.concept_id]]
            if f["educational_context_missing"]:
                self.stats["edges_section_missing"] += 1
            if f["chapter_missing"]:
                self.stats["edges_chapter_missing"] += 1
            if emb is not None:
                r.s_embedding = round(float(emb[r.source_id] @ emb[r.target_id]), 4)
            r.scheme_weights = {name: combine(f, w) for name, w in WEIGHTING_SCHEMES.items()}
            r.weight = r.scheme_weights[scheme]
            r.weight_scheme = scheme
            r.weight_source = "ahp"  # = computed by the factor formula (kept for kg_eval.weight_ablation)
            r.weight_legacy = combine({
                "semantic_similarity": f["s_jaccard_raw"], "cooccurrence": min(1.0, r.n_proposals / 3.0),
                "chapter_proximity": f["chapter_proximity"], "educational_context": f["educational_context_legacy"]})

    @staticmethod
    def _definition_embeddings(concepts, valid):
        """Unit-normalised MiniLM embeddings of each concept's validated definition (else its name)."""
        from sentence_transformers import SentenceTransformer  # explicit dependency; raises if missing
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        texts = [c.definition if valid[c.concept_id] else c.concept_name for c in concepts]
        vecs = model.encode(texts, normalize_embeddings=True)
        return {c.concept_id: v for c, v in zip(concepts, vecs)}

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
        # In this ontology, (A -> B, "Prerequisite") means A must be understood BEFORE B.
        pedagogical_rules = [
            # ── Triangle prerequisites ──────────────────────────────────────────────
            (re.compile(r"pythagorean theorem", re.I), "Right Triangle", "Pythagorean Theorem", "Prerequisite"),
            (re.compile(r"converse of the pythagorean theorem", re.I), "Pythagorean Theorem", "Right Triangle", "Extension"),
            (re.compile(r"special right triangles.*45.*60|45.*60.*special right", re.I), "Right Triangle", "Special Right Triangles", "Extension"),
            (re.compile(r"triangle inequality", re.I), "Line Segment", "Triangle", "Prerequisite"),
            (re.compile(r"congruent triangles|triangle congruence", re.I), "Triangle", "Congruence", "Application"),
            (re.compile(r"similar triangles|triangle similarity", re.I), "Triangle", "Similarity", "Application"),
            # ── Angle prerequisites ─────────────────────────────────────────────────
            (re.compile(r"sum of interior angles.*polygon|polygon.*sum of interior angles", re.I), "Polygon", "Interior Angle", "Part-of"),
            (re.compile(r"exterior angle.*triangle|remote interior", re.I), "Triangle", "Exterior Angle", "Part-of"),
            (re.compile(r"parallel lines.*transversal|transversal.*parallel", re.I), "Parallel", "Transversal", "Prerequisite"),
            (re.compile(r"alternate interior angles", re.I), "Parallel", "Alternate Interior Angles", "Prerequisite"),
            (re.compile(r"corresponding angles", re.I), "Parallel", "Corresponding Angles", "Prerequisite"),
            (re.compile(r"supplementary angles", re.I), "Angle", "Supplementary", "Part-of"),
            (re.compile(r"complementary angles", re.I), "Angle", "Complementary", "Part-of"),
            (re.compile(r"vertical angles", re.I), "Angle", "Vertical Angles", "Part-of"),
            (re.compile(r"linear pair", re.I), "Angle", "Linear Pair", "Part-of"),
            # ── Circles ─────────────────────────────────────────────────────────────
            (re.compile(r"inscribed angle.*central angle|central angle.*arc", re.I), "Central Angle", "Inscribed Angle", "Prerequisite"),
            (re.compile(r"arc length.*circumference|circumference.*arc", re.I), "Circumference", "Arc", "Prerequisite"),
            (re.compile(r"tangent.*radius.*perpendicular|radius.*tangent", re.I), "Radius", "Tangent", "Prerequisite"),
            (re.compile(r"secant.*chord|chord.*secant", re.I), "Chord", "Secant", "Similarity"),
            (re.compile(r"diameter.*radius|two times.*radius", re.I), "Radius", "Diameter", "Part-of"),
            # ── Quadrilaterals ───────────────────────────────────────────────────────
            (re.compile(r"rectangle.*parallelogram|rhombus.*parallelogram|square.*parallelogram", re.I), "Parallelogram", "Rectangle", "Extension"),
            (re.compile(r"isosceles trapezoid", re.I), "Isosceles Triangle", "Trapezoid", "Similarity"),
            (re.compile(r"kite.*perpendicular diagonals", re.I), "Perpendicular", "Kite", "Prerequisite"),
            # ── Similarity & proportionality ─────────────────────────────────────────
            (re.compile(r"scale factor.*dilation|dilation.*scale factor", re.I), "Scale Factor", "Dilation", "Part-of"),
            (re.compile(r"aa similarity|sas similarity|sss similarity", re.I), "Triangle", "Similarity", "Application"),
            # ── Coordinate geometry ──────────────────────────────────────────────────
            (re.compile(r"slope.*parallel|parallel.*slope", re.I), "Slope", "Parallel", "Prerequisite"),
            (re.compile(r"slope.*perpendicular|perpendicular.*slope", re.I), "Slope", "Perpendicular", "Prerequisite"),
            (re.compile(r"distance formula", re.I), "Coordinate Plane", "Distance Formula", "Application"),
            (re.compile(r"midpoint formula", re.I), "Coordinate Plane", "Midpoint Formula", "Application"),
            # ── 3D geometry ──────────────────────────────────────────────────────────
            (re.compile(r"surface area.*prism|volume.*prism", re.I), "Area", "Prism", "Prerequisite"),
            (re.compile(r"surface area.*cylinder|volume.*cylinder", re.I), "Circle", "Cylinder", "Prerequisite"),
            (re.compile(r"surface area.*sphere|volume.*sphere", re.I), "Circle", "Sphere", "Prerequisite"),
            (re.compile(r"cross.?section", re.I), "Plane", "Cross Section", "Prerequisite"),
            # ── Proofs & reasoning ───────────────────────────────────────────────────
            (re.compile(r"two.?column proof|paragraph proof|flow proof", re.I), "Theorem", "Proof", "Application"),
            (re.compile(r"inductive reasoning.*conjecture|conjecture.*inductive", re.I), "Conjecture", "Inductive Reasoning", "Prerequisite"),
            (re.compile(r"deductive reasoning", re.I), "Deductive Reasoning", "Proof", "Prerequisite"),
            (re.compile(r"trigonometric ratio|sine.*cosine|cosine.*sine", re.I), "Right Triangle", "Trigonometry", "Prerequisite"),
            (re.compile(r"fractal.*self.?similar|self.?similar.*fractal", re.I), "Self Similarity", "Fractal", "Part-of"),
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
                        source="rule",
                    )

            # Find all concepts mentioned in this sentence, with the position of their first mention
            found: List[Tuple[NormalizedConcept, int, int]] = []
            for c in all_concepts:
                for n in [c.concept_name] + list(c.aliases):
                    m = re.search(rf"\b{re.escape(n)}\b", sentence_clean, re.IGNORECASE)
                    if m:
                        found.append((c, m.start(), m.end()))
                        break
            if len(found) < 2:
                continue

            # The first relation type (in ONTOLOGY_PATTERNS order) with a whole-word keyword in the sentence.
            hit = None
            for ont, kre in KEYWORD_RES.items():
                m = kre.search(sentence_clean)
                if m:
                    hit = (ont, m)
                    break
            if hit is None:
                continue
            ont, kw_match = hit
            kw = kw_match.group(0).lower()

            for i in range(len(found)):
                for j in range(i + 1, len(found)):
                    (c1, s1, e1), (c2, s2, e2) = found[i], found[j]
                    if ont == "Prerequisite":
                        # No direction in the sentence: earlier-introduced concept -> later one (unchanged rule)
                        src_c, tgt_c = (c1, c2) if (c1.page, c1.concept_id) <= (c2.page, c2.concept_id) else (c2, c1)
                    elif ont == "Similarity":
                        src_c, tgt_c = c1, c2  # symmetric: one proposal per sentence and pair
                    else:
                        # Directional types: one concept must precede the keyword and the other follow it.
                        k0, k1 = kw_match.start(), kw_match.end()
                        before = [c for c, cs, ce in ((c1, s1, e1), (c2, s2, e2)) if ce <= k0]
                        after = [c for c, cs, ce in ((c1, s1, e1), (c2, s2, e2)) if cs >= k1]
                        if len(before) != 1 or len(after) != 1:
                            self.stats["keyword_no_direction_skipped"] += 1
                            continue
                        src_c, tgt_c = before[0], after[0]
                        if kw in REVERSED_KEYWORDS.get(ont, set()):
                            src_c, tgt_c = tgt_c, src_c
                    self.add_relation(
                        source_name=src_c.concept_name,
                        target_name=tgt_c.concept_name,
                        relation_type=ont,
                        evidence=sentence_clean,
                        page=page,
                        chunk_id=chunk_id,
                        source="keyword",
                    )
