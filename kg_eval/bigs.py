"""BIGS (Bidirectional Graph Similarity), Lermanda, Ojeda & Reutter, "Evaluating Knowledge Graph Construction
from Text Without Supervision" (ESWC 2026). Definitions follow the paper, section 2.1:

  BIGS->  = 1/n sum_i min_j d(D_i, Vrb(t_j))    document units covered by the graph   (lower is better)
  BIGS<-  = 1/m sum_j min_i d(D_i, Vrb(t_j))    graph triples grounded in the text    (lower is better)
  Sym-BIGS = 1 - 2(1-BIGS->)(1-BIGS<-) / ((1-BIGS->)+(1-BIGS<-))

d is cosine distance between sentence embeddings; Vrb concatenates "subject predicate object" (the paper's
default); document units are sentences. Per-triple BIGS<- distances are also returned for edge-level analysis.
Embedder defaults to the locally cached all-MiniLM-L6-v2 (paper reports stability across sentence embedders;
pass e.g. all-MiniLM-L12-v2 or BAAI/bge-m3 to match its experiments).
"""

from typing import Dict, List, Sequence

import numpy as np

DEFAULT_EMBEDDER = "sentence-transformers/all-MiniLM-L6-v2"


def verbalize_triple(subject: str, predicate: str, obj: str) -> str:
    return f"{subject} {predicate} {obj}"


def load_embedder(embedder: str = DEFAULT_EMBEDDER):
    """sentence-transformers is a required dependency of BIGS (listed in requirements.txt); fail loudly if missing."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError("BIGS needs sentence-transformers: pip install sentence-transformers "
                          "(then the embedder is downloaded once from Hugging Face)") from exc
    return SentenceTransformer(embedder)


def bigs(doc_units: Sequence[str], triple_texts: Sequence[str], embedder: str = DEFAULT_EMBEDDER, model=None) -> Dict:
    """Equations (1)-(3) of Lermanda et al. (checked against the paper's section 2.1)."""
    model = model or load_embedder(embedder)
    D = model.encode(list(doc_units), normalize_embeddings=True)
    V = model.encode(list(triple_texts), normalize_embeddings=True)
    dist = 1.0 - D @ V.T  # n_docs x m_triples cosine distance
    to_graph = dist.min(axis=1)    # per document unit
    from_graph = dist.min(axis=0)  # per triple
    fwd, bwd = float(to_graph.mean()), float(from_graph.mean())
    a, b = 1 - fwd, 1 - bwd
    sym = 1 - (2 * a * b / (a + b)) if (a + b) else 1.0
    return {
        "bigs_to_graph": fwd, "bigs_from_graph": bwd, "sym_bigs": float(sym),
        "embedder": embedder, "n_doc_units": len(doc_units), "n_triples": len(triple_texts),
        "per_triple_distance": from_graph.tolist(), "per_doc_unit_distance": to_graph.tolist(),
    }
