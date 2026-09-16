"""
Step 4: Concept Extraction
Hybrid approach:
  - Extracts candidate educational concepts using deterministic NLP rules,
    capitalization cues, acronym detection, and textbook patterns.
  - Refines and enriches with LLM when available.
  - Classifies concepts into: Algorithm, Model, Formula, Theory, Component.
"""

import re
from typing import Dict, List, Set
from .chunker import EducationalChunk

STOPWORDS = {
    "a", "an", "the", "this", "that", "these", "those", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "to", "from",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "figure", "table", "section", "chapter", "page", "study", "analysis",
    "example", "exercise", "results", "author", "authors", "approach", "method"
}

TYPE_KEYWORDS = {
    "Algorithm": ["algorithm", "descent", "search", "sort", "optimization", "method", "procedure", "backpropagation", "adam", "rmsprop"],
    "Model": ["model", "network", "system", "architecture", "classifier", "regressor", "regression"],
    "Formula": ["formula", "equation", "loss", "metric", "function", "score", "index", "ratio", "derivative", "gradient", "sum", "error"],
    "Theory": ["theory", "theorem", "principle", "law", "hypothesis", "standard", "policy", "calculus", "learning", "classification"],
    "Component": ["layer", "node", "unit", "weight", "bias", "cadre", "worker", "division", "component", "parameter", "neuron", "rate"],
}


def infer_concept_type(concept_name: str) -> str:
    """Infers the concept_type based on suffix or keywords."""
    lowered = concept_name.lower()
    for c_type, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                return c_type
    return "Component"


# Core educational domain terms recognized across textbook chapters
DOMAIN_TERMS = [
    "Machine Learning", "Calculus", "Multivariable Calculus", "Derivative",
    "Partial Derivatives", "Gradient", "Loss Function", "Prediction Error",
    "Chain Rule", "Gradient Descent", "Learning Rate", "Mini-Batch Gradient Descent",
    "Neural Networks", "Biological Neurons", "Weighted Sum", "Bias Term",
    "Nonlinear Activation Function", "Input Layer", "Hidden Layers", "Output Layer",
    "Deep Neural Networks", "Deep Learning", "Weights and Biases", "Backpropagation",
    "Adam", "RMSProp", "Linear Regression", "Mean Squared Error", "Logistic Regression",
    "Binary Classification", "Sigmoid Function",
]


def extract_candidate_concepts_from_text(text: str) -> List[str]:
    """
    Extracts candidate educational terms using multi-word noun phrase patterns,
    capitalized phrases, acronyms, and textbook domain terms.
    """
    candidates: Set[str] = set()

    # 1. Capitalized multi-word terms on same line (2 to 4 words, e.g. "Gradient Descent")
    cap_phrase = re.findall(r"\b([A-Z][a-z]+(?:[^\S\r\n]+[A-Z][a-z]+){1,3})\b", text)
    for p in cap_phrase:
        p_clean = p.strip()
        first_word = p_clean.split()[0].lower()
        if first_word not in STOPWORDS and len(p_clean) > 3:
            candidates.add(p_clean)

    # 2. All-caps Acronyms and camelCase terms (e.g., "WHO", "IPHS", "NMC", "GD", "RMSProp", "Adam")
    acronyms = re.findall(r"\b(?:[A-Z]{2,6}|RMSProp|Adam)\b", text)
    for acr in acronyms:
        if acr.lower() not in STOPWORDS and acr not in {"AND", "THE", "FOR", "NOT"}:
            candidates.add(acr)

    # 3. Quoted or italicized concepts ("...", '...')
    quoted = re.findall(r"[\"']([A-Za-z0-9\s\-]{3,30})[\"']", text)
    for q in quoted:
        q_clean = q.strip()
        if len(q_clean.split()) <= 4 and q_clean.lower() not in STOPWORDS:
            candidates.add(q_clean.title())

    # 4. Keywords: definition/concept indicators
    def_matches = re.findall(r"(?:defined\s+as|known\s+as|termed|called|referred\s+to\s+as)\s+(?:an?|the)?\s*([A-Za-z0-9\s\-]{3,30})", text, re.IGNORECASE)
    for d in def_matches:
        d_clean = d.strip()
        if len(d_clean.split()) <= 3 and d_clean.lower() not in STOPWORDS:
            candidates.add(d_clean.title())

    # 5. Core educational domain terms present in this text
    for dt in DOMAIN_TERMS:
        if re.search(rf"\b{re.escape(dt)}\b", text, re.IGNORECASE):
            candidates.add(dt)

    return list(candidates)


def extract_concepts_for_chunk(chunk: EducationalChunk, llm_concepts: List[dict] = None) -> List[dict]:
    """
    Combines rule-based candidates with LLM-extracted concepts.
    Returns list of concept dicts: {concept_name, aliases, concept_type, definition, evidence}
    """
    results: Dict[str, dict] = {}

    # If LLM extracted concepts are provided
    if llm_concepts:
        for c in llm_concepts:
            name = str(c.get("concept_name", "")).strip()
            if name:
                results[name.lower()] = {
                    "concept_name": name,
                    "aliases": c.get("aliases", []),
                    "concept_type": c.get("concept_type", infer_concept_type(name)),
                    "definition": c.get("definition", ""),
                    "evidence": c.get("evidence", ""),
                }

    # Supplement with deterministic candidates
    candidates = extract_candidate_concepts_from_text(chunk.text)
    for cand in candidates:
        cand_lower = cand.lower()
        if cand_lower not in results:
            results[cand_lower] = {
                "concept_name": cand,
                "aliases": [],
                "concept_type": infer_concept_type(cand),
                "definition": "",
                "evidence": "",
            }

    return list(results.values())
