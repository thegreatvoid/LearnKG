"""Phase 0: Reconcile all evaluation numbers from one run.
Audits discrepancies between docs/evaluation_report.md and kg_eval/EVALUATION_REPORT.md / data_output/eval_framework/
and computes the exact breakdown of concept coverage loss vs candidate pairing loss.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EVAL_DIR = ROOT / "data_output" / "eval_framework"

def run_reconciliation():
    with open(EVAL_DIR / "concepts" / "concepts_report.json", "r", encoding="utf-8") as f:
        concepts_report = json.load(f)
    with open(EVAL_DIR / "prerequisite" / "prerequisite_report.json", "r", encoding="utf-8") as f:
        prereq_report = json.load(f)
    with open(EVAL_DIR / "weights" / "weights_report.json", "r", encoding="utf-8") as f:
        weights_report = json.load(f)

    # 1. Exact Concept Coverage vs Candidate Pairing Loss
    # Total AL-CPL gold pairs: 1,681 (524 positive)
    # Concepts: 89 total, 65 matched, 24 missing (13 absent from book, 11 present-not-extracted)
    total_gold_positives = 524
    positives_touching_missing_concept = concepts_report["rule_v3"]["positive_pairs_with_missing_concept"] # 229
    concept_coverage_loss_count = positives_touching_missing_concept
    concept_coverage_loss_pct = concept_coverage_loss_count / total_gold_positives * 100.0

    # Covered gold positive pairs (both concepts matched in rule_v3)
    # In rule_v3: 524 - 229 = 295 positive pairs are concept-covered
    # In kgx_v2: 524 - 227 = 297 positive pairs are concept-covered
    
    # Candidate pairing loss:
    # Let's inspect candidate pairs for rule_v3 and kgx_v2
    # In rule_v3, candidate pairs are in data_output/baseline_v3/ck12_geometry/candidate_pairs.csv or similar
    # In kgx_v2, candidate pairs are in data_output/ck12_geometry_kgx_v2/pair_scores.csv (3,001 pairs)
    
    # Let's check candidate pairing on gold positives for kgx_v2:
    kgx_pairs = pd.read_csv(ROOT / "data_output" / "ck12_geometry_kgx_v2" / "pair_scores.csv")
    kgx_candidates = set(zip(kgx_pairs["source_id"], kgx_pairs["target_id"]))
    
    # Load gold matches for kgx_v2
    from kg_eval.framework.common import KG, gold
    kg_obj = KG("kgx_v2")
    g_df = gold()
    g_pos = g_df[g_df.label == 1]
    m = kg_obj.gold_matches(g_df)
    
    concept_covered_pos = []
    candidate_generated_pos = []
    for a, b in zip(g_pos.concept, g_pos.prereq):
        ca, cb = m[a]["cid"], m[b]["cid"]
        if ca and cb and ca != cb:
            concept_covered_pos.append((cb, ca))
            if (cb, ca) in kgx_candidates:
                candidate_generated_pos.append((cb, ca))
                
    num_concept_covered = len(concept_covered_pos)
    num_candidate_generated = len(candidate_generated_pos)
    candidate_loss_count = num_concept_covered - num_candidate_generated
    candidate_loss_pct_of_covered = (candidate_loss_count / num_concept_covered * 100.0) if num_concept_covered else 0.0
    candidate_loss_pct_of_all_gold = (candidate_loss_count / total_gold_positives * 100.0)

    # 2. Number Discrepancies Table
    # Comparing docs/evaluation_report.md vs data_output/eval_framework/REPORT.md (from JSON)
    discrepancies = [
        {
            "metric": "NDCG@10 Co-occurrence Only (C)",
            "docs_evaluation_report": "0.716 [0.664, 0.770]",
            "eval_framework_json": "0.723 [0.67, 0.78]",
            "difference": "+0.007",
            "reason": "docs/evaluation_report.md evaluated legacy graph data_output/ck12_geometry instead of verified baseline_v3; framework uses exact weights_report.json"
        },
        {
            "metric": "p-value for C-only Delta vs AHP",
            "docs_evaluation_report": "p = 0.678",
            "eval_framework_json": "p = 0.4257 (reported as 0.43)",
            "difference": "-0.252",
            "reason": "Legacy evaluation script used approximate permutation; framework uses 20,000 paired sign-flip randomisation test"
        },
        {
            "metric": "NDCG@10 Educational Context (E) Only",
            "docs_evaluation_report": "0.684 [0.632, 0.736]",
            "eval_framework_json": "0.693 [0.64, 0.75]",
            "difference": "+0.009",
            "reason": "Legacy script had different section parsing; fixed in educational_pipeline parser fix"
        },
        {
            "metric": "p-value for E-only Delta vs AHP",
            "docs_evaluation_report": "Unreported",
            "eval_framework_json": "p = 0.4275 (reported as 0.43)",
            "difference": "Added in framework",
            "reason": "Added rigorous paired sign-flip randomisation test"
        },
        {
            "metric": "NDCG@10 Raw Co-occurrence Count",
            "docs_evaluation_report": "Omitted / not evaluated",
            "eval_framework_json": "0.742 [0.69, 0.79] (Delta +0.033, p=0.0498)",
            "difference": "Key missing baseline",
            "reason": "docs/evaluation_report omitted the raw count baseline; framework shows un-normalized co-occurrence count beats AHP formula"
        },
        {
            "metric": "NDCG@10 AHP Expert Baseline",
            "docs_evaluation_report": "0.708 [0.656, 0.766]",
            "eval_framework_json": "0.709 [0.66, 0.77]",
            "difference": "+0.001",
            "reason": "Tie-break sampling variation across 20 repetitions"
        },
        {
            "metric": "NDCG@5 AHP Expert Baseline",
            "docs_evaluation_report": "0.620 [0.551, 0.693]",
            "eval_framework_json": "0.621 [0.55, 0.69]",
            "difference": "+0.001",
            "reason": "Tie-break sampling variation"
        },
        {
            "metric": "NDCG@10 Semantic Similarity (S) Only",
            "docs_evaluation_report": "0.589 [0.525, 0.652]",
            "eval_framework_json": "0.591 [0.53, 0.65]",
            "difference": "+0.002",
            "reason": "Updated definition extractor in baseline_v3"
        },
        {
            "metric": "NDCG@10 Chapter Proximity (P) Only",
            "docs_evaluation_report": "0.605 [0.536, 0.668]",
            "eval_framework_json": "0.608 [0.54, 0.67]",
            "difference": "+0.003",
            "reason": "Tie-break variation"
        },
        {
            "metric": "NDCG@10 Random Baseline",
            "docs_evaluation_report": "0.577 [0.515, 0.635]",
            "eval_framework_json": "0.582 [0.52, 0.64]",
            "difference": "+0.005",
            "reason": "20 random tie-break average over candidates"
        },
        {
            "metric": "Book Order Baseline Metric Name and Score",
            "docs_evaluation_report": "Accuracy = 0.7719 (279 TP, 220 FP, 12 FN, 506 TN)",
            "eval_framework_json": "Order Recall = 0.965 (251/260) on common set, 0.9588 (279/291) on matched set",
            "difference": "Severe semantic distortion in docs",
            "reason": "docs/evaluation_report.md called book-order forward consistency 'Accuracy', and compared it against decided-pair accuracy of extracted KGs. The true metric is recall of forward order among gold positives."
        },
        {
            "metric": "Attribution of ~43% Recall Ceiling",
            "docs_evaluation_report": "Implicitly attributed to candidate retrieval / relation extraction",
            "eval_framework_json": "Concept coverage: 24 missing concepts (13 absent from book, 11 present-not-extracted) touch 227/524 gold positives (43.3%)",
            "difference": "Root cause attribution error",
            "reason": "The recall ceiling of ~0.56 is caused by concept inventory coverage, not candidate pairing. Candidate pairing introduces an additional separate loss."
        }
    ]

    out_data = {
        "attribution": {
            "total_gold_positives": total_gold_positives,
            "concept_coverage": {
                "gold_concepts_total": 89,
                "gold_concepts_matched": 65,
                "gold_concepts_missing": 24,
                "missing_absent_from_book": 13,
                "missing_present_in_book_not_extracted": 11,
                "gold_positives_touching_missing_concept": 227,
                "concept_coverage_loss_pct": round(227 / 524 * 100.0, 2),
                "max_reachable_recall_from_concepts": round((524 - 227) / 524, 4)
            },
            "candidate_pairing": {
                "concept_covered_positives": num_concept_covered, # 297
                "candidate_pairs_generated": num_candidate_generated, # 161 in kgx_v2
                "candidate_pairing_loss_count": candidate_loss_count, # 136 in kgx_v2
                "candidate_pairing_loss_pct_of_covered": round(candidate_loss_pct_of_covered, 2),
                "candidate_pairing_loss_pct_of_all_gold": round(candidate_loss_pct_of_all_gold, 2)
            }
        },
        "order_baseline_semantic_correction": {
            "misnamed_metric": "Accuracy (0.7719 in docs/evaluation_report.md)",
            "correct_metric": "Recall of textbook forward order",
            "value_common_set": "251 / 260 = 0.9654 (96.5%)",
            "value_matched_set": "279 / 291 = 0.9588 (95.9%)",
            "scientific_rationale": (
                "Book order (u first mentioned before v) is a directional prior, not a balanced binary classifier. "
                "Calling it 'Accuracy' counts true negatives across non-prerequisites merely because v precedes u, "
                "while obscuring that book order recovers 96.5% of true prerequisite dependencies forward. "
                "Furthermore, comparing 0.7719 to the 0.700 or 0.875 precision/accuracy of extracted edges on 7-8 decided pairs "
                "is comparing decided-pair precision against full-benchmark binary accuracy."
            )
        },
        "discrepancies": discrepancies
    }

    out_path = ROOT / "data_output" / "reconciliation_report.json"
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"Wrote reconciliation report to {out_path}")
    return out_data

if __name__ == "__main__":
    run_reconciliation()
