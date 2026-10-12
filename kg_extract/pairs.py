"""Stage 3: candidate concept pairs from the text itself (no all-pairs, no book order)."""

from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from educational_pipeline.normalizer import ConceptNormalizer

from .text import norm, split_sentences


def concept_names(c) -> List[str]:
    return [c.concept_name] + sorted(c.aliases)


def embedding_neighbors(concepts, k: int, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Top-k nearest concepts by embedding of 'name: definition' (catches conceptual links with no shared sentence)."""
    from sentence_transformers import SentenceTransformer
    texts = [f"{c.concept_name}: {c.definition}" if c.definition else c.concept_name for c in concepts]
    E = SentenceTransformer(model_name).encode(texts, normalize_embeddings=True)
    sim = E @ E.T
    out = {}
    for i, c in enumerate(concepts):
        order = sim[i].argsort()[::-1]
        for j in [x for x in order if x != i][:k]:
            key = tuple(sorted((c.concept_id, concepts[j].concept_id)))
            out[key] = max(out.get(key, 0.0), float(sim[i, j]))
    return out


def hub_set_has(k, hub_ids):
    return k[0] in hub_ids or k[1] in hub_ids


def generate_candidates(normalizer: ConceptNormalizer, chunks, per_concept: int = 8, max_pairs: int = 1500,
                        embed_neighbors: int = 0, hubs: int = 0):
    """Returns (candidates, sentence_index). candidate = {a, b, score, cooc, evidence[list of sentences]}."""
    concepts = normalizer.get_all_concepts()
    names = {c.concept_id: [norm(n) for n in concept_names(c) if n.strip()] for c in concepts}
    cooc: Counter = Counter()
    chunk_cooc: Counter = Counter()
    evidence: Dict[Tuple[str, str], List[str]] = defaultdict(list)

    for ch in chunks:
        in_chunk = set()
        for s in split_sentences(ch.text):
            sn = norm(s)
            present = sorted(cid for cid, ns in names.items() if any(n in sn for n in ns))
            in_chunk.update(present)
            for i, a in enumerate(present):
                for b in present[i + 1:]:
                    cooc[(a, b)] += 1
                    if len(evidence[(a, b)]) < 3:
                        evidence[(a, b)].append(s)
        ch_ids = sorted(in_chunk)
        for i, a in enumerate(ch_ids):
            for b in ch_ids[i + 1:]:
                chunk_cooc[(a, b)] += 1

    defmention: Counter = Counter()
    for c in concepts:
        dn = norm(c.definition)
        for o in concepts:
            if o.concept_id != c.concept_id and any(n in dn for n in names[o.concept_id]):
                defmention[tuple(sorted((c.concept_id, o.concept_id)))] += 1

    score: Counter = Counter()
    for k, v in cooc.items():
        score[k] += v
    for k, v in defmention.items():
        score[k] += 2 * v
    for k, v in chunk_cooc.items():
        score[k] += 0.25 * v

    if embed_neighbors:
        for k, sim in embedding_neighbors(concepts, embed_neighbors).items():
            score[k] += 1.0 + sim  # ensures neighbours survive the per-concept cut below

    if hubs:  # foundational concepts (most sentences, most definitions that mention them) pair with everything
        indeg = Counter()
        for (x, y), v in defmention.items():
            indeg[x] += v
            indeg[y] += v
        freq = Counter()
        for (x, y), v in cooc.items():
            freq[x] += v
            freq[y] += v
        hub_ids = [cid for cid, _ in sorted(((c.concept_id, freq[c.concept_id] + 3 * indeg[c.concept_id]) for c in concepts),
                                            key=lambda t: -t[1])[:hubs]]
        for h in hub_ids:
            for c in concepts:
                if c.concept_id != h:
                    score[tuple(sorted((h, c.concept_id)))] += 0.5

    by_concept = defaultdict(list)
    for k, s in score.items():
        by_concept[k[0]].append((s, k))
        by_concept[k[1]].append((s, k))
    keep = set()
    for cid, lst in by_concept.items():
        for _, k in sorted(lst, reverse=True)[:per_concept]:
            keep.add(k)
    if hubs:
        keep |= {k for k in score if hub_set_has(k, hub_ids)}
    ranked = sorted(keep, key=lambda k: score[k], reverse=True)[:max_pairs]

    cands = []
    for a, b in ranked:
        ev = list(evidence.get((a, b), []))
        if not ev:
            ev = [x for x in (normalizer.concepts_by_id[a].definition, normalizer.concepts_by_id[b].definition) if x]
        cands.append({"a": a, "b": b, "score": score[(a, b)], "cooc": cooc.get((a, b), 0), "evidence": ev})
    return cands
