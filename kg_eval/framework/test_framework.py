"""Tests for kg_eval.framework (metrics, conventions, safeguards, reproducibility).

Run: python kg_eval/framework/test_framework.py   (or with pytest)
All data below are synthetic fixtures for testing code paths; none are used as evaluation labels.
"""

import math
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from kg_eval.framework import common
from kg_eval.framework.annotation_kit import confusion, kappa
from kg_eval.framework.common import (KG, KGS, NotAReferenceError, load_reference, prf, ranking_metrics, roc_auc,
                                      wilson)
from kg_eval.framework.prereq_eval import pair_table
from kg_eval.framework.relation_checks import cue_direction, cycle_edges, term_re


# ---------------- metrics ----------------

def test_prf_and_empty_cases():
    m = prf(3, 1, 2)
    assert m["precision"] == 0.75 and m["recall"] == 0.6 and abs(m["f1"] - 2 * 0.75 * 0.6 / 1.35) < 1e-12
    e = prf(0, 0, 0)
    assert math.isnan(e["precision"]) and math.isnan(e["recall"]) and math.isnan(e["f1"])


def test_auc_ties_and_degenerate():
    assert roc_auc([0.9, 0.1], [1, 0]) == 1.0
    assert roc_auc([0.5, 0.5], [1, 0]) == 0.5
    assert math.isnan(roc_auc([0.2, 0.3], [1, 1]))  # no negatives


def test_ranking_metrics_perfect_and_constant():
    r = ranking_metrics([3, 2, 1, 0], [1, 1, 0, 0], ks=(2,))
    assert r["ndcg@2"] == 1.0 and r["p@2"] == 1.0 and r["r@2"] == 1.0
    c = ranking_metrics([0, 0, 0, 0], [1, 0, 0, 0], ks=(1,), ties=2000)
    assert abs(c["p@1"] - 0.25) < 0.05  # constant score = random ranking, not a lucky order


def test_ranking_is_reproducible():
    args = ([0.3, 0.3, 0.1, 0.7], [0, 1, 0, 1])
    assert ranking_metrics(*args) == ranking_metrics(*args)


def test_wilson_bounds():
    lo, hi = wilson(7, 7)
    assert 0.6 < lo < 1.0 and hi > 0.99
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_kappa():
    assert kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


# ---------------- direction conventions, symmetry, cycles ----------------

def test_cue_direction_forward_and_reverse():
    s, t = term_re(["radius"]), term_re(["circle"])
    assert cue_direction("A radius is part of a circle.", s, t, "Part-of") == "supports"
    assert cue_direction("A circle has a radius.", s, t, "Part-of") == "supports"      # reverse cue, reversed order
    assert cue_direction("A radius has a circle.", s, t, "Part-of") == "reverse"
    assert cue_direction("A radius and a circle.", s, t, "Part-of") == "none"


def test_cycle_detection():
    on = cycle_edges([("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")])
    assert on == {("a", "b"), ("b", "c"), ("c", "a")}


def _ref(rows):
    return pd.DataFrame(rows, columns=["concept_A", "concept_B", "adjudicated_relation", "adjudicated_direction"])


def test_similarity_is_undirected_and_directed_types_are_not():
    idx = {"sine": "C1", "cosine": "C2", "radius": "C3", "circle": "C4", "kite": "C5"}
    rel = {("C2", "C1", "Similarity"), ("C4", "C3", "Part-of")}  # Part-of stored in the WRONG direction
    ref = _ref([["sine", "cosine", "Similarity", "undirected"], ["radius", "circle", "Part-of", "A->B"],
                ["kite", "circle", "None", "n/a"], ["hendecagon", "circle", "Part-of", "A->B"]])
    assert confusion(ref, idx, rel, "Similarity")[:3] == (1, 0, 0)          # reversed storage is fine
    tp, fp, fn, dir_err, covered = confusion(ref, idx, rel, "Part-of")
    assert (tp, fp, fn, dir_err) == (0, 1, 1, 1)                            # wrong direction = FP + FN
    assert covered == 3                                                      # unknown concept skipped, not a negative


