"""Runs the whole evaluation framework in order, then the report.  python -m kg_eval.framework.run_all"""

import importlib
import sys

STEPS = ["concepts_eval", "prereq_eval", "relation_checks", "weights_eval", "bigs_by_relation", "gap_proxy"]


def main():
    for s in STEPS:
        print(f"\n===== {s} =====", flush=True)
        importlib.import_module(f"kg_eval.framework.{s}").main()
    sys.argv = ["annotation_kit", "build"]
    importlib.import_module("kg_eval.framework.annotation_kit").main()
    importlib.import_module("kg_eval.framework.report").main()


if __name__ == "__main__":
    main()
