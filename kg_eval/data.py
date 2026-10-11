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
    """
    Loads concepts.csv / relations.csv and adapts other layouts (e.g. Colab notebook output) to the
    pipeline schema: concept name column may be name/concept/node, IDs are generated if missing,
    relations may reference concepts by name (source/target, source_name/target_name, node_1/node_2)
    and the type column may be relationship/edge/relation. Missing weights default to 5.
    Relation endpoints absent from concepts.csv are added as bare concepts.
    """
    kg_dir = Path(kg_dir)
    concepts = pd.read_csv(kg_dir / "concepts.csv", dtype=str, keep_default_na=False)
    relations = pd.read_csv(kg_dir / "relations.csv", dtype=str, keep_default_na=False)

    def rename_first(df, target, alts):
        if target not in df.columns:
            for a in alts:
                if a in df.columns:
                    return df.rename(columns={a: target})
        return df

    concepts = rename_first(concepts, "concept_name", ("name", "concept", "node"))
    if "concept_name" not in concepts.columns:
        raise ValueError(f"concepts.csv needs a concept name column (found {list(concepts.columns)})")
    concepts["concept_name"] = concepts["concept_name"].str.strip()
    concepts = concepts[concepts["concept_name"] != ""].drop_duplicates(subset="concept_name").reset_index(drop=True)
    if "concept_id" not in concepts.columns:
        concepts.insert(0, "concept_id", [f"C{i:04d}" for i in range(1, len(concepts) + 1)])
    for col in ("aliases", "concept_type", "definition", "chapter", "section", "page", "chunk_id", "evidence"):
        if col not in concepts.columns:
            concepts[col] = ""

    if not {"source_id", "target_id"} <= set(relations.columns):
        src = next((c for c in ("source", "source_name", "node_1") if c in relations.columns), None)
        tgt = next((c for c in ("target", "target_name", "node_2") if c in relations.columns), None)
        if not src or not tgt:
            raise ValueError(f"relations.csv needs source_id/target_id or source/target names (found {list(relations.columns)})")
        name_to_id = {n.lower(): i for n, i in zip(concepts["concept_name"], concepts["concept_id"])}
        extra = []
        for n in pd.concat([relations[src], relations[tgt]]).str.strip().unique():
            if n and n.lower() not in name_to_id:
                name_to_id[n.lower()] = f"C{len(concepts) + len(extra) + 1:04d}"
                extra.append({"concept_id": name_to_id[n.lower()], "concept_name": n})
        if extra:
            print(f"[!] {len(extra)} relation endpoints missing from concepts.csv were added as bare concepts.")
            concepts = pd.concat([concepts, pd.DataFrame(extra)], ignore_index=True).fillna("")
        relations["source_id"] = relations[src].str.strip().str.lower().map(name_to_id).fillna("")
        relations["target_id"] = relations[tgt].str.strip().str.lower().map(name_to_id).fillna("")
    relations = rename_first(relations, "relation_type", ("relationship", "edge", "relation"))
    for col in ("relation_id", "relation_type", "weight", "evidence"):
        if col not in relations.columns:
            relations[col] = ""
    if not relations["relation_id"].str.strip().any():
        relations["relation_id"] = [f"R{i:04d}" for i in range(1, len(relations) + 1)]
    relations["relation_type"] = relations["relation_type"].str.strip()
    relations["weight"] = pd.to_numeric(relations["weight"], errors="coerce").fillna(5.0).astype(str)
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


def average_precision(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Step-wise AP (area under PR curve), ties at the same score handled as one threshold."""
    pos = sum(labels)
    if pos == 0:
        return float("nan")
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    ap, tp, seen, prev_recall, i = 0.0, 0, 0, 0.0, 0
    while i < len(order):
        j = i
        while j < len(order) and scores[order[j]] == scores[order[i]]:
            tp += labels[order[j]]
            j += 1
        seen = j
        recall = tp / pos
        ap += (recall - prev_recall) * (tp / seen)
        prev_recall, i = recall, j
    return ap


def prf(pred: Sequence[int], labels: Sequence[int]) -> Dict[str, float]:
    tp = sum(1 for p, l in zip(pred, labels) if p and l)
    fp = sum(1 for p, l in zip(pred, labels) if p and not l)
    fn = sum(1 for p, l in zip(pred, labels) if not p and l)
    tn = len(labels) - tp - fp - fn
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    den = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    mcc = (tp * tn - fp * fn) / den if den else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f1, "mcc": mcc}


# ---------- AL-CPL gold and textbook positions ----------

DEFAULT_ALCPL_PAIRS = ROOT / "data_input" / "ck12_geometry" / "geometry.pairs"
DEFAULT_ALCPL_PREQS = ROOT / "data_input" / "ck12_geometry" / "geometry.preqs"


def load_alcpl(pairs_path: Path = DEFAULT_ALCPL_PAIRS, preqs_path: Path = DEFAULT_ALCPL_PREQS) -> pd.DataFrame:
    """
    AL-CPL (Liang et al., AAAI 2018). A line "A,B" means B is a prerequisite of A.
    Returns columns: concept (A), prereq (B), label (1 if B is a prerequisite of A).
    """
    def read(p):
        return [tuple(x.strip() for x in l.split(",", 1)) for l in Path(p).read_text(encoding="utf-8").splitlines() if "," in l]
    positives = set(read(preqs_path))
    rows = [{"concept": a, "prereq": b, "label": int((a, b) in positives)} for a, b in read(pairs_path)]
    return pd.DataFrame(rows).drop_duplicates(subset=["concept", "prereq"]).reset_index(drop=True)


def term_pattern(term: str) -> Optional[re.Pattern]:
    """Case-insensitive whole-word pattern tolerating a plural suffix and flexible spacing/hyphens."""
    words = re.findall(r"[a-z0-9]+", str(term).lower())
    if not words:
        return None
    body = r"[\s\-]+".join(re.escape(w) for w in words)
    return re.compile(rf"\b{body}(?:s|es)?\b", re.IGNORECASE)


def first_position(terms: Sequence[str], text: str) -> Optional[int]:
    """Earliest character offset at which any of the terms is mentioned, or None."""
    best = None
    for t in terms:
        pat = term_pattern(t)
        m = pat.search(text) if pat else None
        if m and (best is None or m.start() < best):
            best = m.start()
    return best


def section_starts(text: str) -> List[int]:
    """Character offsets of numbered section headings such as '1.2 Segments and Distance'."""
    return [m.start() for m in re.finditer(r"^\d+\.\d+\s+\S", text, re.MULTILINE)]


def section_index(pos: Optional[int], starts: Sequence[int]) -> Optional[int]:
    if pos is None:
        return None
    idx = 0
    for k, s in enumerate(starts):
        if s <= pos:
            idx = k + 1
    return idx


def concept_terms(concepts: pd.DataFrame) -> Dict[str, List[str]]:
    """concept_id -> [name, *aliases]."""
    out = {}
    for _, r in concepts.iterrows():
        aliases = [a.strip() for a in str(r.get("aliases", "")).split(",") if a.strip()]
        out[r["concept_id"]] = [r["concept_name"], *aliases]
    return out


def read_jsonl(path: Path) -> List[dict]:
    p = Path(path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def fmt(x, nd=3):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"
