"""Shared loading helpers, text utilities and statistics for kg_eval."""

import json
import math
import random
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import pandas as pd
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KG_DIR = ROOT / "data_output" / "ck12_geometry"
DEFAULT_SOURCE = ROOT / "data_input" / "ck12_geometry" / "ck12_basic_geometry_concepts.txt"
DEFAULT_GOLD = ROOT / "data_input" / "ck12_geometry" / "gold_pairs.csv"
DEFAULT_OUT = ROOT / "data_output" / "ck12_geometry" / "kg_eval"


def load_kg(kg_dir: Path = DEFAULT_KG_DIR):
    concepts = pd.read_csv(kg_dir / "concepts.csv", dtype=str, keep_default_na=False)
    relations = pd.read_csv(kg_dir / "relations.csv", dtype=str, keep_default_na=False)
    return concepts, relations


def read_source(path: Path = DEFAULT_SOURCE) -> str:
    return Path(path).read_text(encoding="utf-8")


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 3]


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(s).lower().replace("_", " ")).strip()


def chapter_number(label: str) -> Optional[int]:
    m = re.search(r"Chapter\s+(\d+)", str(label))
    return int(m.group(1)) if m else None


def edge_table(concepts: pd.DataFrame, relations: pd.DataFrame) -> pd.DataFrame:
    """Relations joined with endpoint names, definitions and chapters."""
    c = concepts.set_index("concept_id")
    df = relations.copy()
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    for side in ("source", "target"):
        ids = df[f"{side}_id"]
        df[f"{side}_name"] = ids.map(c["concept_name"])
        df[f"{side}_chapter"] = ids.map(c["chapter"])
    df["edge_chapter"] = [
        chapter_number(s) or chapter_number(t)
        for s, t in zip(df["source_chapter"].fillna(""), df["target_chapter"].fillna(""))
    ]
    return df


def verbalize(row) -> str:
    return f'({row["source_name"]}) --[{row["relation_type"]}]--> ({row["target_name"]})'


RELATION_SEMANTICS = {
    "Prerequisite": "source must be understood BEFORE target",
    "Part-of": "source is a component/part of target (or target is a part of source in the hierarchy)",
    "Application": "source is applied in / used by target",
    "Extension": "target extends or generalizes source",
    "Similarity": "source and target are similar, analogous or contrasted",
}


# ---------- statistics ----------

def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return float("nan")
    return float(spearmanr(x, y).statistic)


def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    s, l = list(scores), list(labels)
    pos = sum(l)
    neg = len(l) - pos
    if pos == 0 or neg == 0:
        return float("nan")
    r = rankdata(s)
    return float((sum(r[i] for i in range(len(l)) if l[i]) - pos * (pos + 1) / 2) / (pos * neg))


def bootstrap_ci(stat: Callable[[List[int]], float], n: int, reps: int = 2000, seed: int = 0, alpha: float = 0.05):
    """Percentile CI of stat(idx) over resamples of range(n)."""
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        v = stat([rng.randrange(n) for _ in range(n)])
        if not math.isnan(v):
            vals.append(v)
    if len(vals) < reps * 0.5:
        return (float("nan"), float("nan"))
    vals.sort()
    return (vals[int(alpha / 2 * len(vals))], vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))])


def read_jsonl(path: Path) -> List[dict]:
    p = Path(path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def fmt(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"
