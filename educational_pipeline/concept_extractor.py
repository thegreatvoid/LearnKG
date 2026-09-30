"""
Step 4: Concept Extraction
Hybrid approach:
  - Extracts candidate educational concepts using deterministic NLP rules,
    capitalization cues, acronym detection, and textbook patterns.
  - Refines and enriches with LLM when available.
  - Classifies concepts into: Algorithm, Model, Formula, Theory, Component.
"""

import re
from typing import Dict, List, Set
from .chunker import EducationalChunk

STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "to", "from",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "figure", "table", "section", "chapter", "page", "study", "analysis",
    "example", "exercise", "results", "author", "authors", "approach", "method"
}

TYPE_KEYWORDS = {
    "Algorithm": ["algorithm", "descent", "search", "sort", "optimization", "method", "procedure"],
    "Model": ["model", "network", "system", "architecture", "classifier"],
    "Formula": ["formula", "equation", "function", "theorem", "postulate", "ratio", "sum"],
    "Theory": ["theory", "theorem", "principle", "law", "hypothesis", "conjecture", "proof"],
    "Component": ["segment", "angle", "vertex", "side", "face", "edge", "diagonal", "base",
                   "radius", "diameter", "chord", "arc", "sector", "hypotenuse"],
}

# Names, initials and license terms that appear on the copyright/credits page
# and should NEVER be treated as educational geometry concepts.
_BOILERPLATE_BLOCKLIST = {
    # Author names
    "cifarelli", "gloag", "greenberg", "jordan", "sconyers", "zahner",
    "victor", "andrew", "dan", "lori", "jim", "bill", "annamaria", "farbizio",
    # License / publisher noise
    "creative commons", "creative", "commons", "attribution", "share alike",
    "alike", "cc license", "commercial", "unported", "printed", "flexbook",
    "curriculum", "curriculum material", "platform", "complete", "users",
    "except", "click", "material", "license", "editor", "foundation",
    "say thanks", "thanks", "copyright", "nc", "by", "sa", "cc", "st", "cm",
    "ag", "lj", "dg", "bz", "af", "js", "ng", "ck",
    # Single words with no geometric meaning
    "and", "basic", "content", "printed",
}


def _is_boilerplate_concept(name: str) -> bool:
    """Returns True if the candidate name is clearly noise (author, license, etc)."""
    low = name.lower().strip()
    if low in _BOILERPLATE_BLOCKLIST:
        return True
    # Pure numeric / symbol strings are not concepts
    if not re.search(r"[a-zA-Z]{3,}", name):
        return True
    # Very short (≤ 2 chars) single tokens are noise (e.g. "SA", "BY", "NC")
    tokens = name.split()
    if len(tokens) == 1 and len(name) <= 2:
        return True
    return False


def infer_concept_type(concept_name: str) -> str:
    """Infers the concept_type based on suffix or keywords."""
    lowered = concept_name.lower()
    for c_type, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return c_type
    return "Component"


# Core geometry domain terms that should always be captured if present in a chunk
DOMAIN_TERMS = [
    # Fundamental objects
    "Point", "Line", "Line Segment", "Ray", "Plane", "Angle", "Vertex", "Polygon",
    # Triangles
    "Triangle", "Right Triangle", "Equilateral Triangle", "Isosceles Triangle",
    "Scalene Triangle", "Acute Triangle", "Obtuse Triangle", "Special Right Triangles",
    # Quadrilaterals & polygons
    "Quadrilateral", "Parallelogram", "Rectangle", "Rhombus", "Square", "Trapezoid",
    "Kite", "Pentagon", "Hexagon", "Heptagon", "Octagon", "Nonagon", "Decagon",
    "Hendecagon", "Dodecagon", "Regular Polygon",
    # Circles
    "Circle", "Radius", "Diameter", "Chord", "Arc", "Sector", "Tangent", "Secant",
    "Circumference", "Central Angle", "Inscribed Angle", "Concentric",
    # Measurements & transformations
    "Perimeter", "Area", "Volume", "Surface Area", "Scale Factor", "Dilation",
    "Reflection", "Rotation", "Translation", "Symmetry", "Reflection Symmetry",
    "Rotational Symmetry", "Line Symmetry",
    # Theorems & postulates
    "Pythagorean Theorem", "Congruence", "Similarity", "Proportionality",
    "Midpoint", "Bisector", "Perpendicular Bisector", "Angle Bisector",
    # 3-D geometry
    "Prism", "Pyramid", "Cylinder", "Cone", "Sphere", "Polyhedron", "Cross Section",
    # Coordinate geometry
    "Coordinate Plane", "Slope", "Distance Formula", "Midpoint Formula",
    "Cartesian Coordinate", "Coordinate System",
    # Other key terms
    "Proof", "Theorem", "Postulate", "Corollary", "Conjecture", "Counterexample",
    "Inductive Reasoning", "Deductive Reasoning", "Parallel", "Perpendicular",
    "Skew Lines", "Transversal", "Corresponding Angles", "Alternate Interior Angles",
    "Exterior Angle", "Interior Angle", "Supplementary", "Complementary",
    "Vertical Angles", "Linear Pair",
    "Midsegment", "Median", "Altitude", "Centroid", "Incenter", "Circumcenter",
    "Trigonometry", "Sine", "Cosine", "Tangent Ratio", "Inverse Trigonometric",
    "Fractal", "Self Similarity", "Star Polygon",
]


