"""Run the grounded extraction pipeline.

  python -m kg_extract.run --data-dir ck12_geometry --model qwen2.5:7b-instruct --out data_output/ck12_geometry_kgx

Writes concepts.csv, relations.csv (schema of educational_pipeline), pair_scores.csv and run_meta.json.
Book order is NOT used anywhere (`uses_book_order: false`)."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from educational_pipeline.chunker import create_structure_aware_chunks
from educational_pipeline.dataset_builder import build_and_save_dataset
from educational_pipeline.parser import parse_document
from educational_pipeline.relation_extractor import ExtractedRelation, RelationManager
from educational_pipeline.structure_detector import detect_educational_structures

from .backend import OllamaBackend
from .concepts import extract_concepts
from .consistency import make_consistent
from .pairs import generate_candidates
from .score import RELATIONS, score_pairs


def load_chunks(input_path: Path, dump_dir: Path = None):
    """Parse -> detect structure -> chunk. If dump_dir is given, each stage's output is written there as CSV."""
    files = [input_path] if input_path.is_file() else sorted(list(input_path.glob("*.pdf")) + list(input_path.glob("*.txt")))
    if not files:
        raise FileNotFoundError(f"no .txt/.pdf in {input_path}")
    blocks = [b for f in files for b in parse_document(f)]
    structured = detect_educational_structures(blocks)
    chunks = create_structure_aware_chunks(structured)
    if dump_dir is not None:
        dump_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"idx": i, "page": b.page, "chapter": b.chapter, "section": b.section,
                       "is_heading": b.is_heading, "source_file": b.source_file, "text": b.text}
                      for i, b in enumerate(blocks)]).to_csv(dump_dir / "parsed_blocks.csv", index=False)
        pd.DataFrame([{"idx": i, "block_type": b.block_type, "page": b.page, "chapter": b.chapter,
                       "section": b.section, "text": b.text} for i, b in enumerate(structured)]
                     ).to_csv(dump_dir / "structured_blocks.csv", index=False)
        pd.DataFrame([{"chunk_id": c.chunk_id, "block_type": c.block_type, "page": c.page, "chapter": c.chapter,
                       "section": c.section, "n_chars": len(c.text), "text": c.text} for c in chunks]
                     ).to_csv(dump_dir / "chunks.csv", index=False)
        print(f"[dump] {len(blocks)} parsed blocks, {len(structured)} structured blocks, {len(chunks)} chunks -> {dump_dir}")
    return chunks, "\n\n".join(b.text for b in blocks)


def write_pair_scores(path, normalizer, scores, meta):
    rows = []
    for key, m in meta.items():
        a, b = sorted(key)
        for s, t in ((a, b), (b, a)):
            r = scores.get((s, t), {})
            rows.append({"source_id": s, "target_id": t,
                         "source_name": normalizer.concepts_by_id[s].concept_name,
                         "target_name": normalizer.concepts_by_id[t].concept_name,
                         **{f"score_{rel}": round(r.get(rel, 0.0), 4) for rel in RELATIONS},
                         "n_samples": m["n_ok"], "cooccurrence_count": m["cooc"]})
    pd.DataFrame(rows).to_csv(path, index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="ck12_geometry")
    ap.add_argument("--input-base", default="./data_input")
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default="qwen2.5:7b-instruct")
    ap.add_argument("--top-k", type=int, default=250, help="max concepts kept")
    ap.add_argument("--samples", type=int, default=2, help="LLM samples per pair")
    ap.add_argument("--threshold", type=float, default=0.5, help="min score for an edge in relations.csv")
    ap.add_argument("--per-concept", type=int, default=8)
    ap.add_argument("--max-pairs", type=int, default=1500)
    ap.add_argument("--hubs", type=int, default=10, help="pair the H most foundational concepts with every concept")
    ap.add_argument("--embed-neighbors", type=int, default=0,
                    help="also add each concept's k nearest concepts by embedding as candidate pairs")
    ap.add_argument("--no-ground", action="store_true", help="ablation: disable the grounding filter")
    ap.add_argument("--no-llm-concepts", action="store_true", help="ablation: rule/spaCy candidates only")
    ap.add_argument("--dump-intermediate", action="store_true",
                    help="write parsed_blocks.csv, structured_blocks.csv and chunks.csv (parser/structure/chunker output) to <out>/intermediate/")
    ap.add_argument("--candidates-only", action="store_true",
                    help="stop after stages 1-3 (no pair scoring); writes concepts.csv + candidate_pairs.csv")
    args = ap.parse_args()
    out = Path(args.out or f"./data_output/{args.data_dir}_kgx")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    chunks, full_text = load_chunks(Path(args.input_base) / args.data_dir,
                                    out / "intermediate" if args.dump_intermediate else None)
    need_llm = not (args.candidates_only and args.no_llm_concepts)
    backend = OllamaBackend(args.model) if need_llm else None
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm", disable=["ner"])
    except Exception:
        nlp = None
    counters = Counter()

    normalizer, rep = extract_concepts(chunks, None if args.no_llm_concepts else backend, full_text,
                                       top_k=args.top_k, nlp=nlp, ground=not args.no_ground, counters=counters)
    pd.DataFrame(rep.pop("candidates")).to_csv(out / "concept_candidates.csv", index=False)
    print(f"[concepts] {rep} counters={dict(counters)} (all candidates: {out / 'concept_candidates.csv'})")
    cands = generate_candidates(normalizer, chunks, args.per_concept, args.max_pairs, args.embed_neighbors, args.hubs)
    print(f"[pairs] {len(cands)} candidate pairs")
    if args.candidates_only:
        build_and_save_dataset(normalizer, RelationManager(normalizer), out)
        pd.DataFrame([{"source_id": c["a"], "target_id": c["b"],
                       "source_name": normalizer.concepts_by_id[c["a"]].concept_name,
                       "target_name": normalizer.concepts_by_id[c["b"]].concept_name,
                       "score": c["score"], "cooccurrence_count": c["cooc"]} for c in cands]
                     ).to_csv(out / "candidate_pairs.csv", index=False)
        print(f"[done] candidates only -> {out}")
        return
    scores, meta = score_pairs(backend, normalizer, cands, samples=args.samples, counters=counters)
    edges, dropped = make_consistent(scores, args.threshold)

    rm = RelationManager(normalizer)
    for i, (s, t, rel, sc) in enumerate(sorted(edges, key=lambda e: (e[0], e[1], e[2])), 1):
        m = meta[frozenset((s, t))]
        ev = m["evidence"][0] if m["evidence"] else ""
        c = normalizer.concepts_by_id[s]
        rm.relations.append(ExtractedRelation(
            relation_id=f"R{i:04d}", source_id=s, target_id=t, relation_type=rel, weight=round(sc, 4),
            page=c.page, chunk_id=c.chunk_id, evidence=ev, weight_source="llm_score", cooccurrence_count=m["cooc"]))
    build_and_save_dataset(normalizer, rm, out)
    write_pair_scores(out / "pair_scores.csv", normalizer, scores, meta)

    meta_out = {"model": args.model, "args": vars(args), "uses_book_order": False, "seconds": round(time.time() - t0, 1),
                "counters": dict(counters), "candidate_pairs": len(cands), "edges": len(edges),
                "cycle_edges_dropped": len(dropped), "backend_counters": dict(backend.counters) if backend else {}}
    (out / "run_meta.json").write_text(json.dumps(meta_out, indent=2))
    print(json.dumps(meta_out, indent=2))


if __name__ == "__main__":
    main()
