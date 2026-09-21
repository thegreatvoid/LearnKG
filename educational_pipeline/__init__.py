"""
Educational Dataset Construction Pipeline Package
"""

from .pipeline import run_educational_pipeline
from .parser import parse_document, ParsedBlock
from .structure_detector import detect_educational_structures, StructuredBlock
from .chunker import create_structure_aware_chunks, EducationalChunk
from .normalizer import ConceptNormalizer, NormalizedConcept
from .relation_extractor import RelationManager, ExtractedRelation, VALID_ONTOLOGY_TYPES
from .dataset_builder import build_and_save_dataset, CONCEPTS_COLUMNS, RELATIONS_COLUMNS
from .graph_stats import compute_graph_statistics
from .graph_builder import build_educational_graph

__all__ = [
    "run_educational_pipeline",
    "parse_document",
    "ParsedBlock",
    "detect_educational_structures",
    "StructuredBlock",
    "create_structure_aware_chunks",
    "EducationalChunk",
    "ConceptNormalizer",
    "NormalizedConcept",
    "RelationManager",
    "ExtractedRelation",
    "VALID_ONTOLOGY_TYPES",
    "build_and_save_dataset",
    "CONCEPTS_COLUMNS",
    "RELATIONS_COLUMNS",
    "compute_graph_statistics",
    "build_educational_graph",
]
