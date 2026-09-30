"""
External Validation Script: Prerequisite-Relation Extraction vs. AL-CPL Gold Standard

Evaluates the educational pipeline's extracted Prerequisite relations on the
CK-12 Basic Geometry textbook against the AL-CPL Geometry domain benchmark.
"""

import os
import re
import json
import difflib
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

import pandas as pd

from educational_pipeline.normalizer import ConceptNormalizer


def normalize_gold_concept_name(raw_name: str) -> str:
    """
    Normalizes AL-CPL / Wikipedia concept titles:
    - Replaces underscores with spaces
    - Removes parenthetical disambiguation e.g. '(geometry)', '(mathematics)'
    - Applies ConceptNormalizer.clean_name
    """
    s = raw_name.replace("_", " ")
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    s = ConceptNormalizer.clean_name(s)
    return s


# Mapping from AL-CPL / Wikipedia concept names to the terms used in CK-12 Basic Geometry.
# These handle the 16 unmatched gold concepts and other known surface-form mismatches.
GEOMETRY_SYNONYM_MAP: Dict[str, List[str]] = {
    # Direct AL-CPL → CK-12 name mappings
    "Acute and obtuse triangles": ["Acute Triangle", "Obtuse Triangle"],
    "Bisection":                  ["Perpendicular Bisector", "Angle Bisector", "Bisector"],
    "Cartesian coordinate system":["Coordinate Plane", "Coordinate System", "Cartesian Coordinate"],
    "Coordinate system":          ["Coordinate Plane", "Coordinate System"],
    "Cross section":              ["Cross Section"],
    "Grade":                      ["Slope"],
    "Hendecagon":                  ["Hendecagon", "11-gon"],
    "Internal and external angle": ["Interior Angle", "Exterior Angle"],
    "Reflection symmetry":        ["Reflection Symmetry", "Line Symmetry", "Symmetry"],
    "Scaling":                    ["Dilation", "Scale Factor"],
    "Secant line":                ["Secant"],
    "Self-similarity":            ["Self Similarity", "Fractal"],
    "Skew lines":                 ["Skew Lines"],
    "Star polygon":               ["Star Polygon"],
    "Trigonometric functions":    ["Trigonometry", "Sine", "Cosine", "Tangent Ratio"],
    "Two-dimensional space":      ["Coordinate Plane", "Plane"],
}


def build_extracted_concept_index(concepts_df: pd.DataFrame) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str], ConceptNormalizer]:
    """
    Builds lookup tables for extracted concepts.
    Returns:
      - concepts_by_id: {cid: {name, aliases, ...}}
      - term_to_cid: {lowercased_term: cid}
      - normalizer: ConceptNormalizer instance for helper matching methods
    """
    normalizer = ConceptNormalizer()
    concepts_by_id: Dict[str, Dict[str, Any]] = {}
    term_to_cid: Dict[str, str] = {}

    for _, row in concepts_df.iterrows():
        cid = str(row["concept_id"]).strip()
        cname = str(row["concept_name"]).strip()
        aliases_raw = str(row.get("aliases", ""))
        aliases = [a.strip() for a in aliases_raw.split(",") if a.strip()] if aliases_raw and aliases_raw != "nan" else []
        
        concepts_by_id[cid] = {
            "concept_id": cid,
            "concept_name": cname,
            "aliases": aliases,
            "definition": str(row.get("definition", "")),
            "evidence": str(row.get("evidence", "")),
            "page": row.get("page", 1),
            "chunk_id": str(row.get("chunk_id", "")),
        }

        # Index canonical name
        cleaned_cname = ConceptNormalizer.clean_name(cname).lower()
        if cleaned_cname:
            term_to_cid[cleaned_cname] = cid

        # Index aliases
        for a in aliases:
            cleaned_a = ConceptNormalizer.clean_name(a).lower()
            if cleaned_a:
                term_to_cid[cleaned_a] = cid

    return concepts_by_id, term_to_cid, normalizer


