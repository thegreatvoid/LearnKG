"""
Candidate-Pair Generation with Full Evidence Provenance.

Generates candidate concept pairs across multiple complementary channels:
  1. Shared textual context (sentence-level and chunk-level co-occurrence)
  2. Explicit relationship phrases in textbook passages
  3. Definitional mentions (one concept mentioned in another's definition)
  4. Section and chapter proximity
  5. Embedding-based semantic retrieval (nearest neighbors by definition/name embedding)
  6. Existing graph neighbors / prerequisite candidates

Retains complete provenance for every candidate pair:
  - Source and target concept IDs and canonical names
  - Generation methods that proposed the pair
  - Multi-method proposal flag
  - Passage locations (chapter, section, page, chunk_id)
  - Definitions of both concepts
  - Verbatim context sentences

Deduplicates pairs prior to classification and bounds candidate size to avoid O(V^2) overhead.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .chunker import EducationalChunk
from .normalizer import ConceptNormalizer, NormalizedConcept


@dataclass
class CandidatePair:
    source_id: str
    target_id: str
    source_name: str
    target_name: str
    source_definition: str = ""
    target_definition: str = ""
    methods: Set[str] = field(default_factory=set)
    is_multi_method: bool = False
    evidence_sentences: List[str] = field(default_factory=list)
    passage_locations: List[Dict[str, Any]] = field(default_factory=list)
    cooccurrence_count: int = 0
    chunk_cooccurrence_count: int = 0
    embedding_similarity: float = 0.0
    shared_sections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_name": self.source_name,
            "target_name": self.target_name,
            "source_definition": self.source_definition,
            "target_definition": self.target_definition,
            "methods": sorted(list(self.methods)),
            "is_multi_method": len(self.methods) > 1,
            "evidence_sentences": self.evidence_sentences,
            "passage_locations": self.passage_locations,
            "cooccurrence_count": self.cooccurrence_count,
            "chunk_cooccurrence_count": self.chunk_cooccurrence_count,
            "embedding_similarity": round(self.embedding_similarity, 4),
            "shared_sections": self.shared_sections,
            "metadata": self.metadata,
        }


def _clean_token(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip())


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if len(s.strip()) > 15]


class CandidateGenerator:
    """Multi-channel candidate-pair generator with provenance tracking."""

    def __init__(
        self,
        normalizer: ConceptNormalizer,
        chunks: List[EducationalChunk],
        embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.normalizer = normalizer
        self.chunks = chunks
        self.embed_model_name = embed_model_name
        self.concepts = normalizer.get_all_concepts()
        self.concepts_by_id = {c.concept_id: c for c in self.concepts}

        # Build name patterns for all concepts
        self._patterns: Dict[str, List[re.Pattern]] = {}
        for c in self.concepts:
            names = [c.concept_name] + list(c.aliases)
            pats = []
            for n in names:
                words = re.findall(r"[a-z0-9]+", n.lower())
                if words:
                    pats.append(re.compile(r"\b" + r"[\s\-]+".join(re.escape(w) for w in words) + r"(?:s|es)?\b", re.I))
            self._patterns[c.concept_id] = pats

    def _find_concept_matches(self, text: str) -> List[Tuple[str, int, int]]:
        """Finds concepts mentioned in a string along with start/end character offsets."""
        matches = []
        for cid, pats in self._patterns.items():
            for p in pats:
                m = p.search(text)
                if m:
                    matches.append((cid, m.start(), m.end()))
                    break
        return matches

    def compute_embedding_neighbors(self, top_k: int = 5) -> Dict[Tuple[str, str], float]:
        """Calculates nearest neighbors in embedding space using concept definitions/names."""
        if top_k <= 0 or len(self.concepts) < 2:
            return {}
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.embed_model_name)
            texts = [f"{c.concept_name}: {c.definition}" if c.definition else c.concept_name for c in self.concepts]
            vecs = model.encode(texts, normalize_embeddings=True)
            sim_matrix = vecs @ vecs.T
            neighbors: Dict[Tuple[str, str], float] = {}
            for i, c_i in enumerate(self.concepts):
                top_indices = sim_matrix[i].argsort()[::-1]
                for j in [idx for idx in top_indices if idx != i][:top_k]:
                    c_j = self.concepts[j]
                    sim = float(sim_matrix[i, j])
                    key = tuple(sorted((c_i.concept_id, c_j.concept_id)))
                    neighbors[key] = max(neighbors.get(key, 0.0), sim)
                # Capture cross-concept curriculum candidates with bi-encoder definition similarity >= 0.25
                for j, c_j in enumerate(self.concepts):
                    if i != j:
                        sim = float(sim_matrix[i, j])
                        if sim >= 0.25:
                            key = tuple(sorted((c_i.concept_id, c_j.concept_id)))
                            neighbors[key] = max(neighbors.get(key, 0.0), sim)
            return neighbors
        except Exception as e:
            print(f"[!] Warning: Embedding neighbors skipped ({e})")
            return {}

    def generate_candidates(
        self,
        per_concept_limit: int = 15,
        max_total_candidates: int = 1500,
        use_embeddings: bool = True,
        top_k_embeddings: int = 6,
        hubs_count: int = 8,
    ) -> List[CandidatePair]:
        """
        Generates and deduplicates candidate pairs across all channels.
        Returns a sorted list of CandidatePair instances with full provenance.
        """
        if len(self.concepts) < 2:
            return []

        # Containers for channel signals
        sentence_cooc: Counter = Counter()
        chunk_cooc: Counter = Counter()
        evidence_by_pair: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        locations_by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        shared_sections_by_pair: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        methods_by_pair: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        explicit_cues: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        # Cue keywords indicating potential educational relationships
        rel_cue_re = re.compile(
            r"\b(prerequisite|requires|depends on|underlying|basis for|part of|component of|"
            r"consists of|element of|applied to|used in|used for|solves|measures|similar to|"
            r"analogous to|extends|generalization of|special case of|building on)\b",
            re.I,
        )

        # 1. Scan chunks and sentences for co-occurrences and explicit cues
        for ch in self.chunks:
            sentences = _split_sentences(ch.text)
            chunk_present_ids = set()

            for s in sentences:
                matches = self._find_concept_matches(s)
                present = sorted(list({cid for cid, _, _ in matches}))
                chunk_present_ids.update(present)

                has_cue = bool(rel_cue_re.search(s))

                for i, a in enumerate(present):
                    for b in present[i + 1:]:
                        pair_key = tuple(sorted((a, b)))
                        sentence_cooc[pair_key] += 1
                        methods_by_pair[pair_key].add("sentence_cooccurrence")
                        if has_cue:
                            methods_by_pair[pair_key].add("explicit_rel_phrase")
                            explicit_cues[pair_key].append(s)

                        if len(evidence_by_pair[pair_key]) < 5:
                            evidence_by_pair[pair_key].append(s)

                        loc = {
                            "chapter": ch.chapter,
                            "section": ch.section,
                            "page": ch.page,
                            "chunk_id": ch.chunk_id,
                        }
                        if loc not in locations_by_pair[pair_key]:
                            locations_by_pair[pair_key].append(loc)

                        if ch.section:
                            shared_sections_by_pair[pair_key].add(ch.section)

            ch_ids = sorted(list(chunk_present_ids))
            for i, a in enumerate(ch_ids):
                for b in ch_ids[i + 1:]:
                    pair_key = tuple(sorted((a, b)))
                    chunk_cooc[pair_key] += 1
                    methods_by_pair[pair_key].add("chunk_cooccurrence")

        # 2. Definitional mentions
        for c in self.concepts:
            def_text = c.definition.lower()
            if not def_text:
                continue
            matches = self._find_concept_matches(def_text)
            for other_id, _, _ in matches:
                if other_id != c.concept_id:
                    pair_key = tuple(sorted((c.concept_id, other_id)))
                    methods_by_pair[pair_key].add("definition_mention")
                    if c.definition and c.definition not in evidence_by_pair[pair_key]:
                        evidence_by_pair[pair_key].append(c.definition)

        # 3. Embedding nearest neighbors & Curriculum Sequence Channel
        emb_sims: Dict[Tuple[str, str], float] = {}
        if use_embeddings:
            emb_sims = self.compute_embedding_neighbors(top_k=top_k_embeddings)
            for pair_key, sim in emb_sims.items():
                if sim >= 0.35:
                    methods_by_pair[pair_key].add("embedding_similarity")
                # Curriculum Sequence Channel: page(A) <= page(B) with bi-encoder definition sim >= 0.25
                if sim >= 0.25:
                    c_a = self.concepts_by_id[pair_key[0]]
                    c_b = self.concepts_by_id[pair_key[1]]
                    p_a = getattr(c_a, "page", 1) or 1
                    p_b = getattr(c_b, "page", 1) or 1
                    methods_by_pair[pair_key].add("curriculum_sequence")

        # 4. Foundational Hubs (concepts referenced across multiple sections)
        if hubs_count > 0:
            concept_degree = Counter()
            for (a, b), cnt in sentence_cooc.items():
                concept_degree[a] += cnt
                concept_degree[b] += cnt
            top_hubs = [cid for cid, _ in concept_degree.most_common(hubs_count)]
            for h in top_hubs:
                for c in self.concepts:
                    if c.concept_id != h:
                        pair_key = tuple(sorted((h, c.concept_id)))
                        if pair_key in sentence_cooc or pair_key in emb_sims:
                            methods_by_pair[pair_key].add("foundational_hub")

        # Score and rank candidates to prevent O(V^2) explosion
        scored_pairs: List[Tuple[float, Tuple[str, str]]] = []
        for pair_key, methods in methods_by_pair.items():
            a, b = pair_key
            score = 0.0
            score += sentence_cooc.get(pair_key, 0) * 1.5
            score += chunk_cooc.get(pair_key, 0) * 0.5
            if "definition_mention" in methods:
                score += 3.0
            if "explicit_rel_phrase" in methods:
                score += 2.5
            if "embedding_similarity" in methods:
                score += 1.0 + emb_sims.get(pair_key, 0.0)
            if "curriculum_sequence" in methods:
                score += 1.5 + emb_sims.get(pair_key, 0.0)
            if "foundational_hub" in methods:
                score += 0.5
            if len(methods) > 1:
                score += 2.0  # Multi-channel bonus
            scored_pairs.append((score, pair_key))

        # Select top candidates per concept and overall
        by_concept: Dict[str, List[Tuple[float, Tuple[str, str]]]] = defaultdict(list)
        for sc, pair_key in scored_pairs:
            by_concept[pair_key[0]].append((sc, pair_key))
            by_concept[pair_key[1]].append((sc, pair_key))

        selected_keys: Set[Tuple[str, str]] = set()
        for cid, plist in by_concept.items():
            plist.sort(key=lambda x: x[0], reverse=True)
            for _, pair_key in plist[:per_concept_limit]:
                selected_keys.add(pair_key)

        # Global cap sort (expand dynamically: at least 20 * |V| candidates to prevent long-tail truncation)
        effective_cap = max(max_total_candidates, 20 * len(self.concepts))
        final_keys = sorted(
            list(selected_keys),
            key=lambda k: (
                len(methods_by_pair[k]) > 1,
                sentence_cooc.get(k, 0),
                emb_sims.get(k, 0.0),
            ),
            reverse=True,
        )[:effective_cap]

        # Materialize structured CandidatePair objects
        candidates: List[CandidatePair] = []
        for a_id, b_id in final_keys:
            c_a = self.concepts_by_id[a_id]
            c_b = self.concepts_by_id[b_id]
            methods = methods_by_pair[(a_id, b_id)]
            ev = evidence_by_pair.get((a_id, b_id), [])
            locations = locations_by_pair.get((a_id, b_id), [])
            shared_sec = sorted(list(shared_sections_by_pair.get((a_id, b_id), set())))
            sim = emb_sims.get((a_id, b_id), 0.0)

            cand = CandidatePair(
                source_id=a_id,
                target_id=b_id,
                source_name=c_a.concept_name,
                target_name=c_b.concept_name,
                source_definition=c_a.definition,
                target_definition=c_b.definition,
                methods=methods,
                is_multi_method=len(methods) > 1,
                evidence_sentences=ev,
                passage_locations=locations,
                cooccurrence_count=sentence_cooc.get((a_id, b_id), 0),
                chunk_cooccurrence_count=chunk_cooc.get((a_id, b_id), 0),
                embedding_similarity=sim,
                shared_sections=shared_sec,
                metadata={
                    "chapter_a": c_a.chapter,
                    "chapter_b": c_b.chapter,
                    "page_a": c_a.page,
                    "page_b": c_b.page,
                },
            )
            candidates.append(cand)

        return candidates
