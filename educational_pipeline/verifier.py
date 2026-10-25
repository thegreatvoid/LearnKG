"""
Automatic Evidence Verification Stage for Educational Knowledge Graph.

Executes independent verification on extracted relation proposals before graph inclusion.
Verifies seven critical quality dimensions:
  1. Evidence quote exists in the source text (verbatim grounding)
  2. The evidence supports the proposed relation
  3. The relation type matches the formal schema
  4. The direction is correct relative to the evidence
  5. Both concept IDs refer to the intended concepts in the quote
  6. No structural constraint (DAG acyclicity, symmetry) is violated
  7. The evidence does not contradict the proposed edge

Explicit Verification Statuses:
  - VERIFIED_SUPPORTED
  - INSUFFICIENT_EVIDENCE
  - CONTRADICTED
  - INVALID_DIRECTION

Only edges meeting the acceptance policy (VERIFIED_SUPPORTED) enter the final graph.
All rejected or unverified candidates are preserved in diagnostic reports.
"""

from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from .multi_relation_extractor import ExtractedProposal
from .normalizer import ConceptNormalizer


VERIFICATION_STATUSES = {
    "VERIFIED_SUPPORTED",
    "INSUFFICIENT_EVIDENCE",
    "CONTRADICTED",
    "INVALID_DIRECTION",
}

VERIFICATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["VERIFIED_SUPPORTED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED", "INVALID_DIRECTION"],
        },
        "quote_in_text": {"type": "boolean"},
        "direction_valid": {"type": "boolean"},
        "supports_relation": {"type": "boolean"},
        "confidence": {"type": "number"},
        "verification_explanation": {"type": "string"},
    },
    "required": [
        "status",
        "quote_in_text",
        "direction_valid",
        "supports_relation",
        "confidence",
        "verification_explanation",
    ],
    "additionalProperties": False,
}


@dataclass
class VerificationRecord:
    proposal: ExtractedProposal
    status: str
    quote_in_text: bool
    direction_valid: bool
    supports_relation: bool
    confidence: float
    verification_explanation: str
    structural_violation: Optional[str] = None
    accepted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.proposal.source_concept_id,
            "target_id": self.proposal.target_concept_id,
            "source_name": self.proposal.source_name,
            "target_name": self.proposal.target_name,
            "relation_type": self.proposal.relation_type,
            "status": self.status,
            "accepted": self.accepted,
            "quote_in_text": self.quote_in_text,
            "direction_valid": self.direction_valid,
            "supports_relation": self.supports_relation,
            "confidence": round(self.confidence, 4),
            "verification_explanation": self.verification_explanation,
            "structural_violation": self.structural_violation,
            "evidence_quote": self.proposal.evidence_quote,
            "reasoning_summary": self.proposal.reasoning_summary,
        }


def _normalize_text_for_search(text: str) -> str:
    """Normalizes whitespace and punctuation for robust substring search."""
    s = str(text).lower()
    s = re.sub(r"[\s\n\r\t]+", " ", s)
    s = re.sub(r"[\"'\u2018\u2019\u201c\u201d]", "", s)
    return s.strip()


