"""
Chatbot retrieval/answer-quality eval harness — LearnKG's own equivalent of
kg-gen's MINE benchmark (kg-gen/experiments/MINE/), adapted to this project:

  - MINE regenerates a KG from essay text, retrieves via embeddings, and
    scores answers with a hardcoded GPT-5 LLM judge against an external
    Hugging Face dataset of pre-written questions.
  - This harness instead auto-generates its question set from LearnKG's own
    concepts.csv (every concept already carries a verbatim, grounded
    definition — see educational_pipeline/definition_extractor.py), runs
    those questions through the exact same functions kg_chatbot/main.py
    uses, and judges answers with the project's own Ollama integration
    (falling back to a deterministic token-overlap check when no LLM is
    configured, so this always runs fully offline like the rest of the app).

No new dependencies, no external dataset, no hardcoded domain vocabulary.

Run with:  python evaluate_chatbot.py           (from the LearnKG/ directory)
Optional:  OLLAMA_MODEL=zephyr:latest python evaluate_chatbot.py   (LLM judge)
"""

import json
import os
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from kg_chatbot.answer_generator import TemplateAnswerGenerator, get_answer_generator
from kg_chatbot.comparison import build_comparison_side
from kg_chatbot.concept_matcher import _tokenize, match_concept
from kg_chatbot.conversation import ConversationStore
from kg_chatbot.intent_classifier import classify_query
from kg_chatbot.kg_adapter import KGNode, KnowledgeGraph
from kg_chatbot.subgraph_builder import build_localized_subgraph

DATA_DIR = Path(__file__).resolve().parent / "data_output" / "cureus"

MAX_NORMAL_QUESTIONS = 20
MAX_COMPARISON_QUESTIONS = 5
MIN_DEFINITION_LEN = 20
JUDGE_OVERLAP_THRESHOLD = 0.3


@dataclass
class EvalQuestion:
    question: str
    kind: str  # "normal" | "comparison"
    expected_ids: List[str]
    expected_text: str = ""


@dataclass
class EvalResult:
    question: str
    kind: str
    expected_ids: List[str]
    retrieved_ids: List[str] = field(default_factory=list)
    retrieval_hit: bool = False
    answer: str = ""
    answer_source: str = ""
    judge_score: int = 0


def generate_eval_questions(kg: KnowledgeGraph) -> List[EvalQuestion]:
    """Builds ground-truth eval questions directly from the KG itself — no
    external dataset. Works the same way regardless of which document the
    pipeline was run on."""
    questions: List[EvalQuestion] = []

    definable = [n for n in kg.all_nodes() if len(n.description.strip()) >= MIN_DEFINITION_LEN]
    for node in definable[:MAX_NORMAL_QUESTIONS]:
        questions.append(EvalQuestion(
            question=f"What is {node.label}?",
            kind="normal",
            expected_ids=[node.id],
            expected_text=node.description,
        ))

    by_type: dict[str, List[KGNode]] = {}
    for node in kg.all_nodes():
        if node.concept_type:
            by_type.setdefault(node.concept_type, []).append(node)

    comparison_pairs = []
    for nodes in by_type.values():
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                comparison_pairs.append((nodes[i], nodes[j]))

    rng = random.Random(0)  # deterministic sample across runs
    rng.shuffle(comparison_pairs)
    for a, b in comparison_pairs[:MAX_COMPARISON_QUESTIONS]:
        questions.append(EvalQuestion(
            question=f"What is the difference between {a.label} and {b.label}?",
            kind="comparison",
            expected_ids=[a.id, b.id],
        ))

    return questions


