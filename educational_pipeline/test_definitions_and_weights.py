"""Regression tests for definition assignment, factor/weight calculation and reproducibility.

Run: python educational_pipeline/test_definitions_and_weights.py   (or with pytest)
The definition cases are real CK-12 sentences that were mis-assigned before 2026-10-15 (kg_eval/README.md 5.11).
"""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from educational_pipeline.definition_extractor import extract_grounded_definition, find_definition
from educational_pipeline.normalizer import ConceptNormalizer, NormalizedConcept
from educational_pipeline.relation_extractor import (WEIGHTING_SCHEMES, MentionIndex, RelationManager, combine,
                                                     definition_is_valid, pair_factors)

S11 = ("1.1 Points, Lines, and Planes\nA point is a location with no dimension. It is represented by a dot. "
       "A line is a straight one-dimensional figure with no thickness that extends infinitely in both directions.")
S52 = ("5.2 Perpendicular Bisectors and Angle Bisectors\nThe perpendicular bisector theorem states that any point on "
       "the perpendicular bisector of a segment is equidistant from the endpoints.")
S74 = ("7.4 Proportionality Relationships\nThe triangle proportionality theorem states that if a line is parallel to "
       "one side of a triangle and intersects the other two sides, it divides those sides proportionally.")
S61 = "6.1 Angles in Polygons\nThe exterior angle sum of any polygon is always 360 degrees."
S12 = "1.2 Segments and Distance\nThe midpoint of a segment is the point that divides it into two congruent segments."


# ---------------- definition finder ----------------

def test_definitional_sentence_is_found_verbatim():
    d, ev, kind = find_definition("Point", S11)
    assert kind == "definitional" and d == "A point is a location with no dimension." == ev


def test_mid_sentence_match_is_not_a_definition():
    # legacy extractor turned this into "Line is parallel to one side of a triangle ..."
    assert extract_grounded_definition("Line", S74)[0].startswith("Line is parallel")
    d, ev, kind = find_definition("Line", S74)
    assert kind == "mention" and d == "" and "if a line is parallel" in ev


def test_no_rewriting_artefacts():
    # legacy extractor: the optional article ate the "a" of "always" -> "Polygon is lways 360 degrees"
    assert extract_grounded_definition("Polygon", S61)[0] == "Polygon is lways 360 degrees"
    assert find_definition("Polygon", S61)[2] == "mention"


def test_subject_with_of_qualifier_is_definitional():
    assert find_definition("Midpoint", S12)[2] == "definitional"
    assert find_definition("Point", S12)[2] == "mention"  # "the point that divides it" is not Point's definition


def test_heading_lines_are_dropped():
    d, ev, kind = find_definition("Point", S52)
    assert not ev.startswith("5.2") and kind == "mention"


def test_no_mention_returns_none():
    assert find_definition("Circle", S11) is None


# ---------------- normaliser policy ----------------

def _register(policy, *defs):
    n = ConceptNormalizer(definition_policy=policy)
    for text, kind in defs:
        n.register_concept("Point", definition=text, definition_kind=kind, evidence=text)
    return n.get_all_concepts()[0]


def test_first_definitional_is_not_replaced_by_a_longer_mention():
    long_mention = "The perpendicular bisector theorem states that any point on the bisector is equidistant from the endpoints."
    c = _register("first_definitional", ("A point is a location with no dimension.", "definitional"), ("", "mention"),
                  (long_mention, "mention"))
    assert c.definition == "A point is a location with no dimension." and c.definition_kind == "definitional"


def test_mention_is_upgraded_to_a_later_definition():
    c = _register("first_definitional", ("", "mention"), ("A point is a location with no dimension.", "definitional"))
    assert c.definition_kind == "definitional"


def test_legacy_policy_reproduces_longest_wins():
    long_text = "The perpendicular bisector theorem states that any point on the bisector is equidistant from the endpoints."
    c = _register("legacy_longest", ("Point is location with no dimension", "legacy"), (long_text, "legacy"))
    assert c.definition == long_text


def test_unknown_policy_rejected():
    try:
        ConceptNormalizer(definition_policy="newest")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---------------- factors and weights ----------------

def _concepts():
    a = NormalizedConcept("C1", "Kite", definition="A kite is a quadrilateral with two pairs of adjacent sides.",
                          chapter="Chapter 6: Polygons", section="6.5 Trapezoids and Kites")
    b = NormalizedConcept("C2", "Quadrilateral", definition="A quadrilateral is a polygon with four sides.",
                          chapter="Chapter 6: Polygons", section="6.2 Quadrilaterals")
    c = NormalizedConcept("C3", "Circle", definition="", chapter="", section="")
    return a, b, c