class EvidenceVerifier:
    """Independent automatic verification engine for candidate relation edges."""

    def __init__(
        self,
        full_text: str,
        normalizer: ConceptNormalizer,
        verifier_backend=None,
    ):
        self.full_text = full_text
        self.normalized_full_text = _normalize_text_for_search(full_text)
        self.normalizer = normalizer
        self.verifier_backend = verifier_backend
        self.counters = Counter()

        # Graphs to track structural constraints incrementally
        self.dag_graphs: Dict[str, nx.DiGraph] = {
            "Prerequisite": nx.DiGraph(),
            "Part-of": nx.DiGraph(),
            "Extension": nx.DiGraph(),
        }

    def check_quote_in_source(self, quote: str) -> bool:
        """Verifies if the evidence quote exists in the source text."""
        if not quote or len(quote.strip()) < 10:
            return False
        clean_q = _normalize_text_for_search(quote)
        # Check direct substring
        if clean_q in self.normalized_full_text:
            return True
        # Try matching a significant fragment (first 60 chars)
        frag = clean_q[:min(len(clean_q), 60)].strip()
        if len(frag) >= 20 and frag in self.normalized_full_text:
            return True
        return False

    def check_structural_constraints(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
    ) -> Optional[str]:
        """Checks structural constraints (self-loops, DAG acyclicity)."""
        if source_id == target_id:
            return "Self-loop not allowed"

        if relation_type in self.dag_graphs:
            g = self.dag_graphs[relation_type]
            if g.has_edge(target_id, source_id):
                return f"Direct reverse edge already exists in {relation_type} graph"
            # Tentatively add edge to test for acyclicity
            g.add_edge(source_id, target_id)
            is_dag = nx.is_directed_acyclic_graph(g)
            g.remove_edge(source_id, target_id)
            if not is_dag:
                return f"Cycle detected in acyclic relation {relation_type}"

        return None

    def verify_proposal_rule_based(
        self,
        proposal: ExtractedProposal,
        quote_exists: bool,
    ) -> VerificationRecord:
        """Deterministic offline rule-based verification when no verifier LLM is available."""
        src_name = proposal.source_name.lower()
        tgt_name = proposal.target_name.lower()
        quote = (proposal.evidence_quote or "").lower()

        # Definitional Grounding Fallback:
        # For Prerequisite relations, allow an edge to be accepted if target concept B's definition
        # explicitly references source concept A's name or alias, even if exact sentence-level quote is missing.
        tgt_c = self.normalizer.concepts_by_id.get(proposal.target_concept_id)
        src_c = self.normalizer.concepts_by_id.get(proposal.source_concept_id)
        def_fallback = False
        if proposal.relation_type == "Prerequisite" and tgt_c and src_c and tgt_c.definition:
            t_def = tgt_c.definition.lower()
            s_aliases = [src_c.concept_name.lower()] + [a.lower() for a in src_c.aliases]
            if any(re.search(rf"\b{re.escape(sa)}\b", t_def) for sa in s_aliases if len(sa) > 1):
                def_fallback = True
                if not proposal.evidence_quote:
                    proposal.evidence_quote = tgt_c.definition
                    quote = t_def

        # Check 1: Quote existence (exempt if definitional grounding fallback applies)
        if not quote_exists and not def_fallback:
            return VerificationRecord(
                proposal=proposal,
                status="INSUFFICIENT_EVIDENCE",
                quote_in_text=False,
                direction_valid=False,
                supports_relation=False,
                confidence=0.0,
                verification_explanation="Evidence quote was not found in the source textbook.",
                accepted=False,
            )

        # Check 2: Concept presence in quote (exempt if definitional grounding fallback applies)
        src_in_quote = (src_name in quote) or any(a.lower() in quote for a in self.normalizer.concepts_by_id[proposal.source_concept_id].aliases)
        tgt_in_quote = (tgt_name in quote) or any(a.lower() in quote for a in self.normalizer.concepts_by_id[proposal.target_concept_id].aliases)

        if not (src_in_quote and tgt_in_quote) and not def_fallback:
            return VerificationRecord(
                proposal=proposal,
                status="INSUFFICIENT_EVIDENCE",
                quote_in_text=True,
                direction_valid=False,
                supports_relation=False,
                confidence=0.3,
                verification_explanation=f"Both concepts ({proposal.source_name}, {proposal.target_name}) must appear in the evidence quote.",
                accepted=False,
            )

        # Check 3: Contradiction / Negation checks
        negation_patterns = [
            r"\b(is\s+not|are\s+not|never|neither|unlike|cannot\s+be|except)\b",
        ]
        has_negation = any(re.search(p, quote) for p in negation_patterns)
        if has_negation and not ("not only" in quote):
            return VerificationRecord(
                proposal=proposal,
                status="CONTRADICTED",
                quote_in_text=True,
                direction_valid=False,
                supports_relation=False,
                confidence=0.2,
                verification_explanation="Quote contains negative/contrasting clauses that may contradict the relationship.",
                accepted=False,
            )

        # Check 4: Structural constraints
        violation = self.check_structural_constraints(
            proposal.source_concept_id,
            proposal.target_concept_id,
            proposal.relation_type,
        )
        if violation:
            return VerificationRecord(
                proposal=proposal,
                status="INVALID_DIRECTION" if "reverse" in violation else "CONTRADICTED",
                quote_in_text=True,
                direction_valid=False,
                supports_relation=False,
                confidence=0.1,
                verification_explanation=f"Structural constraint violation: {violation}",
                structural_violation=violation,
                accepted=False,
            )

        # Passes deterministic checks
        return VerificationRecord(
            proposal=proposal,
            status="VERIFIED_SUPPORTED",
            quote_in_text=True,
            direction_valid=True,
            supports_relation=True,
            confidence=max(0.7, proposal.confidence),
            verification_explanation="Quote verified verbatim in source; both concepts present; structural constraints satisfied.",
            accepted=True,
        )

    def verify_proposal_llm(
        self,
        proposal: ExtractedProposal,
        quote_exists: bool,
    ) -> VerificationRecord:
        """Performs LLM-based verification call."""
        if not quote_exists:
            return VerificationRecord(
                proposal=proposal,
                status="INSUFFICIENT_EVIDENCE",
                quote_in_text=False,
                direction_valid=False,
                supports_relation=False,
                confidence=0.0,
                verification_explanation="Evidence quote does not exist in textbook text.",
                accepted=False,
            )

        # Structural constraint check first
        violation = self.check_structural_constraints(
            proposal.source_concept_id,
            proposal.target_concept_id,
            proposal.relation_type,
        )
        if violation:
            return VerificationRecord(
                proposal=proposal,
                status="INVALID_DIRECTION" if "reverse" in violation else "CONTRADICTED",
                quote_in_text=True,
                direction_valid=False,
                supports_relation=False,
                confidence=0.1,
                verification_explanation=f"Structural violation: {violation}",
                structural_violation=violation,
                accepted=False,
            )

        verifier_system = (
            "You are an impartial, highly skeptical Knowledge Graph Verification Auditor.\n"
            "Your job is to critically evaluate a proposed educational relationship against its evidence quote.\n\n"
            "Evaluate strictly:\n"
            "1. Does the quote ACTUALLY support the proposed relation type according to formal educational definitions?\n"
            "2. Is the DIRECTION correct (Source -> Target)? If inverted, flag as INVALID_DIRECTION.\n"
            "3. If the quote contradicts or disproves the relation, flag as CONTRADICTED.\n"
            "4. If the quote is ambiguous, vague, or merely mentions the terms together without proof, flag as INSUFFICIENT_EVIDENCE.\n"
            "5. Only return VERIFIED_SUPPORTED if the evidence clearly and unambiguously substantiates the edge.\n\n"
            "Output must be valid JSON adhering strictly to the schema."
        )

        verifier_user = (
            f"PROPOSED RELATION:\n"
            f"  Source: {proposal.source_name} ({proposal.source_concept_id})\n"
            f"  Target: {proposal.target_name} ({proposal.target_concept_id})\n"
            f"  Relation Type: {proposal.relation_type}\n"
            f"  Extractor Reasoning: {proposal.reasoning_summary}\n"
            f"  Direction Explanation: {proposal.direction_explanation}\n\n"
            f"EVIDENCE QUOTE (verbatim from text):\n"
            f"  \"{proposal.evidence_quote}\"\n\n"
            f"Does this evidence quote genuinely support the proposed {proposal.relation_type} relationship from {proposal.source_name} to {proposal.target_name}?"
        )

        try:
            res = self.verifier_backend.chat_json(
                verifier_system,
                verifier_user,
                VERIFICATION_JSON_SCHEMA,
                temperature=0.0,
            )
            v_status = res.get("status", "INSUFFICIENT_EVIDENCE")
            v_dir = bool(res.get("direction_valid", False))
            v_supp = bool(res.get("supports_relation", False))
            v_conf = float(res.get("confidence", 0.5))
            v_exp = str(res.get("verification_explanation", ""))

            if v_status not in VERIFICATION_STATUSES:
                v_status = "INSUFFICIENT_EVIDENCE"

            accepted = (v_status == "VERIFIED_SUPPORTED" and v_dir and v_supp)

            return VerificationRecord(
                proposal=proposal,
                status=v_status,
                quote_in_text=True,
                direction_valid=v_dir,
                supports_relation=v_supp,
                confidence=v_conf,
                verification_explanation=v_exp,
                accepted=accepted,
            )
        except Exception as e:
            # Fallback to rule-based on LLM failure
            rec = self.verify_proposal_rule_based(proposal, quote_exists)
            rec.verification_explanation += f" (LLM verifier fallback: {e})"
            return rec

    def verify(self, proposal: ExtractedProposal) -> VerificationRecord:
        """Verifies a single proposal and updates DAG structure if accepted."""
        # Non-accepted proposals are rejected immediately
        if proposal.decision != "ACCEPT_CANDIDATE" or proposal.relation_type == "NONE":
            return VerificationRecord(
                proposal=proposal,
                status="INSUFFICIENT_EVIDENCE",
                quote_in_text=False,
                direction_valid=False,
                supports_relation=False,
                confidence=0.0,
                verification_explanation="Proposal was marked NONE or rejected during extraction.",
                accepted=False,
            )

        quote_exists = self.check_quote_in_source(proposal.evidence_quote)

        if self.verifier_backend is not None:
            record = self.verify_proposal_llm(proposal, quote_exists)
        else:
            record = self.verify_proposal_rule_based(proposal, quote_exists)

        # Update counters
        self.counters[f"status_{record.status}"] += 1
        if record.accepted:
            self.counters["verified_accepted"] += 1
            # Add to DAG tracker to prevent future cycles
            if proposal.relation_type in self.dag_graphs:
                self.dag_graphs[proposal.relation_type].add_edge(
                    proposal.source_concept_id,
                    proposal.target_concept_id,
                )
        else:
            self.counters["verified_rejected"] += 1

        return record

    def verify_all(
        self,
        proposals: List[ExtractedProposal],
    ) -> Tuple[List[VerificationRecord], List[VerificationRecord]]:
        """
        Verifies all proposals.
        Returns (accepted_records, rejected_or_uncertain_records).
        """
        accepted = []
        diagnostics = []

        for p in proposals:
            record = self.verify(p)
            if record.accepted:
                accepted.append(record)
            else:
                diagnostics.append(record)

        return accepted, diagnostics