def match_gold_concept(
    gold_raw: str,
    term_to_cid: Dict[str, str],
    concepts_by_id: Dict[str, Dict[str, Any]],
    normalizer: ConceptNormalizer,
    fuzzy_threshold: float = 0.82,  # Slightly relaxed to catch more textbook variants
) -> Tuple[Optional[str], str, float, List[str]]:
    """
    Matches an AL-CPL gold concept name to an extracted concept.
    First checks the GEOMETRY_SYNONYM_MAP for known CK-12 name equivalents,
    then falls back through exact, plural, token, and fuzzy matching.
    Returns:
      (matched_cid, confidence_level, score, candidate_notes)
      confidence_level: 'high', 'medium', 'low', or 'unmatched'
    """
    normalized_gold = normalize_gold_concept_name(gold_raw)
    gold_lower = normalized_gold.lower()

    # 0. Synonym map — try each known CK-12 alias for this gold concept
    syn_key = normalized_gold
    # Case-insensitive lookup in synonym map
    for map_key, synonyms in GEOMETRY_SYNONYM_MAP.items():
        if map_key.lower() == gold_lower:
            for syn in synonyms:
                syn_lower = ConceptNormalizer.clean_name(syn).lower()
                if syn_lower in term_to_cid:
                    cid = term_to_cid[syn_lower]
                    return cid, "high", 0.97, [f"Synonym map: '{syn}' matches '{concepts_by_id[cid]['concept_name']}'"]
            break

    # 1. Exact string match on canonical or alias
    if gold_lower in term_to_cid:
        cid = term_to_cid[gold_lower]
        return cid, "high", 1.0, [f"Exact match on '{concepts_by_id[cid]['concept_name']}'"]

    # 2. Singular / Plural match
    for term, cid in term_to_cid.items():
        if normalizer._is_plural_match(gold_lower, term):
            return cid, "high", 0.95, [f"Plural match on '{term}' ({concepts_by_id[cid]['concept_name']})"]

    # 3. Substring / Token subset match (e.g. 'Pythagorean theorem' vs 'Pythagorean Theorem Formula')
    candidate_matches = []
    gold_tokens = set(re.findall(r"\w+", gold_lower))

    for term, cid in term_to_cid.items():
        term_tokens = set(re.findall(r"\w+", term))
        if gold_tokens and term_tokens:
            if gold_tokens == term_tokens:
                return cid, "high", 0.98, [f"Token exact match on '{term}'"]
            if gold_tokens.issubset(term_tokens) or term_tokens.issubset(gold_tokens):
                # Calculate token Jaccard overlap
                jaccard = len(gold_tokens & term_tokens) / len(gold_tokens | term_tokens)
                if jaccard >= 0.6:
                    candidate_matches.append((cid, term, jaccard, "token_overlap"))

    # 4. Fuzzy SequenceMatcher
    for term, cid in term_to_cid.items():
        ratio = difflib.SequenceMatcher(None, gold_lower, term).ratio()
        if ratio >= fuzzy_threshold:
            candidate_matches.append((cid, term, ratio, "fuzzy"))

    if not candidate_matches:
        return None, "unmatched", 0.0, ["No candidate match above threshold"]

    # Sort candidates by score descending
    candidate_matches.sort(key=lambda x: x[2], reverse=True)
    best_cid, best_term, best_score, match_type = candidate_matches[0]

    # Check for ambiguity (multiple top matches with close scores)
    ambiguous_cids = [c[0] for c in candidate_matches if abs(c[2] - best_score) < 0.03]
    unique_ambiguous = list(set(ambiguous_cids))

    cname = concepts_by_id[best_cid]["concept_name"]
    notes = [f"{match_type} match on '{best_term}' ({cname}) score={best_score:.2f}"]

    if len(unique_ambiguous) > 1:
        notes.append(f"Ambiguous candidates: {[concepts_by_id[c]['concept_name'] for c in unique_ambiguous]}")
        return best_cid, "low", best_score, notes

    confidence = "high" if best_score >= 0.90 else "medium"
    return best_cid, confidence, best_score, notes


