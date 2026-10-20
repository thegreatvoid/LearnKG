"""Freeze the weighting method before a second-domain (independent) evaluation, and check it has not changed.

  python -m kg_eval.freeze_manifest --write   # once, BEFORE looking at any second-domain result
  python -m kg_eval.freeze_manifest --check   # before running / reporting the second domain: must print OK

The manifest records the git commit, SHA-256 of every file that defines the method or its evaluation, the weighting
schemes, and the evaluation settings. If --check reports a difference, the second-domain result is no longer an
independent test of the frozen method (see kg_eval/second_domain_protocol.md).
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "kg_eval" / "frozen_manifest.json"
FROZEN_FILES = [
    "educational_pipeline/parser.py", "educational_pipeline/structure_detector.py", "educational_pipeline/chunker.py",
    "educational_pipeline/concept_extractor.py", "educational_pipeline/normalizer.py",
    "educational_pipeline/definition_extractor.py", "educational_pipeline/relation_extractor.py",
    "educational_pipeline/pipeline.py", "educational_pipeline/dataset_builder.py",
    "kg_eval/data.py", "kg_eval/weight_ranking.py", "kg_eval/prereq_gold.py", "kg_eval/direction_check.py",
    "kg_eval/bigs.py", "kg_eval/bigs_compare.py", "evaluate_prerequisite_extraction.py",
    "kg_eval/framework/common.py", "kg_eval/framework/concepts_eval.py", "kg_eval/framework/prereq_eval.py",
    "kg_eval/framework/relation_checks.py", "kg_eval/framework/weights_eval.py", "kg_eval/framework/bigs_by_relation.py",
    "kg_eval/framework/gap_proxy.py", "kg_eval/framework/annotation_kit.py",
]
SETTINGS = {
    "pipeline": {"use_llm": False, "use_neural_model": True, "neural_threshold": -0.5,
                 "definition_policy": "first_definitional", "embedding_similarity": True,
                 "weighting_scheme_reported": "all of WEIGHTING_SCHEMES (no new scheme may be added)",
                 "PYTHONHASHSEED": "0 (not required since 2026-10-15, kept for safety)"},
    "evaluation": {"ndcg_k": [5, 10], "tie_breaks": 20, "bootstrap_reps": 2000, "cv_folds": 5, "cv_grid_step": 0.1,
                   "sign_flip_reps": 20000, "prereq_gold_reps": 1000, "embedder": "sentence-transformers/all-MiniLM-L6-v2"},
    "primary_comparisons": ["scheme cooc_only vs scheme ahp", "scheme cooc_struct_a0.8 vs scheme ahp",
                            "book order gate x C vs book order (gap)"],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current():
    sys.path.insert(0, str(ROOT))
    from educational_pipeline.relation_extractor import WEIGHTING_SCHEMES
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", *FROZEN_FILES], cwd=ROOT, capture_output=True,
                           text=True).stdout.strip()
    return {"git_head": commit, "frozen_files_uncommitted_changes": bool(dirty),
            "files": {f: sha(ROOT / f) for f in FROZEN_FILES}, "weighting_schemes": WEIGHTING_SCHEMES,
            "settings": SETTINGS}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()
    now = current()
    if a.write:
        MANIFEST.write_text(json.dumps(now, indent=2))
        print(f"wrote {MANIFEST}" + ("  (WARNING: frozen files have uncommitted changes; commit them)"
                                     if now["frozen_files_uncommitted_changes"] else ""))
        return
    old = json.loads(MANIFEST.read_text())
    diffs = [f for f in FROZEN_FILES if old["files"].get(f) != now["files"][f]]
    if old["weighting_schemes"] != now["weighting_schemes"]:
        diffs.append("WEIGHTING_SCHEMES")
    if old["settings"] != now["settings"]:
        diffs.append("SETTINGS")
    if diffs:
        print("CHANGED since freeze:", ", ".join(diffs))
        sys.exit(1)
    print("OK: method and evaluation unchanged since", old["git_head"][:10])


if __name__ == "__main__":
    main()
