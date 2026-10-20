"""Shared loading, matching, metrics and safeguards for kg_eval.framework."""

import json
import math
import random
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from educational_pipeline.chunker import create_structure_aware_chunks
from educational_pipeline.normalizer import NormalizedConcept
from educational_pipeline.parser import parse_document
from educational_pipeline.relation_extractor import MentionIndex, definition_is_valid
from educational_pipeline.structure_detector import detect_educational_structures
from evaluate_prerequisite_extraction import build_extracted_concept_index, match_gold_concept

from ..data import DEFAULT_ALCPL_PAIRS, DEFAULT_ALCPL_PREQS, DEFAULT_SOURCE, first_position, load_alcpl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data_output" / "eval_framework"
RELATION_TYPES = ["Prerequisite", "Part-of", "Application", "Similarity", "Extension"]
DIRECTED = {"Prerequisite", "Part-of", "Application", "Extension"}

# The KGs evaluated. Paths are read-only inputs.
KGS = {
    "rule_2026-10-11": {"path": "data_output/ck12_geometry", "desc": "educational_pipeline, rules + neural, before all fixes"},
    "rule_v3": {"path": "data_output/baseline_v3/ck12_geometry", "desc": "educational_pipeline, rules + neural, current code"},
    "kgx_v2": {"path": "data_output/ck12_geometry_kgx_v2", "desc": "kg_extract, qwen2.5:7b concepts + LLM pair votes"},
    "kgx_v2_hybrid": {"path": "data_output/ck12_geometry_kgx_v2_hybrid", "desc": "v2 + hybrid prerequisite edges (uses book order)"},
}


def out_dir(*parts) -> Path:
    p = OUT.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=lambda x: None if isinstance(x, float) and math.isnan(x) else str(x)))


# ---------------------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------------------

class KG:
    def __init__(self, name: str):
        self.name = name
        self.path = ROOT / KGS[name]["path"]
        self.desc = KGS[name]["desc"]
        self.concepts = pd.read_csv(self.path / "concepts.csv", dtype=str, keep_default_na=False)
        self.relations = pd.read_csv(self.path / "relations.csv", dtype=str, keep_default_na=False)
        self.relations["weight_f"] = pd.to_numeric(self.relations["weight"], errors="coerce").fillna(0.0)
        meta = self.path / "run_meta.json"
        self.uses_book_order = json.loads(meta.read_text()).get("uses_book_order", False) if meta.exists() else False
        ps = self.path / "pair_scores.csv"
        self.pair_scores = pd.read_csv(ps, dtype={"source_id": str, "target_id": str}) if ps.exists() else None
        self.name_of = dict(zip(self.concepts.concept_id, self.concepts.concept_name))
        self.objects = {r.concept_id: NormalizedConcept(
            r.concept_id, r.concept_name, aliases={a.strip() for a in r.aliases.split(",") if a.strip()},
            definition=r.definition, chapter=r.chapter, section=r.section) for r in self.concepts.itertuples()}

    def terms(self, cid: str) -> List[str]:
        c = self.objects[cid]
        return [c.concept_name, *sorted(c.aliases)]

    @property
    def mention_index(self) -> MentionIndex:
        if not hasattr(self, "_mi"):
            self._mi = MentionIndex(self.objects.values(), book_chunks())
        return self._mi

    @property
    def valid_definitions(self) -> Dict[str, bool]:
        return {cid: definition_is_valid(c) for cid, c in self.objects.items()}

    @property
    def positions(self) -> Dict[str, Optional[int]]:
        if not hasattr(self, "_pos"):
            text = book_text()
            self._pos = {cid: first_position(self.terms(cid), text) for cid in self.objects}
        return self._pos

    def gold_matches(self, gold: pd.DataFrame) -> Dict[str, dict]:
        """AL-CPL name -> {cid, confidence}. Unmatched names get cid None (never silently treated as negatives)."""
        by_id, term_to_cid, normalizer = build_extracted_concept_index(self.concepts)
        out = {}
        for g in sorted(set(gold.concept) | set(gold.prereq)):
            cid, conf, _, _ = match_gold_concept(g, term_to_cid, by_id, normalizer)
            out[g] = {"cid": cid, "confidence": conf}
        return out


@lru_cache(maxsize=1)
def book_text(source: Path = DEFAULT_SOURCE) -> str:
    return Path(source).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def book_chunks(source: Path = DEFAULT_SOURCE):
    return create_structure_aware_chunks(detect_educational_structures(parse_document(source)))


@lru_cache(maxsize=1)
def book_sentences(source: Path = DEFAULT_SOURCE) -> List[str]:
    """Sentences as the pipeline splits them (after . ? ! inside chunks), heading lines removed."""
    out = []
    for ch in book_chunks(source):
        for line in ch.text.splitlines():
            if re.match(r"^\s*(?:chapter\s+\d+\b.*|\d+(?:\.\d+)+\s+\S.*)$", line, re.I):
                continue
            out += [s.strip() for s in re.split(r"(?<=[.?!])\s+", line) if len(s.strip()) > 3]
    return out


