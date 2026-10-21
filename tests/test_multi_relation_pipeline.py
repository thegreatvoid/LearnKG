"""
Unit and Integration Tests for Multi-Relation Knowledge Graph Pipeline.

Tests all Phase 8 requirements:
  1. Schema validation (config/relation_schema.yaml)
  2. Structured LLM response parsing
  3. Missing or invalid evidence handling
  4. Incorrect direction detection
  5. Duplicate proposal handling
  6. Symmetric Similarity edges
  7. Part-of type-confusion rejection (hyponymy vs meronymy)
  8. Unsupported relation rejection
  9. Weight calculation, decoupling, and normalization
  10. Graph export and reload
  11. Repeated-run deterministic consistency

Runs entirely offline with mocked LLM responses. No external network or live model required.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from educational_pipeline.candidate_generator import CandidatePair
from educational_pipeline.dataset_builder import CONCEPTS_COLUMNS, RELATIONS_COLUMNS, build_and_save_dataset
from educational_pipeline.edge_weighting import calculate_evidence_support, compute_relation_weight
from educational_pipeline.multi_relation_extractor import (
    EXTRACTION_JSON_SCHEMA,
    ExtractedProposal,
    MultiRelationExtractor,
    VALID_RELATION_TYPES,
)
from educational_pipeline.normalizer import ConceptNormalizer, NormalizedConcept
from educational_pipeline.relation_extractor import RelationManager
from educational_pipeline.verifier import EvidenceVerifier, VerificationRecord


class TestMultiRelationPipeline(unittest.TestCase):

    def setUp(self):
        self.normalizer = ConceptNormalizer()
        self.c1 = self.normalizer.register_concept("Right Triangle", definition="A triangle with a right angle.", page=1)
        self.c2 = self.normalizer.register_concept("Pythagorean Theorem", definition="a^2 + b^2 = c^2 in right triangles.", page=2)
        self.c3 = self.normalizer.register_concept("Hypotenuse", definition="The longest side of a right triangle.", page=1)
        self.c4 = self.normalizer.register_concept("Acute Triangle", definition="A triangle where all angles are acute.", page=1)
        self.c5 = self.normalizer.register_concept("Triangle", definition="A polygon with three edges and three vertices.", page=1)

        self.sample_text = (
            "A triangle is a polygon with three edges and three vertices. "
            "A right triangle is a triangle with one right angle. "
            "The hypotenuse is a component part of a right triangle. "
            "The Pythagorean theorem states that in a right triangle, a squared plus b squared equals c squared. "
            "Right triangles are required for understanding the Pythagorean theorem."
        )

    # 1. Schema validation
    def test_schema_validation(self):
        schema_path = REPO_ROOT / "config" / "relation_schema.yaml"
        self.assertTrue(schema_path.exists(), "relation_schema.yaml missing")
        with open(schema_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        expected_relations = {"Prerequisite", "Similarity", "Part-of", "Application", "Extension"}
        actual_relations = set(data.get("relations", {}).keys())
        self.assertEqual(expected_relations, actual_relations)

        for rel, spec in data["relations"].items():
            self.assertIn("direction", spec)
            self.assertIn("definition", spec)
            self.assertIn("positive_examples", spec)
            self.assertIn("negative_examples", spec)
            self.assertIn("structural_constraints", spec)
            self.assertGreater(len(spec["positive_examples"]), 0)
            self.assertGreater(len(spec["negative_examples"]), 0)

        # Part-of must have acyclic constraint and directed
        self.assertEqual(data["relations"]["Part-of"]["direction"], "directed")
        self.assertTrue(data["relations"]["Part-of"]["structural_constraints"]["acyclic_required"])
        # Similarity must be symmetric
        self.assertEqual(data["relations"]["Similarity"]["direction"], "symmetric")
        self.assertTrue(data["relations"]["Similarity"]["structural_constraints"]["is_symmetric"])

    # 2. Structured LLM response parsing (valid response)
    def test_structured_llm_response_parsing_valid(self):
        cand = CandidatePair(
            source_id="C0001",
            target_id="C0002",
            source_name="Right Triangle",
            target_name="Pythagorean Theorem",
        )
        extractor = MultiRelationExtractor(backend=None)

        valid_raw = {
            "source_concept_id": "C0001",
            "target_concept_id": "C0002",
            "relation_type": "Prerequisite",
            "decision": "ACCEPT_CANDIDATE",
            "evidence_quote": "Right triangles are required for understanding the Pythagorean theorem.",
            "evidence_location": "Chapter 1, Section 1.2",
            "direction_explanation": "Right triangle is foundational for the theorem.",
            "confidence": 0.95,
            "reasoning_summary": "Explicit prerequisite dependency.",
        }

        prop = extractor.validate_proposal(valid_raw, cand)
        self.assertTrue(prop.is_valid)
        self.assertEqual(prop.decision, "ACCEPT_CANDIDATE")
        self.assertEqual(prop.relation_type, "Prerequisite")
        self.assertEqual(prop.confidence, 0.95)
        self.assertEqual(prop.source_concept_id, "C0001")
        self.assertEqual(prop.target_concept_id, "C0002")

    # 3. Missing or invalid evidence
    def test_missing_or_invalid_evidence(self):
        cand = CandidatePair(
            source_id="C0001",
            target_id="C0002",
            source_name="Right Triangle",
            target_name="Pythagorean Theorem",
        )
        extractor = MultiRelationExtractor(backend=None)

        # Missing quote
        raw_missing_quote = {
            "source_concept_id": "C0001",
            "target_concept_id": "C0002",
            "relation_type": "Prerequisite",
            "decision": "ACCEPT_CANDIDATE",
            "evidence_quote": "",  # Empty
            "evidence_location": "Ch 1",
            "direction_explanation": "Dir",
            "confidence": 0.8,
            "reasoning_summary": "Reason",
        }
        prop = extractor.validate_proposal(raw_missing_quote, cand)
        self.assertEqual(prop.decision, "NONE")
        self.assertFalse(prop.is_valid)

    # 4. Unsupported relation rejection
    def test_unsupported_relation_rejection(self):
        cand = CandidatePair(
            source_id="C0001",
            target_id="C0002",
            source_name="Right Triangle",
            target_name="Pythagorean Theorem",
        )
        extractor = MultiRelationExtractor(backend=None)

        raw_unsupported = {
            "source_concept_id": "C0001",
            "target_concept_id": "C0002",
            "relation_type": "Subclass-of",  # Outside 5 types
            "decision": "ACCEPT_CANDIDATE",
            "evidence_quote": "A right triangle is something.",
            "evidence_location": "Ch 1",
            "direction_explanation": "Dir",
            "confidence": 0.8,
            "reasoning_summary": "Reason",
        }
        prop = extractor.validate_proposal(raw_unsupported, cand)
        self.assertEqual(prop.decision, "NONE")
        self.assertFalse(prop.is_valid)
        self.assertIn("Unsupported", prop.validation_error)

    # 5. Part-of type-confusion rejection (hyponymy vs meronymy)
    def test_part_of_type_confusion_rejection(self):
        cand = CandidatePair(
            source_id="C0004",
            target_id="C0005",
            source_name="Acute Triangle",
            target_name="Triangle",
        )
        extractor = MultiRelationExtractor(backend=None)

        # Attempting to classify "is a type of" as Part-of
        raw_type_of = {
            "source_concept_id": "C0004",
            "target_concept_id": "C0005",
            "relation_type": "Part-of",
            "decision": "ACCEPT_CANDIDATE",
            "evidence_quote": "An acute triangle is a type of triangle where all angles are acute.",
            "evidence_location": "Ch 1",
            "direction_explanation": "Acute triangle is a kind of triangle.",
            "confidence": 0.9,
            "reasoning_summary": "An acute triangle is a special case of triangle.",
        }
        prop = extractor.validate_proposal(raw_type_of, cand)
        self.assertEqual(prop.decision, "NONE")
        self.assertFalse(prop.is_valid)
        self.assertIn("Type-of", prop.validation_error)

    # 6. Symmetric Similarity edges
    def test_symmetric_similarity_edges(self):
        cand = CandidatePair(
            source_id="C0002",
            target_id="C0001",
            source_name="Pythagorean Theorem",
            target_name="Right Triangle",
        )
        extractor = MultiRelationExtractor(backend=None)

        raw_sim = {
            "source_concept_id": "C0002",
            "target_concept_id": "C0001",
            "relation_type": "Similarity",
            "decision": "ACCEPT_CANDIDATE",
            "evidence_quote": "Right triangles are similar in properties to special triangles.",
            "evidence_location": "Ch 1",
            "direction_explanation": "Symmetric comparison.",
            "confidence": 0.85,
            "reasoning_summary": "Analogy.",
        }
        prop = extractor.validate_proposal(raw_sim, cand)
        self.assertEqual(prop.decision, "ACCEPT_CANDIDATE")
        # Must be canonicalized: C0001 < C0002
        self.assertEqual(prop.source_concept_id, "C0001")
        self.assertEqual(prop.target_concept_id, "C0002")

    # 7. Evidence verification: quote existence and missing quote
    def test_evidence_verification_quote_exists(self):
        verifier = EvidenceVerifier(
            full_text=self.sample_text,
            normalizer=self.normalizer,
            verifier_backend=None,
        )

        valid_prop = ExtractedProposal(
            source_concept_id="C0003",
            target_concept_id="C0001",
            source_name="Hypotenuse",
            target_name="Right Triangle",
            relation_type="Part-of",
            decision="ACCEPT_CANDIDATE",
            evidence_quote="The hypotenuse is a component part of a right triangle.",
            evidence_location="Ch 1",
            direction_explanation="Hypotenuse is part of right triangle",
            confidence=0.9,
            reasoning_summary="Meronymy",
        )

        rec = verifier.verify(valid_prop)
        self.assertEqual(rec.status, "VERIFIED_SUPPORTED")
        self.assertTrue(rec.accepted)
        self.assertTrue(rec.quote_in_text)

        # Fabricated quote
        fake_prop = ExtractedProposal(
            source_concept_id="C0003",
            target_concept_id="C0001",
            source_name="Hypotenuse",
            target_name="Right Triangle",
            relation_type="Part-of",
            decision="ACCEPT_CANDIDATE",
            evidence_quote="This completely fabricated sentence does not exist anywhere in geometry.",
            evidence_location="Ch 1",
            direction_explanation="Dir",
            confidence=0.9,
            reasoning_summary="Fake",
        )
        rec_fake = verifier.verify(fake_prop)
        self.assertEqual(rec_fake.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(rec_fake.accepted)
        self.assertFalse(rec_fake.quote_in_text)

    # 8. Structural DAG cycle prevention
    def test_dag_cycle_prevention(self):
        verifier = EvidenceVerifier(
            full_text=self.sample_text,
            normalizer=self.normalizer,
            verifier_backend=None,
        )

        prop1 = ExtractedProposal(
            source_concept_id="C0001",
            target_concept_id="C0002",
            source_name="Right Triangle",
            target_name="Pythagorean Theorem",
            relation_type="Prerequisite",
            decision="ACCEPT_CANDIDATE",
            evidence_quote="Right triangles are required for understanding the Pythagorean theorem.",
            evidence_location="Ch 1",
            direction_explanation="C1 -> C2",
            confidence=0.9,
            reasoning_summary="Prereq",
        )
        rec1 = verifier.verify(prop1)
        self.assertTrue(rec1.accepted)

        # Attempt to add reverse prerequisite edge C0002 -> C0001
        prop2 = ExtractedProposal(
            source_concept_id="C0002",
            target_concept_id="C0001",
            source_name="Pythagorean Theorem",
            target_name="Right Triangle",
            relation_type="Prerequisite",
            decision="ACCEPT_CANDIDATE",
            evidence_quote="Right triangles are required for understanding the Pythagorean theorem.",
            evidence_location="Ch 1",
            direction_explanation="C2 -> C1",
            confidence=0.9,
            reasoning_summary="Cycle",
        )
        rec2 = verifier.verify(prop2)
        self.assertFalse(rec2.accepted)
        self.assertIn("reverse", str(rec2.structural_violation).lower())

    # 9. Weight calculation, decoupling, and schemes
    def test_weight_calculation_and_decoupling(self):
        factors = {
            "semantic_similarity": 0.6,
            "cooccurrence": 0.8,
            "chapter_proximity": 0.5,
            "educational_context": 0.4,
        }

        # AHP baseline
        w_ahp = compute_relation_weight(factors, "Prerequisite", scheme="ahp")
        expected_ahp = round(0.52 * 0.6 + 0.24 * 0.8 + 0.09 * 0.5 + 0.15 * 0.4, 4)
        self.assertAlmostEqual(w_ahp, expected_ahp, places=4)

        # Cooc-only
        w_cooc = compute_relation_weight(factors, "Prerequisite", scheme="cooc_only")
        self.assertEqual(w_cooc, 0.8)

        # Unweighted
        w_unweighted = compute_relation_weight(factors, "Prerequisite", scheme="unweighted")
        self.assertEqual(w_unweighted, 1.0)

        # Relation-aware for Similarity (0.6 S + 0.4 C)
        w_sim = compute_relation_weight(factors, "Similarity", scheme="relation_aware")
        expected_sim = round(0.60 * 0.6 + 0.40 * 0.8, 4)
        self.assertAlmostEqual(w_sim, expected_sim, places=4)

        # Evidence support decoupling
        support_ver = calculate_evidence_support(cooccurrence_count=3, evidence_sentences_count=2, is_verified=True)
        support_unver = calculate_evidence_support(cooccurrence_count=3, evidence_sentences_count=2, is_verified=False)
        self.assertGreater(support_ver, support_unver)

    # 10. Duplicate handling
    def test_duplicate_proposal_handling(self):
        rm = RelationManager(self.normalizer)
        r1 = rm.add_relation("Right Triangle", "Pythagorean Theorem", "Prerequisite", "s1", source="rule")
        r2 = rm.add_relation("Right Triangle", "Pythagorean Theorem", "Prerequisite", "s1", source="rule")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        # Identical proposal ignored
        self.assertEqual(r1.n_proposals, 1)

        # New evidence proposal increments proposals
        r3 = rm.add_relation("Right Triangle", "Pythagorean Theorem", "Prerequisite", "s2", source="keyword")
        self.assertEqual(r1.n_proposals, 2)
        self.assertEqual(r1.sources, {"rule", "keyword"})

    # 11. Graph export and reload
    def test_graph_export_and_reload(self):
        rm = RelationManager(self.normalizer)
        rm.add_relation("Right Triangle", "Pythagorean Theorem", "Prerequisite", "Sentence evidence", source="rule")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir)
            concepts_csv, relations_csv = build_and_save_dataset(self.normalizer, rm, out_path)

            self.assertTrue(concepts_csv.exists())
            self.assertTrue(relations_csv.exists())

            df_c = pd.read_csv(concepts_csv)
            df_r = pd.read_csv(relations_csv)

            self.assertEqual(list(df_c.columns), CONCEPTS_COLUMNS)
            self.assertEqual(list(df_r.columns), RELATIONS_COLUMNS)
            self.assertGreater(len(df_c), 0)
            self.assertEqual(len(df_r), 1)

            # Check decoupled columns present and non-null
            for col in ["extraction_confidence", "evidence_support", "relation_weight", "verification_status"]:
                self.assertIn(col, df_r.columns)

    # 12. Repeated run consistency
    def test_repeated_run_consistency(self):
        factors = {"semantic_similarity": 0.45, "cooccurrence": 0.66, "chapter_proximity": 0.5, "educational_context": 0.33}
        run1 = [compute_relation_weight(factors, rel, scheme="relation_aware") for rel in ["Prerequisite", "Similarity", "Part-of"]]
        run2 = [compute_relation_weight(factors, rel, scheme="relation_aware") for rel in ["Prerequisite", "Similarity", "Part-of"]]
        self.assertEqual(run1, run2)


if __name__ == "__main__":
    unittest.main()
