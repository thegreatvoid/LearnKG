import uuid
import pandas as pd
import numpy as np
from .prompts import extractConcepts
from .prompts import graphPrompt


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
