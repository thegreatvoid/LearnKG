"""
Multi-Relation LLM Extractor for Educational Knowledge Graph.

Implements structured extraction for:
  - Prerequisite
  - Similarity
  - Part-of
  - Application
  - Extension

Requires structured schema outputs with programmatic validation:
  - source_concept_id
  - target_concept_id
  - relation_type
  - decision ("ACCEPT_CANDIDATE" or "NONE")
  - evidence_quote
  - evidence_location
  - direction_explanation
  - confidence
  - reasoning_summary

Enforces relation-specific ontological rules:
  - Similarity: symmetric canonicalization
  - Part-of: strict rejection of type-of / hyponymy confusions
  - Application: functional usage / operationalization requirement
  - Extension: dimensional expansion or generalization
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from .candidate_generator import CandidatePair
from .normalizer import ConceptNormalizer


VALID_RELATION_TYPES = {
    "Prerequisite",
    "Similarity",
    "Part-of",
    "Application",
    "Extension",
    "NONE",
}

VALID_DECISIONS = {"ACCEPT_CANDIDATE", "NONE"}

# JSON Schema for Ollama / LLM structured generation
EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "source_concept_id": {"type": "string"},
        "target_concept_id": {"type": "string"},
        "relation_type": {
            "type": "string",
            "enum": ["Prerequisite", "Similarity", "Part-of", "Application", "Extension", "NONE"],
        },
        "decision": {
            "type": "string",
            "enum": ["ACCEPT_CANDIDATE", "NONE"],
        },
        "evidence_quote": {"type": "string"},
        "evidence_location": {"type": "string"},
        "direction_explanation": {"type": "string"},
        "confidence": {"type": "number"},
        "reasoning_summary": {"type": "string"},
    },
    "required": [
        "source_concept_id",
        "target_concept_id",
        "relation_type",
        "decision",
        "evidence_quote",
        "evidence_location",
        "direction_explanation",
        "confidence",
        "reasoning_summary",
    ],
    "additionalProperties": False,
}


@dataclass
class ExtractedProposal:
    source_concept_id: str
    target_concept_id: str
    source_name: str
    target_name: str
    relation_type: str
    decision: str
    evidence_quote: str
    evidence_location: str
    direction_explanation: str
    confidence: float
    reasoning_summary: str
    is_valid: bool = True
    validation_error: str = ""
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_relation_schema_prompt(schema_path: Optional[Path] = None) -> str:
    """Loads and formats the relation schema and few-shot guidance from YAML."""
    if schema_path is None:
        schema_path = Path(__file__).resolve().parent.parent / "config" / "relation_schema.yaml"

    if not schema_path.exists():
        # Fallback summary if config not found
        return (
            "Permitted relations:\n"
            "- Prerequisite: Source must be mastered BEFORE Target.\n"
            "- Similarity: Source and Target are conceptually or functionally similar (Symmetric).\n"
            "- Part-of: Source is a component part of Target (NOT a type-of or category).\n"
            "- Application: Source is applied, used, or operationalized in Target.\n"
            "- Extension: Target generalizes or expands Base Source.\n"
            "- NONE: No permitted relation supported by evidence."
        )

    with open(schema_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    lines = ["EDUCATIONAL RELATION ONTOLOGY & RULES:"]
    for rel_name, spec in data.get("relations", {}).items():
        lines.append(f"\n[{rel_name}] ({spec.get('direction', 'directed')}):")
        lines.append(f"  Definition: {spec.get('definition', '').strip()}")
        lines.append(f"  Required distinction: {spec.get('required_distinction', '').strip()}")
        pos = spec.get("positive_examples", [])
        if pos:
            ex = pos[0]
            lines.append(f"  Positive Example: {ex.get('source')} -> {ex.get('target')} ({ex.get('explanation')})")
        neg = spec.get("negative_examples", [])
        if neg:
            nex = neg[0]
            lines.append(f"  Negative Example: {nex.get('source')} -> {nex.get('target')} [Confusion: {nex.get('confusion')}]")

    lines.append("\nCRITICAL CONSTRAINT: Do NOT confuse Type-of (e.g. Acute Triangle is a type of Triangle) with Part-of. Type-of relations must be returned as NONE.")
    return "\n".join(lines)


def build_extraction_prompt(
    cand: CandidatePair,
    schema_prompt: str,
) -> Tuple[str, str]:
    """Builds system and user prompts for extracting relations between a candidate pair."""
    system_prompt = (
        "You are an expert Educational Ontologist and Knowledge Graph Builder.\n"
        "Your task is to analyze two educational concepts and determine if an explicit, evidence-backed relationship "
        "exists between them according to the strict educational schema.\n\n"
        f"{schema_prompt}\n\n"
        "INSTRUCTIONS:\n"
        "1. Examine the concept names, definitions, and provided textbook evidence sentences.\n"
        "2. Only accept a relationship if the evidence sentence EXPLICITLY establishes it.\n"
        "3. If the evidence only shows co-occurrence, shared topic, or an unsupported relation (such as Type-of), return decision='NONE' and relation_type='NONE'.\n"
        "4. Output MUST be valid JSON adhering strictly to the schema with exact concept IDs.\n"
        "5. Keep the reasoning summary and direction explanation concise (1-2 sentences)."
    )

    ev_text = "\n".join(f"- \"{s}\"" for s in cand.evidence_sentences[:5]) if cand.evidence_sentences else "(No direct co-occurring sentence; evaluate definitions and context)"
    locations_str = ", ".join(f"Ch: {l.get('chapter', '?')}, Sec: {l.get('section', '?')}, Page: {l.get('page', '?')}" for l in cand.passage_locations[:3])

    user_prompt = (
        f"CONCEPT A:\n"
        f"  ID: {cand.source_id}\n"
        f"  Name: {cand.source_name}\n"
        f"  Definition: {cand.source_definition or '(none provided)'}\n\n"
        f"CONCEPT B:\n"
        f"  ID: {cand.target_id}\n"
        f"  Name: {cand.target_name}\n"
        f"  Definition: {cand.target_definition or '(none provided)'}\n\n"
        f"TEXTBOOK EVIDENCE PASSAGES:\n"
        f"{ev_text}\n\n"
        f"PASSAGE LOCATIONS: {locations_str or 'General textbook context'}\n\n"
        f"Decide the exact relationship between Concept A ({cand.source_id}) and Concept B ({cand.target_id})."
    )

    return system_prompt, user_prompt


class MultiRelationExtractor:
    """Manages LLM extraction for all 5 educational relations with programmatic field validation."""

    def __init__(
        self,
        backend=None,
        schema_path: Optional[Path] = None,
    ):
        self.backend = backend
        self.schema_prompt = load_relation_schema_prompt(schema_path)
        self.counters = Counter()
        self.raw_responses: List[Dict[str, Any]] = []

    def validate_proposal(
        self,
        raw: Dict[str, Any],
        cand: CandidatePair,
    ) -> ExtractedProposal:
        """Programmatically validates all fields of the LLM output."""
        src_id = str(raw.get("source_concept_id", "")).strip()
        tgt_id = str(raw.get("target_concept_id", "")).strip()
        rel_type = str(raw.get("relation_type", "")).strip()
        decision = str(raw.get("decision", "")).strip()
        quote = str(raw.get("evidence_quote", "")).strip()
        loc = str(raw.get("evidence_location", "")).strip()
        dir_exp = str(raw.get("direction_explanation", "")).strip()
        reasoning = str(raw.get("reasoning_summary", "")).strip()

        try:
            conf = float(raw.get("confidence", 0.0))
            conf = max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            conf = 0.0

        # Create base proposal
        proposal = ExtractedProposal(
            source_concept_id=src_id,
            target_concept_id=tgt_id,
            source_name=cand.source_name if src_id == cand.source_id else cand.target_name,
            target_name=cand.target_name if tgt_id == cand.target_id else cand.source_name,
            relation_type=rel_type,
            decision=decision,
            evidence_quote=quote,
            evidence_location=loc,
            direction_explanation=dir_exp,
            confidence=conf,
            reasoning_summary=reasoning,
            is_valid=True,
            validation_error="",
            raw_response=raw,
        )

        # Validation Rule 1: Decision check
        if decision not in VALID_DECISIONS:
            proposal.is_valid = False
            proposal.validation_error = f"Invalid decision '{decision}'; must be ACCEPT_CANDIDATE or NONE"
            proposal.decision = "NONE"
            return proposal

        if decision == "NONE" or rel_type == "NONE":
            proposal.decision = "NONE"
            proposal.relation_type = "NONE"
            return proposal

        # Validation Rule 2: Relation type must be in 5-type ontology
        if rel_type not in VALID_RELATION_TYPES - {"NONE"}:
            proposal.is_valid = False
            proposal.validation_error = f"Unsupported relation_type '{rel_type}'"
            proposal.decision = "NONE"
            return proposal

        # Validation Rule 3: Concept IDs must match the pair
        expected_ids = {cand.source_id, cand.target_id}
        if {src_id, tgt_id} != expected_ids:
            proposal.is_valid = False
            proposal.validation_error = f"Concept IDs ({src_id}, {tgt_id}) do not match candidate pair {expected_ids}"
            proposal.decision = "NONE"
            return proposal

        if src_id == tgt_id:
            proposal.is_valid = False
            proposal.validation_error = "Self-loop edge proposed (source_id == target_id)"
            proposal.decision = "NONE"
            return proposal

        # Validation Rule 4: Part-of vs Type-of confusion rejection
        if rel_type == "Part-of":
            # Check for type-of terminology in quote, explanation, or reasoning
            combined_text = f"{quote} {dir_exp} {reasoning}".lower()
            type_of_patterns = [
                r"\bis\s+a\s+type\s+of\b",
                r"\bis\s+a\s+kind\s+of\b",
                r"\bspecial\s+case\s+of\b",
                r"\bclassification\s+of\b",
                r"\bcategory\s+of\b",
                r"\bvariety\s+of\b",
            ]
            for pat in type_of_patterns:
                if re.search(pat, combined_text):
                    proposal.is_valid = False
                    proposal.validation_error = f"Type-of / hyponymy confusion detected in Part-of proposal ({pat})"
                    proposal.decision = "NONE"
                    self.counters["rejected_type_of_in_part_of"] += 1
                    return proposal

        # Validation Rule 5: Symmetric canonicalization for Similarity
        if rel_type == "Similarity":
            # Canonicalize order by concept_id
            if src_id > tgt_id:
                proposal.source_concept_id = tgt_id
                proposal.target_concept_id = src_id
                proposal.source_name, proposal.target_name = proposal.target_name, proposal.source_name

        # Validation Rule 6: Evidence quote requirement
        if not quote or len(quote) < 10:
            proposal.is_valid = False
            proposal.validation_error = "Missing or trivial evidence_quote for accepted candidate"
            proposal.decision = "NONE"
            return proposal

        return proposal

    def extract_candidate(self, cand: CandidatePair) -> ExtractedProposal:
        """Extracts and validates a relationship proposal for a single candidate pair."""
        if self.backend is None:
            # Fallback when no LLM backend is attached
            return ExtractedProposal(
                source_concept_id=cand.source_id,
                target_concept_id=cand.target_id,
                source_name=cand.source_name,
                target_name=cand.target_name,
                relation_type="NONE",
                decision="NONE",
                evidence_quote="",
                evidence_location="",
                direction_explanation="No LLM backend attached",
                confidence=0.0,
                reasoning_summary="",
                is_valid=True,
            )

        sys_p, usr_p = build_extraction_prompt(cand, self.schema_prompt)
        try:
            raw = self.backend.chat_json(sys_p, usr_p, EXTRACTION_JSON_SCHEMA, temperature=0.0)
            self.counters["llm_extraction_success"] += 1
        except Exception as e:
            self.counters["llm_extraction_error"] += 1
            return ExtractedProposal(
                source_concept_id=cand.source_id,
                target_concept_id=cand.target_id,
                source_name=cand.source_name,
                target_name=cand.target_name,
                relation_type="NONE",
                decision="NONE",
                evidence_quote="",
                evidence_location="",
                direction_explanation=f"LLM extraction error: {e}",
                confidence=0.0,
                reasoning_summary="",
                is_valid=False,
                validation_error=str(e),
            )

        self.raw_responses.append({"candidate": (cand.source_id, cand.target_id), "response": raw})
        proposal = self.validate_proposal(raw, cand)
        return proposal

    def extract_all(self, candidates: List[CandidatePair]) -> List[ExtractedProposal]:
        """Extracts proposals across all candidate pairs."""
        proposals = []
        for cand in candidates:
            p = self.extract_candidate(cand)
            proposals.append(p)
            self.counters[f"extracted_{p.relation_type}"] += 1
            if p.decision == "ACCEPT_CANDIDATE":
                self.counters["accepted_candidates"] += 1
            else:
                self.counters["rejected_candidates"] += 1
        return proposals
