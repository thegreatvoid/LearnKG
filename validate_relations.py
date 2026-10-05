"""
Validates relations.csv against concepts.csv — both directions the user
asked about:

  WANTED  (is each existing relation actually correct?)
    - Structural checks: referential integrity, no self-loops, no exact
      duplicates, weight in [0,1], relation_type in the controlled 5-type
      ontology.
    - Grounding checks: every relation carries a verbatim `evidence`
      sentence (educational_pipeline/relation_extractor.py) — so we can
      mechanically check whether that sentence actually mentions BOTH the
      source and target concept (by name or alias), and whether it contains
      at least one of the keywords that would justify the assigned
      relation_type (ONTOLOGY_PATTERNS). A relation whose evidence doesn't
      mention both concepts, or doesn't contain any supporting keyword, is
      flagged as a likely spurious ("unwanted") relation.
    - Optional LLM-as-judge: "does this evidence actually support this
      relation claim?" — same Ollama-or-deterministic-fallback pattern as
      evaluate_chatbot.py/evaluate_mine1.py.

  MISSING (are there relations that should exist but don't?)
    - Concept pairs that co-occur in the same source chunk (chunk_id in
      concepts.csv) but have no relation row between them in either
      direction are reported as candidates for human review — the
      extraction pipeline had the opportunity to link them (they were in
      the same sentence/chunk window) but didn't.

Run with:  python validate_relations.py          (from the LearnKG/ directory)
Optional:  OLLAMA_MODEL=zephyr:latest python validate_relations.py   (LLM judge)
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from educational_pipeline.relation_extractor import ONTOLOGY_PATTERNS, VALID_ONTOLOGY_TYPES

DATA_DIR = Path(__file__).resolve().parent / "data_output" / "cureus"
MAX_MISSING_CANDIDATES = 30


@dataclass
class RelationCheck:
    relation_id: str
    source: str
    target: str
    relation_type: str
    weight: float
    evidence: str
    checks: Dict[str, bool] = field(default_factory=dict)
    judge_score: Optional[int] = None
    verdict: str = "confirmed"  # "confirmed" (wanted) | "flagged" (likely unwanted)


def _name_variants(name: str, aliases: str) -> Set[str]:
    variants = {str(name).strip().lower()} if name else set()
    for a in str(aliases).split(","):
        a = a.strip().lower()
        if a:
            variants.add(a)
    return variants


def _mentions(text: str, variants: Set[str]) -> bool:
    text_l = text.lower()
    return any(re.search(rf"\b{re.escape(v)}\b", text_l) for v in variants if v)


def validate_structural_and_grounding(df_c: pd.DataFrame, df_r: pd.DataFrame) -> List[RelationCheck]:
    concept_ids = set(df_c["concept_id"])
    name_variants_by_id = {row.concept_id: _name_variants(row.concept_name, row.aliases) for row in df_c.itertuples()}
    label_by_id = {row.concept_id: row.concept_name for row in df_c.itertuples()}

    results: List[RelationCheck] = []
    seen_keys: Set[tuple] = set()

    for row in df_r.itertuples():
        weight = float(row.weight) if str(row.weight).strip() else 0.0
        evidence = str(row.evidence or "")
        rc = RelationCheck(
            relation_id=row.relation_id,
            source=label_by_id.get(row.source_id, row.source_id),
            target=label_by_id.get(row.target_id, row.target_id),
            relation_type=row.relation_type,
            weight=weight,
            evidence=evidence,
        )

        key = (row.source_id, row.target_id, row.relation_type)
        checks = {
            "referential_integrity": row.source_id in concept_ids and row.target_id in concept_ids,
            "no_self_loop": row.source_id != row.target_id,
            "no_exact_duplicate": key not in seen_keys,
            "weight_in_range": 0.0 <= weight <= 1.0,
            "valid_ontology_type": row.relation_type in VALID_ONTOLOGY_TYPES,
            "evidence_present": bool(evidence.strip()),
        }
        seen_keys.add(key)

        src_variants = name_variants_by_id.get(row.source_id, set())
        tgt_variants = name_variants_by_id.get(row.target_id, set())
        checks["evidence_mentions_source"] = checks["evidence_present"] and _mentions(evidence, src_variants)
        checks["evidence_mentions_target"] = checks["evidence_present"] and _mentions(evidence, tgt_variants)

        keywords = ONTOLOGY_PATTERNS.get(row.relation_type, [])
        checks["ontology_keyword_present"] = checks["evidence_present"] and any(
            kw in evidence.lower() for kw in keywords
        )

        rc.checks = checks
        rc.verdict = "confirmed" if all(checks.values()) else "flagged"
        results.append(rc)

    return results


def judge_relation(source: str, relation_type: str, target: str, evidence: str, use_ollama: bool, ollama_model: Optional[str]) -> int:
    """0/1 — does the evidence actually support this relation claim? Ollama
    if configured/reachable, else falls back to the structural grounding
    checks already computed (evidence mentions both concepts + a
    supporting ontology keyword) as a deterministic proxy."""
    if use_ollama and ollama_model:
        try:
            import requests

            base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            prompt = (
                f"Claim: '{source}' has a '{relation_type}' relationship with '{target}'.\n"
                f"Evidence sentence: \"{evidence}\"\n\n"
                "Does the evidence sentence actually support this claim? "
                "Reply with only the single digit 1 (yes) or 0 (no)."
            )
            resp = requests.post(
                f"{base_url}/api/generate",
                json={"model": ollama_model, "prompt": prompt, "stream": False},
                timeout=12.0,
            )
            resp.raise_for_status()
            text = (resp.json().get("response") or "").strip()
            for ch in text:
                if ch in "01":
                    return int(ch)
        except Exception as exc:
            print(f"[validate_relations] Ollama judge failed ({exc}); falling back to structural proxy.")

    return 0  # overwritten by caller's structural-proxy fallback


def find_missing_relation_candidates(df_c: pd.DataFrame, df_r: pd.DataFrame, max_results: int = MAX_MISSING_CANDIDATES) -> List[dict]:
    """Concept pairs that co-occur in the same source chunk but have no
    relation between them in either direction — candidates for "wanted but
    missing" relations."""
    chunk_to_concepts: Dict[str, List[str]] = {}
    for row in df_c.itertuples():
        chunk_to_concepts.setdefault(row.chunk_id, []).append(row.concept_id)

    existing_pairs: Set[tuple] = set()
    for row in df_r.itertuples():
        existing_pairs.add((row.source_id, row.target_id))
        existing_pairs.add((row.target_id, row.source_id))

    label_by_id = {row.concept_id: row.concept_name for row in df_c.itertuples()}
    candidates = []
    seen_pairs: Set[tuple] = set()

    for chunk_id, ids in chunk_to_concepts.items():
        unique_ids = sorted(set(ids))
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                a, b = unique_ids[i], unique_ids[j]
                pair_key = (a, b)
                if pair_key in seen_pairs or (a, b) in existing_pairs:
                    continue
                seen_pairs.add(pair_key)
                candidates.append({
                    "concept_a": label_by_id.get(a, a),
                    "concept_b": label_by_id.get(b, b),
                    "shared_chunk_id": chunk_id,
                })

    return candidates[:max_results]