def extract_candidate_concepts_from_text(text: str) -> List[str]:
    """
    Extracts candidate educational terms using multi-word noun phrase patterns,
    capitalized phrases, acronyms, and textbook domain terms.
    Boilerplate names (authors, license text) are excluded.
    """
    candidates: Set[str] = set()

    # 1. Capitalized multi-word terms on same line (2 to 4 words, e.g. "Right Triangle")
    cap_phrase = re.findall(r"\b([A-Z][a-z]+(?:[^\S\r\n]+[A-Z][a-z]+){1,3})\b", text)
    for p in cap_phrase:
        p_clean = p.strip()
        first_word = p_clean.split()[0].lower()
        if first_word not in STOPWORDS and len(p_clean) > 4 and not _is_boilerplate_concept(p_clean):
            candidates.add(p_clean)

    # 2. Meaningful all-caps acronyms (geometry: SAS, ASA, AAS, SSS, HL, SSA)
    #    Restrict to known geometry abbreviation patterns; generic 2-char codes are noise.
    acronyms = re.findall(r"\b([A-Z]{2,5})\b", text)
    for acr in acronyms:
        if acr.lower() not in STOPWORDS and acr not in {"AND", "THE", "FOR", "NOT", "URL"}:
            # Only keep geometry congruence/similarity short-codes or well-known abbreviations
            if len(acr) >= 3 and not _is_boilerplate_concept(acr):
                candidates.add(acr)

    # 3. Quoted or italicized concepts ("...", '...')
    quoted = re.findall(r"[\"']([A-Za-z][A-Za-z0-9\s\-]{2,30})[\"']", text)
    for q in quoted:
        q_clean = q.strip()
        if len(q_clean.split()) <= 4 and q_clean.lower() not in STOPWORDS and not _is_boilerplate_concept(q_clean):
            candidates.add(q_clean.title())

    # 4. Keywords: definition/concept indicators
    def_matches = re.findall(
        r"(?:defined\s+as|known\s+as|termed|called|referred\s+to\s+as)\s+(?:an?|the)?\s*([A-Za-z][A-Za-z0-9\s\-]{2,30})",
        text, re.IGNORECASE
    )
    for d in def_matches:
        d_clean = d.strip()
        if len(d_clean.split()) <= 3 and d_clean.lower() not in STOPWORDS and not _is_boilerplate_concept(d_clean):
            candidates.add(d_clean.title())

    # 5. Core geometry domain terms present in this text
    for dt in DOMAIN_TERMS:
        if re.search(rf"\b{re.escape(dt)}\b", text, re.IGNORECASE):
            candidates.add(dt)

    return list(candidates)


def extract_concepts_for_chunk(chunk: EducationalChunk, llm_concepts: List[dict] = None) -> List[dict]:
    """
    Combines rule-based candidates with LLM-extracted concepts.
    Returns list of concept dicts: {concept_name, aliases, concept_type, definition, evidence}
    Boilerplate names (authors, license text) are excluded from both sources.
    """
    results: Dict[str, dict] = {}

    # If LLM extracted concepts are provided
    if llm_concepts:
        for c in llm_concepts:
            name = str(c.get("concept_name", "")).strip()
            if name and not _is_boilerplate_concept(name):
                results[name.lower()] = {
                    "concept_name": name,
                    "aliases": c.get("aliases", []),
                    "concept_type": c.get("concept_type", infer_concept_type(name)),
                    "definition": c.get("definition", ""),
                    "evidence": c.get("evidence", ""),
                }

    # Supplement with deterministic candidates
    candidates = extract_candidate_concepts_from_text(chunk.text)
    for cand in candidates:
        if _is_boilerplate_concept(cand):
            continue
        cand_lower = cand.lower()
        if cand_lower not in results:
            results[cand_lower] = {
                "concept_name": cand,
                "aliases": [],
                "concept_type": infer_concept_type(cand),
                "definition": "",
                "evidence": "",
            }

    return list(results.values())