def gold(pairs: Path = DEFAULT_ALCPL_PAIRS, preqs: Path = DEFAULT_ALCPL_PREQS) -> pd.DataFrame:
    return load_alcpl(pairs, preqs)


# ---------------------------------------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------------------------------------

def prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if p == p and r == r and p + r else float("nan")
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def roc_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    s, y = np.asarray(scores, float), np.asarray(labels, int)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()
    return float(gt / (len(pos) * len(neg)))


def _gains(rels: Sequence[int], order: Sequence[int]):
    return [rels[i] for i in order]


def ranking_metrics(scores: Sequence[float], rels: Sequence[int], ks=(5, 10), ties: int = 20, seed: int = 0) -> Dict[str, float]:
    """NDCG@k, P@k, R@k averaged over random tie-breaks (a constant score gives the random-ranking value).
    `rels` are 1 (relevant) / 0 (judged not relevant). Unknown candidates must be removed by the caller or
    passed as 0 with the metric then labelled a lower bound."""
    rng = random.Random(seed)
    idx = list(range(len(scores)))
    n_rel = sum(rels)
    acc = {f"{m}@{k}": [] for k in ks for m in ("ndcg", "p", "r")}
    ideal = sorted(rels, reverse=True)
    for _ in range(ties):
        rng.shuffle(idx)
        order = sorted(idx, key=lambda i: -scores[i])
        g = _gains(rels, order)
        for k in ks:
            dcg = sum(x / math.log2(i + 2) for i, x in enumerate(g[:k]))
            idcg = sum(x / math.log2(i + 2) for i, x in enumerate(ideal[:k]))
            acc[f"ndcg@{k}"].append(dcg / idcg if idcg else float("nan"))
            acc[f"p@{k}"].append(sum(g[:k]) / k)
            acc[f"r@{k}"].append(sum(g[:k]) / n_rel if n_rel else float("nan"))
    return {k: float(np.mean(v)) for k, v in acc.items()}


def pairwise_accuracy(scores: Sequence[float], rels: Sequence[int]) -> float:
    """Share of (relevant, non-relevant) candidate pairs ordered correctly (ties count 1/2) = per-query AUC."""
    return roc_auc(scores, rels)


def cluster_bootstrap_ci(values: Sequence[float], reps: int = 2000, seed: int = 0):
    """95% percentile CI of the mean of per-cluster (e.g. per-query) values."""
    v = np.array([x for x in values if x == x], float)
    if len(v) < 2:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), (reps, len(v)))].mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    c = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    m = (p + z * z / (2 * n)) / (1 + z * z / n)
    return [m - c, m + c]


def sign_flip_p(diffs: Sequence[float], reps: int = 20000, seed: int = 0) -> float:
    d = np.array([x for x in diffs if x == x], float)
    if not len(d) or not d.any():
        return 1.0
    rng = np.random.default_rng(seed)
    flips = rng.choice([-1.0, 1.0], size=(reps, len(d)))
    return float((np.abs((flips * d).mean(axis=1)) >= abs(d.mean()) - 1e-12).mean())


# ---------------------------------------------------------------------------------------------------------
# Safeguard: reference labels must be human annotations, never predictions
# ---------------------------------------------------------------------------------------------------------

class NotAReferenceError(ValueError):
    pass


REFERENCE_REQUIRED = ["item_id", "annotator_id", "label_provenance"]


def load_reference(path: Path, label_col: str = "adjudicated_label", allowed=("yes", "no", "unsure")) -> pd.DataFrame:
    """Loads an adjudicated annotation file and refuses anything that is not human-labelled.

    Required: REFERENCE_REQUIRED + `label_col`; label_provenance must be 'human' on every row; annotator_id non-empty;
    labels in `allowed` (case-insensitive). A file derived from KG predictions (e.g. relations.csv) fails."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in REFERENCE_REQUIRED + [label_col] if c not in df.columns]
    if missing:
        raise NotAReferenceError(f"{path}: missing columns {missing}; not an adjudicated human annotation file")
    if df.empty:
        raise NotAReferenceError(f"{path}: no rows")
    bad = df[(df.label_provenance.str.lower() != "human") | (df.annotator_id.str.strip() == "")]
    if len(bad):
        raise NotAReferenceError(f"{path}: {len(bad)} rows are not human-annotated (label_provenance/annotator_id)")
    ok = {a.lower() for a in allowed}
    if not df[label_col].str.lower().isin(ok).all():
        raise NotAReferenceError(f"{path}: {label_col} must be one of {sorted(ok)}")
    return df
