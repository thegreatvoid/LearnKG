import uuid
import pandas as pd
import numpy as np
from .prompts import extractConcepts
from .prompts import graphPrompt

# ---------------------------------------------------------------------------
# AHP-Derived Edge Weight  (Saaty's Analytic Hierarchy Process)
# ---------------------------------------------------------------------------
# Pairwise comparison yielded CR ≈ 0.022 < 0.10 → consistent judgments.
#
#   Factor  Symbol  AHP weight  Source
#   ──────  ──────  ──────────  ──────────────────────────────────────────
#   Semantic Similarity   S    0.52    LLM-assigned weight (1-10, norm.)
#   Co-occurrence         C    0.24    chunk co-occurrence count (norm.)
#   Chapter Proximity     P    0.09    shared-chunk ratio proxy (0-1)
#   Educational Context   E    0.15    educational relationship keyword (0/1)
#
AHP_ALPHA = 0.52   # Semantic Similarity
AHP_BETA  = 0.24   # Co-occurrence
AHP_GAMMA = 0.09   # Chapter Proximity
AHP_DELTA = 0.15   # Educational Context

# Keywords that flag an educationally-meaningful relationship
_EDUCATIONAL_KEYWORDS = {
    "prerequisite", "explains", "defines", "enables",
    "introduces", "requires", "extends", "generalizes",
    "specializes", "applies", "illustrates", "teaches",
}


def ahp_edge_weight(
    llm_weight: float,
    cooccurrence_count: float,
    chunk_overlap_ratio: float,
    relationship: str,
) -> float:
    """
    Compute AHP-weighted edge score.

    Parameters
    ----------
    llm_weight         : LLM-assigned relation strength (1–10 scale).
    cooccurrence_count : Raw co-occurrence count between the two nodes.
    chunk_overlap_ratio: Fraction of shared chunks out of all chunks either
                         node appears in (proxy for Chapter Proximity).
                         Pass 0.0 when the edge has no proximity signal.
    relationship       : Relationship predicate string from the LLM.

    Returns
    -------
    float in [0, 1] — higher means a stronger / more trustworthy edge.
    """
    # S: normalise LLM weight from [1, 10] → [0, 1]
    S = float(np.clip((llm_weight - 1) / 9.0, 0.0, 1.0))

    # C: normalise co-occurrence count; cap at 5 to avoid outlier dominance
    C = float(np.clip(cooccurrence_count / 5.0, 0.0, 1.0))

    # P: chapter-proximity proxy already in [0, 1]
    P = float(np.clip(chunk_overlap_ratio, 0.0, 1.0))

    # E: binary flag — 1 if relationship mentions an educational concept
    rel_lower = str(relationship).lower()
    E = 1.0 if any(kw in rel_lower for kw in _EDUCATIONAL_KEYWORDS) else 0.0

    return AHP_ALPHA * S + AHP_BETA * C + AHP_GAMMA * P + AHP_DELTA * E


def documents2Dataframe(documents) -> pd.DataFrame:
    """Converts a list of LangChain document chunks into a DataFrame with chunk_ids."""
    rows = []
    for chunk in documents:
        row = {
            "text": chunk.page_content,
            **chunk.metadata,
            "chunk_id": uuid.uuid4().hex,
        }
        rows = rows + [row]

    df = pd.DataFrame(rows)
    return df


def df2ConceptsList(dataframe: pd.DataFrame) -> list:
    """Legacy NER-style concept extraction (kept for backwards compatibility)."""
    results = dataframe.apply(
        lambda row: extractConcepts(
            row.text, {"chunk_id": row.chunk_id, "type": "concept"}
        ),
        axis=1,
    )
    results = results.dropna()
    results = results.reset_index(drop=True)
    concept_list = np.concatenate(results).ravel().tolist()
    return concept_list


def concepts2Df(concepts_list) -> pd.DataFrame:
    """Legacy concept list → DataFrame (kept for backwards compatibility)."""
    concepts_dataframe = pd.DataFrame(concepts_list).replace(" ", np.nan)
    concepts_dataframe = concepts_dataframe.dropna(subset=["entity"])
    concepts_dataframe["entity"] = concepts_dataframe["entity"].apply(
        lambda x: x.lower()
    )
    return concepts_dataframe


def df2Graph(dataframe: pd.DataFrame, model=None) -> list:
    """
    For every text chunk, calls the LLM to extract directed, weighted relations.
    Returns a flat list of relation dicts:
        { source, target, relationship, weight, description, chunk_id }
    """
    results = dataframe.apply(
        lambda row: graphPrompt(row.text, {"chunk_id": row.chunk_id}, model), axis=1
    )
    # invalid json results in NaN — drop silently
    results = results.dropna()
    results = results.reset_index(drop=True)

    # Flatten list-of-lists into a single list
    concept_list = np.concatenate(results).ravel().tolist()
    return concept_list


def graph2Df(nodes_list) -> pd.DataFrame:
    """
    Converts the raw list of relation dicts (new schema) into a clean DataFrame.

    New schema columns:
        source      – origin/actor concept  (lowercased)
        target      – recipient/effect concept  (lowercased)
        relationship – directional predicate string
        weight      – integer 1-10 from LLM (cast to float for safety)
        description – one-sentence context string
        chunk_id    – originating chunk UUID

    Drops rows missing source, target, or relationship.
    """
    graph_dataframe = pd.DataFrame(nodes_list)

    # Guard: make sure the expected columns exist
    required_cols = {"source", "target", "relationship"}
    missing = required_cols - set(graph_dataframe.columns)
    if missing:
        raise ValueError(
            f"graph2Df: LLM output is missing expected columns: {missing}. "
            f"Got columns: {list(graph_dataframe.columns)}"
        )

    # Normalize: replace empty strings with NaN then drop incomplete rows
    graph_dataframe.replace("", np.nan, inplace=True)
    graph_dataframe.dropna(subset=["source", "target", "relationship"], inplace=True)

    # Lowercase & strip entity names so nodes merge correctly
    graph_dataframe["source"] = graph_dataframe["source"].apply(
        lambda x: str(x).strip().lower()
    )
    graph_dataframe["target"] = graph_dataframe["target"].apply(
        lambda x: str(x).strip().lower()
    )
    graph_dataframe["relationship"] = graph_dataframe["relationship"].apply(
        lambda x: str(x).strip().lower()
    )

    # Cast weight to numeric; default to 5 if missing or unparseable
    if "weight" in graph_dataframe.columns:
        graph_dataframe["weight"] = pd.to_numeric(
            graph_dataframe["weight"], errors="coerce"
        ).fillna(5).clip(1, 10)
    else:
        graph_dataframe["weight"] = 5.0

    # Ensure description column exists
    if "description" not in graph_dataframe.columns:
        graph_dataframe["description"] = ""

    return graph_dataframe.reset_index(drop=True)
