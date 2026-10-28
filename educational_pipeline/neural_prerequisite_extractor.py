"""
Neural Transformer / Cross-Encoder Prerequisite Extraction Module.

Uses pre-trained cross-encoder models on GPU/CPU to score pedagogical dependency
between concepts grounded in textbook context and curriculum sequence.
Enforces DAG acyclicity and outputs evidence-backed prerequisite relations.
"""

from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Tuple, Set
import networkx as nx
import torch
from sentence_transformers import CrossEncoder

from .normalizer import ConceptNormalizer, NormalizedConcept
from .chunker import EducationalChunk


class NeuralPrerequisiteExtractor:
    """
    Extracts directional prerequisite relationships using a neural Cross-Encoder model.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        threshold: float = -1.5,
        device: Optional[str] = None,
    ):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.threshold = threshold
        self.model_name = model_name
        print(f"[*] Initializing Neural Prerequisite Cross-Encoder ({model_name}) on {self.device}...")
        self.model = CrossEncoder(model_name, device=self.device)

    def extract_prerequisites(
        self,
        normalizer: ConceptNormalizer,
        chunks: List[EducationalChunk],
        full_text: Optional[str] = None,
    ) -> List[Dict]:
        """
        Extracts directional prerequisite edges (A -> B: A is prerequisite for B)
        from concept contexts and textbook structure.
        """
        concepts = normalizer.get_all_concepts()
        if len(concepts) < 2:
            return []

        # 1. Build contextual profile for each concept
        concept_profiles = {}
        for c in concepts:
            # Gather relevant sentences/paragraphs
            mentions = []
            for chunk in chunks:
                if c.concept_name.lower() in chunk.text.lower():
                    # Extract sentence
                    sents = re.split(r"(?<=[.?!])\s+", chunk.text)
                    for s in sents:
                        if c.concept_name.lower() in s.lower() and len(s.strip()) > 20:
                            mentions.append(s.strip())
                            if len(mentions) >= 3:
                                break
                if len(mentions) >= 3:
                    break

            primary_ctx = c.definition if c.definition else (" ".join(mentions[:2]) if mentions else c.concept_name)
            concept_profiles[c.concept_id] = {
                "concept": c,
                "name": c.concept_name,
                "page": c.page,
                "definition": c.definition,
                "context": primary_ctx,
                "mentions": mentions,
            }

        # 2. Generate candidate pairs with soft page penalty (instead of strict cutoff)
        candidates = []
        pair_metadata = []

        for c_src in concepts:
            src_prof = concept_profiles[c_src.concept_id]
            for c_tgt in concepts:
                if c_src.concept_id == c_tgt.concept_id:
                    continue
                tgt_prof = concept_profiles[c_tgt.concept_id]

                # Soft page penalty: concepts appearing later receive penalty proportional to delta
                page_delta = tgt_prof["page"] - src_prof["page"]
                # If target appears before source, apply sharp penalty
                soft_page_penalty = 0.0 if page_delta >= 0 else min(5.0, abs(page_delta) * 0.5)

                # Prepare Cross-Encoder prompt
                query = f"Foundational prerequisite in geometry: {src_prof['name']}"
                tgt_evidence = tgt_prof["mentions"][0] if tgt_prof["mentions"] else tgt_prof["context"]
                doc = f"Topic: {tgt_prof['name']}. Definition: {tgt_prof['context']}. Evidence: {tgt_evidence}"

                candidates.append((query, doc))
                pair_metadata.append((c_src, c_tgt, tgt_evidence, soft_page_penalty))

        if not candidates:
            return []

        # 3. Batch neural scoring on GPU/CPU
        print(f"[*] Scoring {len(candidates)} candidate concept pairs with Neural Cross-Encoder...")
        scores = self.model.predict(candidates, batch_size=64, show_progress_bar=False)

        # 4. Filter by threshold after soft page penalty, target-relative top-k scoring, and enforce DAG acyclicity
        by_target: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for i, score in enumerate(scores):
            c_src, c_tgt, evidence, page_pen = pair_metadata[i]
            calibrated_score = float(score) - page_pen
            if calibrated_score >= self.threshold:
                by_target[c_tgt.concept_id].append({
                    "src": c_src,
                    "tgt": c_tgt,
                    "score": calibrated_score,
                    "raw_score": float(score),
                    "evidence": evidence,
                })

        # Apply target-relative top-k logit scoring (keep top-k strongest incoming prerequisites per concept)
        scored_pairs = []
        for tgt_id, cands in by_target.items():
            cands.sort(key=lambda x: x["score"], reverse=True)
            for item in cands[:12]:  # Keep up to 12 calibrated predecessor candidates per target
                scored_pairs.append(item)

        scored_pairs.sort(key=lambda x: x["score"], reverse=True)

        # Build DAG incrementally to guarantee 0 cycles
        G_dag = nx.DiGraph()
        for c in concepts:
            G_dag.add_node(c.concept_id)

        accepted_relations = []
        for pair in scored_pairs:
            s_id = pair["src"].concept_id
            t_id = pair["tgt"].concept_id

            # Check cycle before adding
            G_dag.add_edge(s_id, t_id)
            if not nx.is_directed_acyclic_graph(G_dag):
                # Reject cycle-inducing edge
                G_dag.remove_edge(s_id, t_id)
                continue

            # Scale neural score from raw logit (e.g. -1.5 to +5.0) to normalized 0.1-1.0 range
            raw_s = pair["score"]
            norm_weight = min(1.0, max(0.1, (raw_s + 2.5) / 7.5))

            accepted_relations.append({
                "source_name": pair["src"].concept_name,
                "target_name": pair["tgt"].concept_name,
                "relation_type": "Prerequisite",
                "weight": round(norm_weight, 4),
                "raw_logit": round(pair["raw_score"], 4),
                "evidence": pair["evidence"],
                "page": pair["tgt"].page,
                "chunk_id": pair["tgt"].chunk_id,
            })

        print(f"[+] Neural model accepted {len(accepted_relations)} DAG-acyclic prerequisite relations.")
        return accepted_relations