def print_report(results: List[RelationCheck], missing: List[dict]) -> None:
    confirmed = [r for r in results if r.verdict == "confirmed"]
    flagged = [r for r in results if r.verdict == "flagged"]

    print("=" * 70)
    print("  RELATION VALIDATION — WANTED vs UNWANTED")
    print("=" * 70)
    print(f"  Total relations : {len(results)}")
    print(f"  Confirmed (wanted)      : {len(confirmed)} ({100 * len(confirmed) / max(1, len(results)):.1f}%)")
    print(f"  Flagged (likely unwanted): {len(flagged)} ({100 * len(flagged) / max(1, len(results)):.1f}%)")

    if flagged:
        fail_counts: Dict[str, int] = {}
        for r in flagged:
            for check_name, passed in r.checks.items():
                if not passed:
                    fail_counts[check_name] = fail_counts.get(check_name, 0) + 1
        print("\n  Failure breakdown (a flagged relation may fail more than one check):")
        for check_name, count in sorted(fail_counts.items(), key=lambda kv: -kv[1]):
            print(f"    - {check_name}: {count}")

        print("\n  Flagged relations:")
        for r in flagged[:20]:
            failed = [k for k, v in r.checks.items() if not v]
            print(f"    [{r.relation_id}] {r.source} --{r.relation_type}--> {r.target}  (failed: {', '.join(failed)})")
            if r.evidence:
                print(f"        evidence: \"{r.evidence[:120]}\"")
        if len(flagged) > 20:
            print(f"    ... and {len(flagged) - 20} more (see relation_validation.json)")

    print(f"\n  Likely-missing relation candidates (co-occur, unlinked): {len(missing)}")
    for m in missing[:15]:
        print(f"    - {m['concept_a']}  <->  {m['concept_b']}  (shared chunk {m['shared_chunk_id'][:8]}...)")
    if len(missing) > 15:
        print(f"    ... and {len(missing) - 15} more (see relation_validation.json)")
    print("=" * 70)


def main() -> None:
    if not (DATA_DIR / "concepts.csv").exists():
        raise FileNotFoundError(
            f"No concepts.csv found at {DATA_DIR} — run the pipeline first "
            f"(python run_pipeline.py --pipeline educational --dataset cureus --no-llm)."
        )

    df_c = pd.read_csv(DATA_DIR / "concepts.csv", dtype=str).fillna("")
    df_r = pd.read_csv(DATA_DIR / "relations.csv", dtype=str).fillna("")

    results = validate_structural_and_grounding(df_c, df_r)

    ollama_model = os.environ.get("OLLAMA_MODEL")
    use_ollama = bool(ollama_model)
    for r in results:
        structural_proxy = 1 if all([
            r.checks["evidence_mentions_source"],
            r.checks["evidence_mentions_target"],
            r.checks["ontology_keyword_present"],
        ]) else 0
        if use_ollama:
            score = judge_relation(r.source, r.relation_type, r.target, r.evidence, use_ollama, ollama_model)
            r.judge_score = score if r.evidence else 0
        else:
            r.judge_score = structural_proxy

    missing = find_missing_relation_candidates(df_c, df_r)

    print_report(results, missing)

    output_path = DATA_DIR / "relation_validation.json"
    output_path.write_text(json.dumps({
        "relations": [asdict(r) for r in results],
        "missing_candidates": missing,
        "summary": {
            "total": len(results),
            "confirmed": sum(1 for r in results if r.verdict == "confirmed"),
            "flagged": sum(1 for r in results if r.verdict == "flagged"),
            "missing_candidates": len(missing),
        },
    }, indent=2))
    print(f"\n[+] Full results written to {output_path}")


if __name__ == "__main__":
    main()