# ---------------- safeguards ----------------

def _write(df):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    df.to_csv(f.name, index=False)
    return Path(f.name)


def test_predictions_are_refused_as_reference():
    rel = Path(common.ROOT / "data_output/baseline_v3/ck12_geometry/relations.csv")
    try:
        load_reference(rel)
    except NotAReferenceError:
        pass
    else:
        raise AssertionError("relations.csv must not load as a reference")


def test_empty_and_non_human_references_are_refused():
    cols = ["item_id", "annotator_id", "label_provenance", "adjudicated_label"]
    for df in (pd.DataFrame(columns=cols),
               pd.DataFrame([["R1", "A1", "model", "yes"]], columns=cols),
               pd.DataFrame([["R1", "", "human", "yes"]], columns=cols),
               pd.DataFrame([["R1", "A1", "human", "maybe"]], columns=cols)):
        try:
            load_reference(_write(df))
        except NotAReferenceError:
            continue
        raise AssertionError(f"should refuse:\n{df}")
    ok = load_reference(_write(pd.DataFrame([["R1", "A1+A2", "human", "yes"]], columns=cols)))
    assert len(ok) == 1


def test_blind_items_hide_origin():
    d = common.OUT / "annotation" / "relations"
    if not (d / "relation_items_BLIND.csv").exists():
        return  # built by `annotation_kit build`
    blind = pd.read_csv(d / "relation_items_BLIND.csv")
    assert not {"origin", "relation_type", "weight", "source_id"} & set(blind.columns)
    key = pd.read_csv(d / "relation_items_KEY_do_not_show_annotators.csv")
    share = (key.origin_direction_in_item == "A->B").mean()
    assert 0.3 < share < 0.7, share  # pair order is randomised, so column order leaks no direction


# ---------------- prerequisite protocol: missing concepts, unknown labels, duplicates ----------------

def _tiny_kg():
    d = Path(tempfile.mkdtemp())
    pd.DataFrame([["C1", "Point", "", "c", "", "", "", "1", "", ""], ["C2", "Line", "", "c", "", "", "", "1", "", ""],
                  ["C3", "Plane", "", "c", "", "", "", "1", "", ""], ["C4", "Kite", "", "c", "", "", "", "1", "", ""]],
                 columns=["concept_id", "concept_name", "aliases", "concept_type", "definition", "chapter", "section",
                          "page", "chunk_id", "evidence"]).to_csv(d / "concepts.csv", index=False)
    pd.DataFrame([["R1", "C1", "C2", "Prerequisite", "0.5", "", "", ""],
                  ["R2", "C1", "C2", "Prerequisite", "0.5", "", "", ""],   # duplicate row
                  ["R3", "C4", "C3", "Prerequisite", "0.4", "", "", ""]],  # pair AL-CPL never labelled
                 columns=["relation_id", "source_id", "target_id", "relation_type", "weight", "page", "chunk_id",
                          "evidence"]).to_csv(d / "relations.csv", index=False)
    KGS["_test"] = {"path": str(d), "desc": "test fixture"}
    return KG("_test")


def test_missing_concepts_are_not_negatives_and_unknown_edges_are_counted():
    kg = _tiny_kg()
    g = pd.DataFrame([["Line", "Point", 1], ["Plane", "Line", 1], ["Hendecagon", "Point", 0]],
                     columns=["concept", "prereq", "label"])
    t, unknown, _, n_edges = pair_table(kg, g)
    assert list(t.covered) == [True, True, False]                 # Hendecagon not in KG -> uncovered, not a negative
    assert t.loc[0, "edge"] == 1 and t.loc[1, "edge"] == 0
    assert unknown == 1                                           # Kite -> Plane: unlabelled, not a false positive
    assert n_edges == 2                                           # duplicate row counted once
    del KGS["_test"]


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
