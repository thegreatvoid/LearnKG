"""Regression tests for the keyword path of RelationManager.extract_relations_from_sentences.

Run: python educational_pipeline/test_keyword_path.py   (or with pytest)

Bug 1: a sentence that names two concepts and a Part-of / Application / Extension keyword produced no edge (only the
       Prerequisite and Similarity branches called add_relation).
Bug 2: a Similarity keyword sentence called add_relation twice for the same ordered pair, so one sentence counted as
       two proposals.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from educational_pipeline.normalizer import ConceptNormalizer
from educational_pipeline.relation_extractor import RelationManager


def manager(*names):
    n = ConceptNormalizer()
    for i, name in enumerate(names):
        n.register_concept(name, chapter="Chapter 1: Basics", section="1.1 Test", page=1 + i)
    m = RelationManager(n)
    calls = Counter()
    original = m.add_relation

    def counting_add(source_name, target_name, relation_type, *a, **k):
        calls[(source_name.lower(), target_name.lower(), relation_type)] += 1
        return original(source_name, target_name, relation_type, *a, **k)

    m.add_relation = counting_add
    return m, calls


def edges(m):
    name = {c.concept_id: c.concept_name.lower() for c in m.normalizer.get_all_concepts()}
    return {(name[r.source_id], name[r.target_id], r.relation_type) for r in m.relations}


def test_part_of_keyword_creates_edge():
    m, _ = manager("Kite", "Quadrilateral")
    m.extract_relations_from_sentences(["A kite is a type of quadrilateral with two pairs of adjacent sides."], 1, "c1")
    assert ("kite", "quadrilateral", "Part-of") in edges(m), edges(m)


def test_application_keyword_creates_edge():
    m, _ = manager("Distance Formula", "Segment")
    m.extract_relations_from_sentences(["The distance formula is used to find the length of a segment."], 1, "c1")
    assert ("distance formula", "segment", "Application") in edges(m), edges(m)


def test_extension_keyword_creates_edge():
    m, _ = manager("Square", "Rhombus")
    m.extract_relations_from_sentences(["A square is a special case of a rhombus with four right angles."], 1, "c1")
    assert ("square", "rhombus", "Extension") in edges(m), edges(m)


def test_passive_keyword_reverses_direction():
    m, _ = manager("Circle", "Center")
    m.extract_relations_from_sentences(["A circle includes its center as the reference point."], 1, "c1")
    assert ("center", "circle", "Part-of") in edges(m), edges(m)
    assert ("circle", "center", "Part-of") not in edges(m)


def test_keyword_without_direction_evidence_is_skipped():
    # both concepts on the same side of the keyword: the sentence does not say which is part of which
    m, _ = manager("Kite", "Quadrilateral")
    m.extract_relations_from_sentences(["A kite and a quadrilateral are both part of this chapter."], 1, "c1")
    assert not any(t == "Part-of" for *_, t in edges(m)), edges(m)


def test_similarity_sentence_is_one_proposal():
    m, calls = manager("Square", "Rectangle")
    m.extract_relations_from_sentences(["A square is similar to a rectangle in many ways."], 1, "c1")
    sim = {k: v for k, v in calls.items() if k[2] == "Similarity"}
    assert sum(sim.values()) == 1, sim


def test_keyword_must_be_a_whole_word():
    m, _ = manager("Square", "Rectangle")
    m.extract_relations_from_sentences(["Unlike a square, a rectangle need not have equal sides."], 1, "c1")
    assert not edges(m), edges(m)


def test_same_rule_same_sentence_counts_once_but_new_evidence_counts():
    m, _ = manager("Kite", "Quadrilateral")
    m.add_relation("Kite", "Quadrilateral", "Part-of", "s1", source="rule")
    m.add_relation("Kite", "Quadrilateral", "Part-of", "s1", source="rule")      # same rule, same sentence
    r = m.add_relation("Kite", "Quadrilateral", "Part-of", "s2", source="rule")  # new sentence
    r = m.add_relation("Kite", "Quadrilateral", "Part-of", "s1", source="keyword")  # other source, kept
    assert r.n_proposals == 3 and r.evidence_all == ["s1", "s2"] and r.sources == {"rule", "keyword"}, r


def test_extractor_scores_are_stored_not_used_as_weight():
    from types import SimpleNamespace
    m, _ = manager("Kite", "Quadrilateral")
    r = m.add_relation("Kite", "Quadrilateral", "Prerequisite", "s1", weight=0.9, source="neural")
    m.add_relation("Kite", "Quadrilateral", "Prerequisite", "s2", weight=8, source="llm")
    m.finalize_weights([SimpleNamespace(text="A kite is a quadrilateral.", section="1.1 Test")])
    assert r.extractor_scores == {"neural": 0.9, "llm": 8.0}, r.extractor_scores
    assert r.weight_source == "ahp" and 0.0 <= r.weight <= 1.0 and r.weight != 0.9


def test_cooccurrence_counts_sentences_not_proposals():
    from types import SimpleNamespace
    m, _ = manager("Kite", "Quadrilateral")
    for i in range(5):  # five proposals from five sentences that are not in the text
        m.add_relation("Kite", "Quadrilateral", "Part-of", f"s{i}", source="rule")
    m.finalize_weights([SimpleNamespace(text="A kite is a quadrilateral. A kite has two pairs of sides.", section="1.1")])
    r = m.relations[0]
    assert r.cooccurrence_count == 1 and r.n_proposals == 5, (r.cooccurrence_count, r.n_proposals)


def test_definition_validation_rejects_mention_only():
    from educational_pipeline.relation_extractor import definition_is_valid
    from educational_pipeline.normalizer import NormalizedConcept
    good = NormalizedConcept("C1", "Line", definition="A line is a straight one-dimensional figure.")
    bad = NormalizedConcept("C2", "Line", definition="A linear pair is two adjacent angles that form a straight line.")
    head = NormalizedConcept("C3", "Ray", definition="1.3 Rays and Angles\nA ray has one endpoint.")
    # a leading section-heading line is ignored, so the ray sentence counts as its definition
    assert definition_is_valid(good) and not definition_is_valid(bad) and definition_is_valid(head)


def test_chapter_proximity_distance_and_missing():
    from educational_pipeline.relation_extractor import chapter_proximity
    from educational_pipeline.normalizer import NormalizedConcept
    a = NormalizedConcept("C1", "A", chapter="Chapter 2: X")
    b = NormalizedConcept("C2", "B", chapter="Chapter 5: Y")
    c = NormalizedConcept("C3", "C", chapter="")
    assert chapter_proximity(a, b) == 0.25 and chapter_proximity(a, a) == 1.0 and chapter_proximity(a, c) == 0.5


def test_reverse_directed_edges_stay_distinct():
    m, _ = manager("Kite", "Quadrilateral")
    m.add_relation("Kite", "Quadrilateral", "Part-of", "s1")
    m.add_relation("Quadrilateral", "Kite", "Part-of", "s2")
    assert {("kite", "quadrilateral", "Part-of"), ("quadrilateral", "kite", "Part-of")} <= edges(m)


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