def _chunks():
    return [SimpleNamespace(text="A quadrilateral is a polygon with four sides. A kite is a quadrilateral.", section="6.2 Quadrilaterals"),
            SimpleNamespace(text="A kite is a quadrilateral with two pairs of adjacent sides. A kite has a diagonal.", section="6.5 Trapezoids and Kites")]


def test_factor_values_and_normalisation():
    a, b, c = _concepts()
    idx = MentionIndex([a, b, c], _chunks())
    f = pair_factors(a, b, idx)
    assert f["cooccurrence_count"] == 2 and abs(f["cooccurrence"] - 2 / 3) < 1e-9          # C = min(1, n/3)
    assert f["chapter_proximity"] == 1.0 and not f["chapter_missing"]                       # same chapter
    assert abs(f["educational_context"] - 1.0) < 1e-9                                       # both in {6.2, 6.5}
    assert 0.0 < f["semantic_similarity"] < 1.0


def test_missing_metadata_and_invalid_definition():
    a, b, c = _concepts()
    idx = MentionIndex([a, b, c], _chunks())
    f = pair_factors(a, c, idx)
    assert f["chapter_missing"] and f["chapter_proximity"] == 0.5     # unknown chapter -> neutral, flagged
    assert f["educational_context_missing"] and f["educational_context"] == 0.0
    assert f["cooccurrence_count"] == 0 and f["semantic_similarity"] == 0.0  # empty definition -> name words
    assert not definition_is_valid(c)


def test_scheme_formulas():
    f = {"semantic_similarity": 0.5, "cooccurrence": 1.0, "chapter_proximity": 0.5, "educational_context": 0.25}
    assert combine(f, WEIGHTING_SCHEMES["ahp"]) == round(0.52 * 0.5 + 0.24 + 0.09 * 0.5 + 0.15 * 0.25, 4)
    assert combine(f, WEIGHTING_SCHEMES["cooc_only"]) == 1.0
    assert combine(f, WEIGHTING_SCHEMES["cooc_struct_a0.8"]) == round(0.8 + 0.2 * 0.25, 4)
    for name, w in WEIGHTING_SCHEMES.items():
        assert abs(sum(w.values()) - 1.0) < 1e-9, name  # convex: weights stay in [0, 1]


def test_finalize_stores_all_schemes_and_rejects_unknown():
    n = ConceptNormalizer(definition_policy="first_definitional")
    for c in _concepts()[:2]:
        n.register_concept(c.concept_name, definition=c.definition, definition_kind="definitional",
                           chapter=c.chapter, section=c.section)
    m = RelationManager(n)
    r = m.add_relation("Kite", "Quadrilateral", "Part-of", "A kite is a quadrilateral.", source="keyword")
    m.finalize_weights(_chunks(), scheme="cooc_only")
    assert r.weight == r.scheme_weights["cooc_only"] and set(r.scheme_weights) == set(WEIGHTING_SCHEMES)
    try:
        m.finalize_weights(_chunks(), scheme="tuned_on_test")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_finalize_is_deterministic():
    def run():
        n = ConceptNormalizer(definition_policy="first_definitional")
        for c in _concepts()[:2]:
            n.register_concept(c.concept_name, definition=c.definition, definition_kind="definitional",
                               chapter=c.chapter, section=c.section)
        m = RelationManager(n)
        m.add_relation("Kite", "Quadrilateral", "Part-of", "A kite is a quadrilateral.", source="keyword")
        m.finalize_weights(_chunks())
        return [(r.relation_id, r.weight, r.scheme_weights) for r in m.relations]
    assert run() == run()


def test_concept_candidates_do_not_depend_on_hash_seed():
    # Whole book: with the old `list(set(...))` the candidate order differed for every seed (checked 2026-10-15).
    book = ROOT / "data_input" / "ck12_geometry" / "ck12_basic_geometry_concepts.txt"
    code = ("from educational_pipeline.concept_extractor import extract_candidate_concepts_from_text as f; "
            f"t = open({str(book)!r}).read(); print([f(p) for p in t.split(chr(10) * 2)])")
    outs = {subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                           env={**os.environ, "PYTHONHASHSEED": seed}).stdout for seed in ("1", "2", "3")}
    assert len(outs) == 1, outs


if __name__ == "__main__":
    failed = 0
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            try:
                f()
                print("ok  ", n)
            except AssertionError as e:
                failed += 1
                print("FAIL", n, "->", e)
    sys.exit(1 if failed else 0)