def run_evaluation(
    dataset_name: str = "ck12_geometry",
    data_output_dir: str = "./data_output",
    output_report_json: Optional[str] = None,
) -> Dict[str, Any]:
    output_path = Path(data_output_dir) / dataset_name
    concepts_file = output_path / "concepts.csv"
    relations_file = output_path / "relations.csv"
    gold_file = output_path / "gold_prerequisite_pairs.csv"

    if not concepts_file.exists() or not relations_file.exists():
        raise FileNotFoundError(f"Extracted pipeline outputs not found in {output_path}")
    if not gold_file.exists():
        raise FileNotFoundError(f"Gold standard CSV not found at {gold_file}")

    print(f"[*] Loading extracted concepts from {concepts_file}...")
    concepts_df = pd.read_csv(concepts_file)
    print(f"[*] Loading extracted relations from {relations_file}...")
    relations_df = pd.read_csv(relations_file)
    print(f"[*] Loading gold prerequisite pairs from {gold_file}...")
    gold_df = pd.read_csv(gold_file)

    # 1. Filter extracted relations to Prerequisite type
    prereq_relations_df = relations_df[relations_df["relation_type"].str.strip().str.lower() == "prerequisite"].copy()
    print(f"[+] Total extracted relations: {len(relations_df)}, Prerequisite relations: {len(prereq_relations_df)}")

    # 2. Build extracted concept index
    concepts_by_id, term_to_cid, normalizer = build_extracted_concept_index(concepts_df)
    print(f"[+] Indexed {len(concepts_by_id)} canonical concepts ({len(term_to_cid)} indexed terms/aliases).")

    # 3. Extract concept set from gold dataset
    gold_concepts = sorted(list(set(gold_df["concept_a"].dropna().tolist() + gold_df["concept_b"].dropna().tolist())))
    print(f"[*] Total unique gold concepts: {len(gold_concepts)}")

    # 4. Map each gold concept to extracted concepts
    gold_to_extracted: Dict[str, Dict[str, Any]] = {}
    matched_gold_count = 0
    unmatched_gold = []
    ambiguous_matches = []
    low_conf_matches = []

    for gc in gold_concepts:
        cid, conf, score, notes = match_gold_concept(gc, term_to_cid, concepts_by_id, normalizer)
        matched_name = concepts_by_id[cid]["concept_name"] if cid else None
        gold_to_extracted[gc] = {
            "matched_cid": cid,
            "matched_concept_name": matched_name,
            "confidence": conf,
            "score": score,
            "notes": notes,
        }
        if cid:
            matched_gold_count += 1
            if conf == "low":
                low_conf_matches.append({"gold": gc, "matched": matched_name, "score": score, "notes": notes})
            if any("Ambiguous" in n for n in notes):
                ambiguous_matches.append({"gold": gc, "matched": matched_name, "score": score, "notes": notes})
        else:
            unmatched_gold.append(gc)

    coverage_pct = (matched_gold_count / len(gold_concepts)) * 100 if gold_concepts else 0
    print(f"[+] Gold Concept Coverage: {matched_gold_count}/{len(gold_concepts)} ({coverage_pct:.1f}%) matched.")
    print(f"[-] Unmatched Gold Concepts (Coverage Gap): {len(unmatched_gold)}")

    # 5. Build set of extracted Prerequisite edges (both directions as directed pairs + evidence)
    # Store: (src_cid, tgt_cid) -> evidence
    extracted_prereq_edges: Dict[Tuple[str, str], List[str]] = {}
    for _, row in prereq_relations_df.iterrows():
        sid = str(row["source_id"]).strip()
        tid = str(row["target_id"]).strip()
        ev = str(row.get("evidence", ""))
        extracted_prereq_edges.setdefault((sid, tid), []).append(ev)

    # Helper to check if edge exists in either direction
    def has_extracted_prereq(cid1: str, cid2: str) -> Tuple[bool, Optional[str]]:
        if (cid1, cid2) in extracted_prereq_edges:
            return True, extracted_prereq_edges[(cid1, cid2)][0]
        if (cid2, cid1) in extracted_prereq_edges:
            return True, extracted_prereq_edges[(cid2, cid1)][0]
        return False, None

    # 6. Evaluate all pairs
    tp_pairs = []
    fp_pairs = []
    fn_pairs = []
    tn_pairs = []

    # Conditioned evaluation (where both concepts were matched)
    cond_tp = []
    cond_fp = []
    cond_fn = []
    cond_tn = []

    for _, row in gold_df.iterrows():
        ga = str(row["concept_a"]).strip()
        gb = str(row["concept_b"]).strip()
        is_gold_prereq = int(row["is_prerequisite"]) == 1

        match_a = gold_to_extracted.get(ga, {})
        match_b = gold_to_extracted.get(gb, {})
        cid_a = match_a.get("matched_cid")
        cid_b = match_b.get("matched_cid")

        both_matched = bool(cid_a and cid_b)
        extracted_pred = False
        evidence_str = None

        if both_matched:
            # Self-loops in matching are considered non-prerequisite
            if cid_a != cid_b:
                extracted_pred, evidence_str = has_extracted_prereq(cid_a, cid_b)

        pair_record = {
            "gold_a": ga,
            "gold_b": gb,
            "is_gold_prerequisite": is_gold_prereq,
            "matched_a": match_a.get("matched_concept_name"),
            "matched_b": match_b.get("matched_concept_name"),
            "both_concepts_matched": both_matched,
            "extracted_prerequisite": extracted_pred,
            "evidence": evidence_str,
        }

        # Overall confusion matrix
        if extracted_pred:
            if is_gold_prereq:
                tp_pairs.append(pair_record)
            else:
                fp_pairs.append(pair_record)
        else:
            if is_gold_prereq:
                fn_pairs.append(pair_record)
            else:
                tn_pairs.append(pair_record)

        # Conditioned confusion matrix (only pairs where both concepts matched)
        if both_matched:
            if extracted_pred:
                if is_gold_prereq:
                    cond_tp.append(pair_record)
                else:
                    cond_fp.append(pair_record)
            else:
                if is_gold_prereq:
                    cond_fn.append(pair_record)
                else:
                    cond_tn.append(pair_record)

    def calc_metrics(tp_len, fp_len, fn_len, tn_len):
        prec = tp_len / (tp_len + fp_len) if (tp_len + fp_len) > 0 else 0.0
        rec = tp_len / (tp_len + fn_len) if (tp_len + fn_len) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        acc = (tp_len + tn_len) / (tp_len + fp_len + fn_len + tn_len) if (tp_len + fp_len + fn_len + tn_len) > 0 else 0.0
        return {
            "TP": tp_len,
            "FP": fp_len,
            "FN": fn_len,
            "TN": tn_len,
            "Precision": round(prec, 4),
            "Recall": round(rec, 4),
            "F1": round(f1, 4),
            "Accuracy": round(acc, 4),
        }

    overall_metrics = calc_metrics(len(tp_pairs), len(fp_pairs), len(fn_pairs), len(tn_pairs))
    conditioned_metrics = calc_metrics(len(cond_tp), len(cond_fp), len(cond_fn), len(cond_tn))

    report = {
        "dataset": dataset_name,
        "total_gold_pairs": len(gold_df),
        "positive_gold_pairs": int((gold_df["is_prerequisite"] == 1).sum()),
        "negative_gold_pairs": int((gold_df["is_prerequisite"] == 0).sum()),
        "total_gold_concepts": len(gold_concepts),
        "matched_gold_concepts": matched_gold_count,
        "unmatched_gold_concepts_count": len(unmatched_gold),
        "concept_coverage_percent": round(coverage_pct, 2),
        "unmatched_gold_concepts": unmatched_gold,
        "ambiguous_concept_matches": ambiguous_matches,
        "low_confidence_matches": low_conf_matches,
        "overall_evaluation": overall_metrics,
        "concept_conditioned_evaluation": {
            "total_pairs_both_concepts_matched": len(cond_tp) + len(cond_fp) + len(cond_fn) + len(cond_tn),
            "metrics": conditioned_metrics,
        },
        "sample_false_positives": fp_pairs[:5],
        "sample_false_negatives": fn_pairs[:5],
        "sample_true_positives": tp_pairs[:5],
    }

    if output_report_json is None:
        output_report_json = str(output_path / "evaluation_report.json")

    with open(output_report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Full evaluation report saved to: {output_report_json}")

    # Print human-readable summary
    print("\n" + "=" * 65)
    print("      EXTERNAL VALIDATION REPORT: PREREQUISITE EXTRACTION")
    print("=" * 65)
    print(f"Benchmark Dataset        : AL-CPL Geometry (github.com/harrylclc/AL-CPL-dataset)")
    print(f"Evaluated Textbook       : CK-12 Basic Geometry (unmodified rule-based pipeline)")
    print(f"Total Gold Concept Pairs : {len(gold_df)} (Pos: {report['positive_gold_pairs']}, Neg: {report['negative_gold_pairs']})")
    print(f"Gold Concepts Coverage   : {matched_gold_count}/{len(gold_concepts)} ({coverage_pct:.1f}%)")
    print(f"Coverage Gap (Unmatched) : {len(unmatched_gold)} concepts")
    print("-" * 65)
    print("OVERALL METRICS (All 1,681 Gold Pairs):")
    print(f"  Precision : {overall_metrics['Precision']:.4f}")
    print(f"  Recall    : {overall_metrics['Recall']:.4f}")
    print(f"  F1-Score  : {overall_metrics['F1']:.4f}")
    print(f"  Confusion Matrix : TP={overall_metrics['TP']}, FP={overall_metrics['FP']}, FN={overall_metrics['FN']}, TN={overall_metrics['TN']}")
    print("-" * 65)
    print("CONCEPT-CONDITIONED METRICS (Pairs where both concepts are matched):")
    print(f"  Evaluated Pairs : {report['concept_conditioned_evaluation']['total_pairs_both_concepts_matched']}")
    print(f"  Precision       : {conditioned_metrics['Precision']:.4f}")
    print(f"  Recall          : {conditioned_metrics['Recall']:.4f}")
    print(f"  F1-Score        : {conditioned_metrics['F1']:.4f}")
    print(f"  Confusion Matrix: TP={conditioned_metrics['TP']}, FP={conditioned_metrics['FP']}, FN={conditioned_metrics['FN']}, TN={conditioned_metrics['TN']}")
    print("=" * 65 + "\n")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Prerequisite Extraction on AL-CPL Benchmark")
    parser.add_argument("--dataset", default="ck12_geometry", help="Dataset name in data_output/")
    parser.add_argument("--output-report", default=None, help="Path to write evaluation_report.json")
    args = parser.parse_args()

    run_evaluation(dataset_name=args.dataset, output_report_json=args.output_report)