def judge_answer(answer: str, expected_text: str, use_ollama: bool, ollama_model: Optional[str]) -> int:
    """0/1 groundedness judge — mirrors MINE's EvaluateResponse intent
    ("does the context contain the information in the correct answer") but
    reuses this project's own Ollama plumbing instead of dspy + GPT-5, and
    falls back to a deterministic token-overlap check when no LLM is
    configured or reachable, so the harness never hard-fails offline."""
    if use_ollama and ollama_model:
        try:
            import requests

            base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            prompt = (
                "Does the ANSWER contain the information stated in the EXPECTED text? "
                "Reply with only the single digit 1 (yes) or 0 (no).\n\n"
                f"EXPECTED:\n{expected_text}\n\nANSWER:\n{answer}\n\nReply:"
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
            print(f"[evaluate_chatbot] Ollama judge failed ({exc}); falling back to token-overlap for this question.")

    answer_tokens = _tokenize(answer)
    expected_tokens = _tokenize(expected_text)
    if not expected_tokens:
        return 0
    overlap = len(answer_tokens & expected_tokens) / len(expected_tokens)
    return 1 if overlap >= JUDGE_OVERLAP_THRESHOLD else 0


def run_eval(kg: KnowledgeGraph, questions: List[EvalQuestion]) -> List[EvalResult]:
    answer_generator = get_answer_generator()
    ollama_model = os.environ.get("OLLAMA_MODEL")
    use_ollama = answer_generator.name == "ollama"
    conversations = ConversationStore()
    results: List[EvalResult] = []

    for q in questions:
        conv = conversations.get(f"eval-{q.question}")
        result = EvalResult(question=q.question, kind=q.kind, expected_ids=q.expected_ids)

        if q.kind == "comparison":
            label_a, label_b = _split_comparison_question(q)
            side_a = build_comparison_side(kg, label_a, conv)
            side_b = build_comparison_side(kg, label_b, conv)
            retrieved = [s.match.node.id for s in (side_a, side_b) if s is not None]
            result.retrieved_ids = retrieved
            result.retrieval_hit = set(retrieved) == set(q.expected_ids)
            answer_text = "; ".join(s.match.node.label for s in (side_a, side_b) if s)
            result.answer = answer_text
            result.answer_source = "template"
            result.judge_score = 1 if result.retrieval_hit else 0
            results.append(result)
            continue

        match = match_concept(q.question, kg)
        if match is None:
            results.append(result)
            continue

        center = match.node
        result.retrieved_ids = [center.id]
        result.retrieval_hit = center.id in q.expected_ids

        question_tokens = _tokenize(q.question)
        prereqs, related = build_localized_subgraph(kg, center.id, question_tokens)
        edges = kg.edges_of(center.id)
        try:
            answer_text = answer_generator.generate(q.question, center, edges, kg.get)
            source = answer_generator.name
        except Exception:
            answer_text = TemplateAnswerGenerator().generate(q.question, center, edges, kg.get)
            source = "template"
        conv.mark_known(center.id)

        result.answer = answer_text
        result.answer_source = source
        result.judge_score = judge_answer(answer_text, q.expected_text, use_ollama, ollama_model)
        results.append(result)

    return results


def _split_comparison_question(q: EvalQuestion) -> tuple[str, str]:
    intent = classify_query(q.question)
    if intent.query_type == "comparison" and intent.phrase_a and intent.phrase_b:
        return intent.phrase_a, intent.phrase_b
    # Shouldn't happen for our own generated phrasing, but degrade gracefully.
    return q.question, q.question


def print_report(results: List[EvalResult]) -> None:
    for r in results:
        status = "HIT " if r.retrieval_hit else "MISS"
        print(f"[{status}] ({r.kind}) {r.question}")
        print(f"         expected={r.expected_ids} retrieved={r.retrieved_ids} judge={r.judge_score}")

    def _accuracy(subset: List[EvalResult], field_name: str) -> float:
        if not subset:
            return 0.0
        return 100.0 * sum(getattr(r, field_name) for r in subset) / len(subset)

    normal = [r for r in results if r.kind == "normal"]
    comparison = [r for r in results if r.kind == "comparison"]

    print("\n" + "=" * 60)
    print("  EVAL SUMMARY")
    print("=" * 60)
    print(f"  Total questions       : {len(results)}")
    print(f"  Normal retrieval acc. : {_accuracy(normal, 'retrieval_hit'):.1f}% ({len(normal)} questions)")
    print(f"  Comparison retr. acc. : {_accuracy(comparison, 'retrieval_hit'):.1f}% ({len(comparison)} questions)")
    print(f"  Judge (groundedness)  : {_accuracy(results, 'judge_score'):.1f}%")
    print("=" * 60)


def main() -> None:
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

    results = run_eval(kg, questions)
    print_report(results)

    output_path = DATA_DIR / "eval_results.json"
    output_path.write_text(json.dumps([asdict(r) for r in results], indent=2))
    print(f"\n[+] Full results written to {output_path}")


if __name__ == "__main__":
    main()
