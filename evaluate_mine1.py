"""
Faithful MINE-1 methodology, applied to LearnKG's own knowledge graph.

kg-gen's MINE benchmark (kg-gen/experiments/MINE/_1_evaluation.py) measures
KG quality like this: embed every node, retrieve the top-k nodes most
similar to a question, expand each retrieved node to its 2-hop neighborhood
(KGGen.retrieve / retrieve_relevant_nodes / retrieve_context), concatenate
that into a context block, and have an LLM judge whether the context
actually contains the information needed to answer the question. Critically,
MINE judges the RETRIEVED CONTEXT itself, not a separately generated
natural-language answer — that's what distinguishes it from the production
chatbot pipeline (which this repo already has a separate eval harness for,
see evaluate_chatbot.py).

This script reproduces that exact methodology against LearnKG's own
concepts.csv/relations.csv:
  - Embeddings: sentence-transformers (same model family MINE uses,
    all-MiniLM-L6-v2) instead of kg-gen's full KGGen/dspy/litellm stack —
    LearnKG has no use for an LLM-provider abstraction layer since it
    already talks to Ollama directly (kg_chatbot/answer_generator.py).
  - 2-hop context expansion: reuses subgraph_builder._bfs_neighborhood
    (the same BFS this project already uses for the chatbot's localized
    subgraph) rather than reimplementing graph traversal.
  - LLM-as-judge: reuses evaluate_chatbot.py's judge_answer (Ollama if
    OLLAMA_MODEL is configured and reachable, deterministic token-overlap
    fallback otherwise) instead of a hardcoded GPT-5 judge.
  - Question set: reuses evaluate_chatbot.py's generate_eval_questions
    (auto-derived from the KG's own grounded concept definitions) instead
    of MINE's external Hugging Face essay/query dataset.

Run with:  python evaluate_mine1.py                 (from the LearnKG/ directory)
Optional:  OLLAMA_MODEL=zephyr:latest python evaluate_mine1.py   (LLM-judge variant)
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from evaluate_chatbot import EvalQuestion, generate_eval_questions, judge_answer
from kg_chatbot.kg_adapter import KGNode, KnowledgeGraph
from kg_chatbot.subgraph_builder import _bfs_neighborhood

DATA_DIR = Path(__file__).resolve().parent / "data_output" / "cureus"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # same model family MINE's _1_evaluation.py defaults to
TOP_K = 3
CONTEXT_HOP_DEPTH = 2  # matches KGGen.retrieve_context's default depth


@dataclass
class Mine1Result:
    question: str
    kind: str
    expected_ids: List[str]
    retrieved_ids: List[str] = field(default_factory=list)
    retrieval_hit: bool = False
    context_text: str = ""
    judge_score: int = 0


def _node_text(node: KGNode) -> str:
    """What gets embedded per node — label plus grounded definition, the
    same "entity + description" framing KGGen embeds for retrieval."""
    return f"{node.label}: {node.description}" if node.description else node.label


def load_embedding_model(model_name: str = EMBEDDING_MODEL_NAME):
    from sentence_transformers import SentenceTransformer

    print(f"[*] Loading embedding model '{model_name}' (downloads on first run)...")
    return SentenceTransformer(model_name)


def build_node_embeddings(kg: KnowledgeGraph, model) -> Dict[str, "object"]:
    nodes = kg.all_nodes()
    texts = [_node_text(n) for n in nodes]
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return {node.id: emb for node, emb in zip(nodes, embeddings)}


def retrieve_context(
    question: str,
    kg: KnowledgeGraph,
    model,
    node_embeddings: Dict[str, "object"],
    top_k: int = TOP_K,
    hop_depth: int = CONTEXT_HOP_DEPTH,
) -> tuple[Set[str], str]:
    """MINE's core retrieval step: embed the question, cosine-similarity
    top-k nodes, expand each to its 2-hop neighborhood, concatenate
    everything into one context block. Returns (retrieved_ids, context_text)."""
    import numpy as np

    q_emb = model.encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]

    ids = list(node_embeddings.keys())
    matrix = np.stack([node_embeddings[i] for i in ids])
    scores = matrix @ q_emb  # cosine similarity (embeddings are normalized)
    ranked = sorted(zip(ids, scores), key=lambda pair: -pair[1])
    seed_ids = [i for i, _ in ranked[:top_k]]

    retrieved_ids: Set[str] = set(seed_ids)
    for seed_id in seed_ids:
        neighborhood = _bfs_neighborhood(kg, seed_id, hop_depth)
        retrieved_ids |= set(neighborhood.keys())

    context_lines = []
    for nid in retrieved_ids:
        node = kg.get(nid)
        if node:
            context_lines.append(_node_text(node))
        for edge in kg.edges_of(nid):
            if edge.evidence:
                context_lines.append(edge.evidence)

    context_text = " ".join(dict.fromkeys(context_lines))  # dedup while preserving order
    return retrieved_ids, context_text


def run_mine1_eval(
    kg: KnowledgeGraph,
    questions: List[EvalQuestion],
    model,
    node_embeddings: Dict[str, "object"],
    use_ollama: bool,
    ollama_model: str,
) -> List[Mine1Result]:
    results: List[Mine1Result] = []
    for q in questions:
        retrieved_ids, context_text = retrieve_context(q.question, kg, model, node_embeddings)
        result = Mine1Result(
            question=q.question,
            kind=q.kind,
            expected_ids=q.expected_ids,
            retrieved_ids=sorted(retrieved_ids),
            retrieval_hit=all(eid in retrieved_ids for eid in q.expected_ids),
        )
        result.context_text = context_text
        expected_text = q.expected_text or " ".join(
            kg.get(eid).description for eid in q.expected_ids if kg.get(eid)
        )
        result.judge_score = judge_answer(context_text, expected_text, use_ollama, ollama_model)
        results.append(result)
    return results


def print_report(results: List[Mine1Result]) -> None:
    for r in results:
        status = "HIT " if r.retrieval_hit else "MISS"
        print(f"[{status}] ({r.kind}) {r.question}")
        print(f"         expected={r.expected_ids} retrieved={r.retrieved_ids} judge={r.judge_score}")

    def _accuracy(subset: List[Mine1Result], field_name: str) -> float:
        if not subset:
            return 0.0
        return 100.0 * sum(getattr(r, field_name) for r in subset) / len(subset)

    normal = [r for r in results if r.kind == "normal"]
    comparison = [r for r in results if r.kind == "comparison"]

    print("\n" + "=" * 60)
    print("  MINE-1 METHODOLOGY — EVAL SUMMARY (embedding retrieval + 2-hop context + LLM judge)")
    print("=" * 60)
    print(f"  Total questions       : {len(results)}")
    print(f"  Normal retrieval acc. : {_accuracy(normal, 'retrieval_hit'):.1f}% ({len(normal)} questions)")
    print(f"  Comparison retr. acc. : {_accuracy(comparison, 'retrieval_hit'):.1f}% ({len(comparison)} questions)")
    print(f"  Judge (context grounds expected answer) : {_accuracy(results, 'judge_score'):.1f}%")
    print("=" * 60)


def main() -> None:
    import os

    if not (DATA_DIR / "concepts.csv").exists():
        raise FileNotFoundError(
            f"No concepts.csv found at {DATA_DIR} — run the pipeline first "
            f"(python run_pipeline.py --pipeline educational --dataset cureus --no-llm)."
        )

    kg = KnowledgeGraph.from_csv(
        concepts_csv=DATA_DIR / "concepts.csv",
        relations_csv=DATA_DIR / "relations.csv",
        concept_stats_csv=DATA_DIR / "concept_stats.csv",
    )
    print(f"[*] Loaded KG: {len(kg.nodes)} concepts, {kg.graph.number_of_edges()} relations.")

    questions = generate_eval_questions(kg)
    print(f"[*] Generated {len(questions)} eval questions from the KG's own grounded definitions.\n")

    model = load_embedding_model()
    node_embeddings = build_node_embeddings(kg, model)

    ollama_model = os.environ.get("OLLAMA_MODEL")
    use_ollama = bool(ollama_model)

    results = run_mine1_eval(kg, questions, model, node_embeddings, use_ollama, ollama_model)
    print_report(results)

    output_path = DATA_DIR / "mine1_eval_results.json"
    output_path.write_text(json.dumps([asdict(r) for r in results], indent=2))
    print(f"\n[+] Full results written to {output_path}")


if __name__ == "__main__":
    main()
