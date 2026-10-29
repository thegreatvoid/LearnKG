"""
Unified Positive-Only Prerequisite Evaluation Module for LearnKG

Supports both PRAT and CK-12 Geometry (and other datasets) via clean dataset configuration
and CLI arguments without duplicating the evaluation algorithm or synthesizing negative pairs.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from evaluate_prerequisite_extraction import (
    build_extracted_concept_index,
    match_gold_concept,
)
from kg_eval.data import load_kg

# Dataset Registry
DATASET_CONFIGS = {
    "prat": {
        "dataset_name": "PRAT",
        "kg_dir": Path("data_output/PRAT"),
        "gold_pairs_path": Path("data_input/PRAT/GOLD-PR_PairsOnly.tsv"),
        "gold_concepts_path": Path("data_input/PRAT/GOLD-PR_Concepts.txt"),
        "format": "tsv",  # PREREQUISITE \t TARGET
        "source_col_idx": 0,
        "target_col_idx": 1,
        "line_direction": "prereq_target",  # col 0 is prerequisite, col 1 is target
    },
    "geometry": {
        "dataset_name": "CK-12 Geometry",
        "kg_dir": Path("data_output/ck12_geometry"),
        "gold_pairs_path": Path("data_input/ck12_geometry/geometry.preqs"),
        "gold_concepts_path": None,  # extracted from gold pair endpoints
        "format": "alcpl_preqs",  # line format: "concept,prereq" meaning prereq -> concept
        "line_direction": "target_prereq",  # col 0 is target concept, col 1 is prerequisite
    },
    "geometry_cleaned": {
        "dataset_name": "CK-12 Geometry (Cleaned)",
        "kg_dir": Path("data_output/ck12_geometry"),
        "gold_pairs_path": Path("data_input/ck12_geometry_cleaned/geometry.preqs"),
        "gold_concepts_path": None,
        "format": "alcpl_preqs",
        "line_direction": "target_prereq",
    },
}


def load_dataset_gold_pairs(
    gold_pairs_path: Path,
    file_format: str = "tsv",
    line_direction: str = "prereq_target",
    gold_concepts_path: Optional[Path] = None,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Loads gold concepts and unique directed prerequisite pairs (prereq -> target).

    Returns:
      (gold_concepts_list, unique_directed_pairs [(prereq, target), ...])
    """
    gold_pairs_path = Path(gold_pairs_path)
    if not gold_pairs_path.exists():
        raise FileNotFoundError(f"Gold pairs file not found at: {gold_pairs_path}")

    pairs: List[Tuple[str, str]] = []

    if file_format == "tsv" or gold_pairs_path.suffix.lower() == ".tsv":
        df = pd.read_csv(gold_pairs_path, sep="\t")
        col0 = df.columns[0]
        col1 = df.columns[1]
        for _, row in df.iterrows():
            c0 = str(row[col0]).strip()
            c1 = str(row[col1]).strip()
            if c0 and c1:
                if line_direction == "prereq_target":
                    pairs.append((c0, c1))
                else:
                    pairs.append((c1, c0))
    elif file_format in ("alcpl_preqs", "csv") or gold_pairs_path.suffix.lower() in (".preqs", ".pairs", ".csv"):
        lines = [l.strip() for l in gold_pairs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        for l in lines:
            if "," in l:
                parts = [p.strip() for p in l.split(",", 1)]
                c0, c1 = parts[0], parts[1]
                if line_direction == "target_prereq":
                    # AL-CPL convention: "A,B" means B is prerequisite of A (B -> A)
                    pairs.append((c1, c0))
                else:
                    pairs.append((c0, c1))
            elif "\t" in l:
                parts = [p.strip() for p in l.split("\t", 1)]
                c0, c1 = parts[0], parts[1]
                if line_direction == "target_prereq":
                    pairs.append((c1, c0))
                else:
                    pairs.append((c0, c1))

    unique_pairs = sorted(list(set(pairs)))

    # Determine gold concept vocabulary
    if gold_concepts_path and Path(gold_concepts_path).exists():
        gold_concepts = [
            l.strip()
            for l in Path(gold_concepts_path).read_text(encoding="utf-8").splitlines()
            if l.strip()
        ]
    else:
        # Extract vocabulary from endpoints of pairs
        endpoint_set = set()
        for p, t in unique_pairs:
            endpoint_set.add(p)
            endpoint_set.add(t)
        gold_concepts = sorted(list(endpoint_set))

    return gold_concepts, unique_pairs


def evaluate_positive_only(
    kg_dir: Path,
    gold_pairs_path: Path,
    gold_concepts_path: Optional[Path] = None,
    dataset_name: str = "dataset",
    file_format: str = "tsv",
    line_direction: str = "prereq_target",
    output_report_json: Optional[Path] = None,
    output_report_md: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates extracted prerequisite relationships against positive-only gold pairs.

    Directionality convention:
      Gold internal: (prerequisite, target) meaning prerequisite -> target
      Predicted KG: (source_id, target_id) where relation_type == 'Prerequisite'
    """
    kg_dir = Path(kg_dir)
    gold_pairs_path = Path(gold_pairs_path)

    # 1. Load extracted KG
    concepts_df, relations_df = load_kg(kg_dir)
    prereq_relations = relations_df[
        relations_df["relation_type"].str.strip().str.lower() == "prerequisite"
    ].copy()

    concepts_by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts_df)

    # 2. Load gold concepts & unique directed positive pairs (prereq -> target)
    gold_concepts, unique_gold_pairs = load_dataset_gold_pairs(
        gold_pairs_path=gold_pairs_path,
        file_format=file_format,
        line_direction=line_direction,
        gold_concepts_path=gold_concepts_path,
    )

    # 3. Map gold concepts to extracted KG concepts
    gold_to_cid: Dict[str, Optional[str]] = {}
    gold_to_match_info: Dict[str, Dict[str, Any]] = {}
    for gc in gold_concepts:
        cid, conf, score, notes = match_gold_concept(gc, term_to_cid, concepts_by_id, normalizer)
        gold_to_cid[gc] = cid
        gold_to_match_info[gc] = {
            "matched_cid": cid,
            "matched_name": concepts_by_id[cid]["concept_name"] if cid else None,
            "confidence": conf,
            "score": score,
            "notes": notes,
        }

    mapped_gold_concepts = {k: v for k, v in gold_to_cid.items() if v}

    # Map gold pairs to canonical concept ID pairs
    evaluable_gold_pairs: List[Tuple[str, str]] = []
    gold_cid_pairs_set: Set[Tuple[str, str]] = set()
    gold_cid_to_raw_pairs: Dict[Tuple[str, str], List[Tuple[str, str]]] = {}

    for p, t in unique_gold_pairs:
        cid_p = gold_to_cid.get(p)
        cid_t = gold_to_cid.get(t)
        if cid_p and cid_t and cid_p != cid_t:
            evaluable_gold_pairs.append((p, t))
            cid_pair = (cid_p, cid_t)
            gold_cid_pairs_set.add(cid_pair)
            gold_cid_to_raw_pairs.setdefault(cid_pair, []).append((p, t))

    # 4. Extract and map predicted prerequisite edges
    cid_to_name = dict(zip(concepts_df["concept_id"], concepts_df["concept_name"]))
    cid_to_gold: Dict[str, str] = {v: k for k, v in mapped_gold_concepts.items()}

    predicted_cid_pairs: List[Tuple[str, str]] = []
    unmapped_predicted_endpoints = []

    for _, row in prereq_relations.iterrows():
        sid = str(row["source_id"]).strip()
        tid = str(row["target_id"]).strip()
        if sid and tid and sid != tid:
            predicted_cid_pairs.append((sid, tid))
            s_gold = cid_to_gold.get(sid)
            t_gold = cid_to_gold.get(tid)
            if not s_gold or not t_gold:
                unmapped_predicted_endpoints.append({
                    "source_id": sid,
                    "target_id": tid,
                    "source_name": cid_to_name.get(sid, sid),
                    "target_name": cid_to_name.get(tid, tid),
                    "source_gold": s_gold,
                    "target_gold": t_gold,
                })

    unique_predicted_cid_pairs = sorted(list(set(predicted_cid_pairs)))
    duplicates_removed_pred = len(predicted_cid_pairs) - len(unique_predicted_cid_pairs)

    # 5. Compute positive-only set-based metrics
    P = set(unique_predicted_cid_pairs)
    G = gold_cid_pairs_set

    tp_cid_set = P & G
    fp_cid_set = P - G
    fn_cid_evaluable_set = G - P

    tp_count = len(tp_cid_set)
    fp_count = len(fp_cid_set)
    fn_count_evaluable = len(fn_cid_evaluable_set)
    fn_count_total_gold = len(unique_gold_pairs) - tp_count

    prec = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
    rec_total = tp_count / len(unique_gold_pairs) if len(unique_gold_pairs) > 0 else 0.0
    rec_evaluable = tp_count / len(G) if len(G) > 0 else 0.0

    f1_total = (2 * prec * rec_total) / (prec + rec_total) if (prec + rec_total) > 0 else 0.0
    f1_evaluable = (2 * prec * rec_evaluable) / (prec + rec_evaluable) if (prec + rec_evaluable) > 0 else 0.0

    # Human-readable examples
    matched_tp_examples = []
    for sid, tid in list(tp_cid_set)[:10]:
        matched_tp_examples.append({
            "source": cid_to_name.get(sid, sid),
            "target": cid_to_name.get(tid, tid),
            "gold_pairs": gold_cid_to_raw_pairs.get((sid, tid), []),
        })

    unmatched_pred_examples = []
    for sid, tid in list(fp_cid_set)[:10]:
        unmatched_pred_examples.append({
            "source": cid_to_name.get(sid, sid),
            "target": cid_to_name.get(tid, tid),
            "source_gold": cid_to_gold.get(sid),
            "target_gold": cid_to_gold.get(tid),
        })

    missed_gold_examples = []
    for p, t in list(set(unique_gold_pairs) - {raw for cpair in tp_cid_set for raw in gold_cid_to_raw_pairs.get(cpair, [])})[:10]:
        missed_gold_examples.append({
            "prerequisite": p,
            "target": t,
            "both_concepts_mapped": bool(gold_to_cid.get(p) and gold_to_cid.get(t)),
        })

    report: Dict[str, Any] = {
        "dataset": dataset_name,
        "evaluation_protocol": "Positive-Only Prerequisite Evaluation (No Negative Synthesis)",
        "gold_concepts_total": len(gold_concepts),
        "gold_concepts_mapped": len(mapped_gold_concepts),
        "gold_concept_mapping_coverage": round(len(mapped_gold_concepts) / len(gold_concepts), 4) if gold_concepts else 0.0,
        "gold_positive_pairs_total": len(unique_gold_pairs),
        "gold_pairs_evaluable_subset": len(G),
        "gold_pair_evaluable_coverage": round(len(G) / len(unique_gold_pairs), 4) if unique_gold_pairs else 0.0,
        "predicted_prerequisite_pairs_raw": len(predicted_cid_pairs),
        "predicted_prerequisite_pairs_unique": len(unique_predicted_cid_pairs),
        "duplicate_predictions_removed": duplicates_removed_pred,
        "metrics_evaluable_subset": {
            "TP": tp_count,
            "FP_unmatched_predictions": fp_count,
            "FN": fn_count_evaluable,
            "Precision": round(prec, 4),
            "Recall": round(rec_evaluable, 4),
            "F1": round(f1_evaluable, 4),
            "Gold_Pair_Coverage": round(rec_evaluable, 4),
        },
        "metrics_full_gold_set": {
            "TP": tp_count,
            "FP_unmatched_predictions": fp_count,
            "FN": fn_count_total_gold,
            "Precision": round(prec, 4),
            "Recall": round(rec_total, 4),
            "F1": round(f1_total, 4),
            "Gold_Pair_Coverage": round(rec_total, 4),
        },
        "sample_true_positives": matched_tp_examples,
        "sample_unmatched_predictions": unmatched_pred_examples,
        "sample_missed_gold_pairs": missed_gold_examples,
        "unmapped_predicted_endpoints": unmapped_predicted_endpoints[:10],
        "important_limitations": [
            "Positive-only gold standard: gold file contains verified prerequisite pairs, not an exhaustive negative enumeration.",
            "Unmatched predictions are counted as FP under set-matching convention, but cannot be inferred to be true false prerequisites.",
            "ROC-AUC, specificity, and accuracy are intentionally omitted because explicit negative labels do not exist."
        ]
    }

    if output_report_json:
        output_report_json = Path(output_report_json)
        output_report_json.parent.mkdir(parents=True, exist_ok=True)
        output_report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if output_report_md:
        output_report_md = Path(output_report_md)
        output_report_md.parent.mkdir(parents=True, exist_ok=True)
        md_text = f"""# {dataset_name} Positive-Only Prerequisite Evaluation Report

## Summary
- **Dataset**: {dataset_name}
- **Protocol**: Positive-Only Evaluation (Zero synthetic negatives)
- **Gold Concepts**: {report['gold_concepts_total']} (Mapped: {report['gold_concepts_mapped']}, {report['gold_concept_mapping_coverage']*100:.1f}%)
- **Gold Pairs**: {report['gold_positive_pairs_total']} unique (Evaluable subset: {report['gold_pairs_evaluable_subset']}, {report['gold_pair_evaluable_coverage']*100:.1f}%)
- **Predicted Prerequisite Pairs**: {report['predicted_prerequisite_pairs_unique']} (Deduplicated)

## Metrics Table
| Metric | Evaluable Subset (Both Mapped) | Full Gold Set |
|---|---|---|
| True Positives (TP) | {report['metrics_evaluable_subset']['TP']} | {report['metrics_full_gold_set']['TP']} |
| Unmatched Predictions (FP)* | {report['metrics_evaluable_subset']['FP_unmatched_predictions']} | {report['metrics_full_gold_set']['FP_unmatched_predictions']} |
| False Negatives (FN) | {report['metrics_evaluable_subset']['FN']} | {report['metrics_full_gold_set']['FN']} |
| **Precision** | **{report['metrics_evaluable_subset']['Precision']:.4f}** | **{report['metrics_full_gold_set']['Precision']:.4f}** |
| **Recall** | **{report['metrics_evaluable_subset']['Recall']:.4f}** | **{report['metrics_full_gold_set']['Recall']:.4f}** |
| **F1-Score** | **{report['metrics_evaluable_subset']['F1']:.4f}** | **{report['metrics_full_gold_set']['F1']:.4f}** |
| **Gold-Pair Coverage** | **{report['metrics_evaluable_subset']['Gold_Pair_Coverage']:.4f}** | **{report['metrics_full_gold_set']['Gold_Pair_Coverage']:.4f}** |

> \\* *Important qualification*: In positive-only evaluation, unmatched predictions are treated as FP relative to the gold set, but cannot be confirmed as false pedagogical dependencies because the benchmark is not an exhaustive negative annotation. ROC-AUC and specificity are omitted.
"""
        output_report_md.write_text(md_text, encoding="utf-8")

    return report


def evaluate_dataset(
    dataset_key: str = "prat",
    kg_dir: Optional[Path] = None,
    output_report_json: Optional[Path] = None,
    output_report_md: Optional[Path] = None,
) -> Dict[str, Any]:
    """Convenience entry point using predefined dataset configurations."""
    cfg = DATASET_CONFIGS.get(dataset_key.lower())
    if not cfg:
        raise ValueError(f"Unknown dataset '{dataset_key}'. Supported: {list(DATASET_CONFIGS.keys())}")

    target_kg_dir = Path(kg_dir) if kg_dir else cfg["kg_dir"]
    out_json = output_report_json or (target_kg_dir / "positive_only_evaluation_report.json")
    out_md = output_report_md or (target_kg_dir / "positive_only_evaluation_report.md")

    return evaluate_positive_only(
        kg_dir=target_kg_dir,
        gold_pairs_path=cfg["gold_pairs_path"],
        gold_concepts_path=cfg.get("gold_concepts_path"),
        dataset_name=cfg["dataset_name"],
        file_format=cfg["format"],
        line_direction=cfg["line_direction"],
        output_report_json=out_json,
        output_report_md=out_md,
    )


# Alias for backwards compatibility
evaluate_positive_only_prat = lambda **kwargs: evaluate_dataset(dataset_key="prat", **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Unified Positive-Only Prerequisite Evaluation")
    parser.add_argument("--dataset", choices=list(DATASET_CONFIGS.keys()), default="prat",
                        help="Dataset key: 'prat', 'geometry', or 'geometry_cleaned'")
    parser.add_argument("--kg-dir", type=Path, default=None, help="Path to extracted KG directory")
    parser.add_argument("--gold-pairs", type=Path, default=None, help="Custom path to gold positive pairs")
    parser.add_argument("--gold-concepts", type=Path, default=None, help="Custom path to gold concepts vocabulary")
    parser.add_argument("--output-json", type=Path, default=None, help="Path to output JSON report")
    parser.add_argument("--output-md", type=Path, default=None, help="Path to output Markdown report")
    args = parser.parse_args()

    if args.gold_pairs:
        rep = evaluate_positive_only(
            kg_dir=args.kg_dir or DATASET_CONFIGS[args.dataset]["kg_dir"],
            gold_pairs_path=args.gold_pairs,
            gold_concepts_path=args.gold_concepts,
            dataset_name=DATASET_CONFIGS[args.dataset]["dataset_name"],
            file_format=DATASET_CONFIGS[args.dataset]["format"],
            line_direction=DATASET_CONFIGS[args.dataset]["line_direction"],
            output_report_json=args.output_json,
            output_report_md=args.output_md,
        )
    else:
        rep = evaluate_dataset(
            dataset_key=args.dataset,
            kg_dir=args.kg_dir,
            output_report_json=args.output_json,
            output_report_md=args.output_md,
        )

    print("=" * 65)
    print(f"      {rep['dataset'].upper()} POSITIVE-ONLY PREREQUISITE EVALUATION REPORT")
    print("=" * 65)
    print(f"Gold Concepts Coverage  : {rep['gold_concepts_mapped']}/{rep['gold_concepts_total']} ({rep['gold_concept_mapping_coverage']*100:.1f}%)")
    print(f"Gold Pairs Evaluated    : {rep['gold_pairs_evaluable_subset']}/{rep['gold_positive_pairs_total']} ({rep['gold_pair_evaluable_coverage']*100:.1f}%)")
    print(f"Predicted Prereq Pairs  : {rep['predicted_prerequisite_pairs_unique']}")
    print("-" * 65)
    print("EVALUABLE SUBSET (Pairs where both concepts mapped):")
    m_sub = rep["metrics_evaluable_subset"]
    print(f"  TP: {m_sub['TP']} | FP (unmatched): {m_sub['FP_unmatched_predictions']} | FN: {m_sub['FN']}")
    print(f"  Precision: {m_sub['Precision']:.4f} | Recall: {m_sub['Recall']:.4f} | F1: {m_sub['F1']:.4f}")
    print("-" * 65)
    print(f"FULL GOLD SET (All {rep['gold_positive_pairs_total']} unique gold pairs):")
    m_all = rep["metrics_full_gold_set"]
    print(f"  TP: {m_all['TP']} | FP (unmatched): {m_all['FP_unmatched_predictions']} | FN: {m_all['FN']}")
    print(f"  Precision: {m_all['Precision']:.4f} | Recall: {m_all['Recall']:.4f} | F1: {m_all['F1']:.4f}")
    print("=" * 65)
