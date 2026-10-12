"""Offline unit tests (fake backend). Run: python -m pytest kg_extract/test_kg_extract.py  (or python kg_extract/test_kg_extract.py)"""

import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg_extract.backend import BackendError
from kg_extract.concepts import extract_concepts
from kg_extract.consistency import enforce_dag, make_consistent
from kg_extract.pairs import generate_candidates
from kg_extract.score import score_pairs

TEXT = ("A point is a location with no dimension. A line is a set of points that extends forever. "
        "A line segment is part of a line with two endpoints. The midpoint divides a line segment into two equal parts.")


def chunk(text=TEXT, section="1.1 Points and Lines"):
    return SimpleNamespace(text=text, section=section, chapter="Chapter 1: Basics", page=1, chunk_id="c1")


class FakeBackend:
    def __init__(self, responses):
        self.responses, self.counters, self.calls = list(responses), Counter(), 0

    def chat_json(self, system, user, schema, temperature=0.0, seed=None):
        self.calls += 1
        r = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(r, Exception):
            self.counters["llm_fail"] += 1
            raise r
        self.counters["llm_ok"] += 1
        return r


def test_grounding_drops_invented_concepts():
    be = FakeBackend([{"concepts": [{"name": "Point", "definition_sentence": "A point is a location with no dimension."},
                                    {"name": "Hyperbolic Manifold", "definition_sentence": "made up"}]}])
    c = Counter()
    norm, _ = extract_concepts([chunk()], be, TEXT, counters=c)
    names = {x.concept_name.lower() for x in norm.get_all_concepts()}
    assert "point" in names and "hyperbolic manifold" not in names
    assert c["candidates_dropped_ungrounded"] >= 1


def test_no_ground_ablation_keeps_invented():
    be = FakeBackend([{"concepts": [{"name": "Hyperbolic Manifold", "definition_sentence": ""}]}])
    norm, _ = extract_concepts([chunk()], be, TEXT, ground=False, min_freq=0)
    assert "hyperbolic manifold" in {x.concept_name.lower() for x in norm.get_all_concepts()}


def test_llm_failure_is_counted_not_swallowed():
    be = FakeBackend([BackendError("boom")])
    c = Counter()
    extract_concepts([chunk()], be, TEXT, counters=c)
    assert c["chunks_llm_failed"] == 1


def test_dag_enforcement_removes_lowest_edge_of_cycle():
    edges = [("a", "b", "Prerequisite", 0.9), ("b", "c", "Prerequisite", 0.8), ("c", "a", "Prerequisite", 0.6),
             ("a", "c", "Similarity", 0.7)]
    kept, dropped = enforce_dag(edges, "Prerequisite")
    assert dropped == [("c", "a", "Prerequisite", 0.6)]
    assert ("a", "c", "Similarity", 0.7) in kept and len(kept) == 3


def test_one_label_per_pair_and_threshold():
    scores = {("a", "b"): {"Prerequisite": 0.7, "Part-of": 0.4}, ("b", "a"): {"Prerequisite": 0.2}}
    edges, _ = make_consistent(scores, 0.5)
    assert edges == [("a", "b", "Prerequisite", 0.7)]


def test_pair_scoring_votes_and_order_swap():
    norm, _ = extract_concepts([chunk()], None, TEXT)
    cands = generate_candidates(norm, [chunk()])
    assert cands
    names = {c.concept_name.lower(): c.concept_id for c in norm.get_all_concepts()}
    # model always says "A is a prerequisite of B" -> with swapped sample, direction flips, so votes split.
    be = FakeBackend([{"relation": "Prerequisite", "source": "A", "confidence": 1.0}])
    scores, meta = score_pairs(be, norm, cands[:1], samples=2)
    a, b = cands[0]["a"], cands[0]["b"]
    assert abs(scores[(a, b)]["Prerequisite"] - 0.5) < 1e-9 and abs(scores[(b, a)]["Prerequisite"] - 0.5) < 1e-9


def test_heading_terms_keep_topic_nouns():
    from kg_extract.concepts import heading_terms
    assert heading_terms("4.5 Isosceles and Equilateral Triangles") == [
        ("Isosceles Triangles", "heading"), ("Equilateral Triangles", "heading")]
    assert heading_terms("3.2 Properties of Parallel Lines") == [("Properties", "heading_part"), ("Parallel Lines", "heading")]
    assert heading_terms("1.5 Classifying Triangles") == [("Triangles", "heading")]


def test_definition_patterns():
    from kg_extract.concepts import rule_candidates
    text = ("A ray is part of a line. Two angles that are not adjacent are called remote interior angles. "
            "SOH CAH TOA is the mnemonic for the ratios. A protractor is used to measure angles. "
            "Angles are called acute when they are small.")
    got = {k for k, v in rule_candidates(chunk(text, section=""), None).items() if "definition" in v["cues"]}
    assert {"ray", "remote interior angles"} <= got
    assert not got & {"remote", "soh cah toa", "protractor", "gles", "angles"}


def test_candidate_report_and_defined_single_word_kept():
    text = "A ray is part of a line. The sides of a figure meet."
    norm, rep = extract_concepts([chunk(text, section="")], None, text)
    assert "ray" in {c.concept_name.lower() for c in norm.get_all_concepts()}
    assert {"name", "cues", "freq", "salience", "dropped"} <= set(rep["candidates"][0])


def test_concept_precision_judge(tmp_path=None):
    import tempfile
    import pandas as pd
    from kg_eval.concept_quality import judge_concepts, precision_report
    concepts = pd.DataFrame({"concept_name": ["ray", "times", "rays"], "evidence": ["A ray is part of a line.", "", ""],
                             "definition": ["", "", ""]})
    be = FakeBackend([{"judgments": [{"name": "ray", "verdict": "concept", "same_as": ""},
                                     {"name": "times", "verdict": "not_concept", "same_as": ""},
                                     {"name": "rays", "verdict": "duplicate", "same_as": "ray"}]}])
    be.model = "fake"
    cache = Path(tempfile.mkdtemp()) / "cache.jsonl"
    rep = precision_report(judge_concepts(concepts, be, "geometry", cache))
    assert rep["judged"] == 3 and abs(rep["concept_precision"] - 1 / 3) < 1e-9 and rep["not_concept"] == ["times"]
    judge_concepts(concepts, be, "geometry", cache)  # second run is served from the cache
    assert be.calls == 1


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)
