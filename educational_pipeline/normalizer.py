"""
Step 5: Concept Normalization and Entity Linking
Merges equivalent expressions and assigns one canonical concept name
and a unique concept ID (e.g. C0001, C0002).
Tracks aliases and merges occurrences across the entire corpus.
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class NormalizedConcept:
    concept_id: str
    concept_name: str
    aliases: Set[str] = field(default_factory=set)
    concept_type: str = "Component"
    definition: str = ""
    chapter: str = ""
    section: str = ""
    page: int = 1
    chunk_id: str = ""
    evidence: str = ""


class ConceptNormalizer:
    """
    Maintains a global registry of canonical concepts, matching acronyms,
    casing, plurals, and string similarity.
    """

    def __init__(self):
        self.concepts_by_id: Dict[str, NormalizedConcept] = {}
        # Mapping from lowercase alias/name -> concept_id
        self.lookup: Dict[str, str] = {}
        self._next_id = 1

    def _generate_id(self) -> str:
        cid = f"C{self._next_id:04d}"
        self._next_id += 1
        return cid

    @staticmethod
    def clean_name(name: str) -> str:
        """Cleans and standardizes concept name string."""
        s = str(name).strip()
        # Remove trailing punctuation
        s = re.sub(r"[\.,;:!]+$", "", s).strip()
        # Remove leading articles
        s = re.sub(r"^(?:the|a|an)\s+", "", s, flags=re.IGNORECASE).strip()
        return s

    @staticmethod
    def _is_plural_match(s1: str, s2: str) -> bool:
        """Checks if s1 and s2 are singular/plural of each other."""
        if s1 + "s" == s2 or s2 + "s" == s1:
            return True
        if s1 + "es" == s2 or s2 + "es" == s1:
            return True
        if s1.endswith("ies") and s1[:-3] + "y" == s2:
            return True
        if s2.endswith("ies") and s2[:-3] + "y" == s1:
            return True
        return False

    @staticmethod
    def _is_acronym_match(short_name: str, long_name: str) -> bool:
        """Checks if short_name is an acronym of long_name."""
        s = short_name.upper().strip()
        l = long_name.strip()
        words = [w for w in re.split(r"[\s\-]+", l) if w and w[0].isalpha()]
        if not words or len(words) != len(s):
            return False
        first_letters = "".join(w[0].upper() for w in words)
        return s == first_letters

    @staticmethod
    def _is_fuzzy_match(s1: str, s2: str, threshold: float = 0.87) -> bool:
        """Catches near-duplicate names/phrasing (e.g. 'Neural Network' vs.
        'Neural Networks Model') that the plural/acronym rules miss."""
        if len(s1) < 6 or len(s2) < 6:
            return False
        if abs(len(s1) - len(s2)) > 6:
            return False
        return difflib.SequenceMatcher(None, s1, s2).ratio() >= threshold

    def find_match(self, name: str) -> Optional[str]:
        """Finds existing concept_id for the given name or alias."""
        cleaned = self.clean_name(name)
        lowered = cleaned.lower()

        if lowered in self.lookup:
            return self.lookup[lowered]

        # Check singular/plural match
        for existing_term, cid in self.lookup.items():
            if self._is_plural_match(lowered, existing_term):
                return cid

        # Check acronym match
        for existing_term, cid in self.lookup.items():
            if len(cleaned) <= 5 and cleaned.isupper() and self._is_acronym_match(cleaned, existing_term):
                return cid
            if len(existing_term) <= 5 and existing_term.isupper() and self._is_acronym_match(existing_term, cleaned):
                return cid

        # Fuzzy string match as a last resort, to merge near-duplicate phrasing
        for existing_term, cid in self.lookup.items():
            if self._is_fuzzy_match(lowered, existing_term):
                return cid

        return None

    def register_concept(
        self,
        name: str,
        aliases: Optional[List[str]] = None,
        concept_type: str = "Component",
        definition: str = "",
        chapter: str = "",
        section: str = "",
        page: int = 1,
        chunk_id: str = "",
        evidence: str = "",
    ) -> NormalizedConcept:
        """Registers a concept or merges it into an existing canonical concept."""
        cleaned = self.clean_name(name)
        if not cleaned:
            cleaned = "Concept"

        existing_id = self.find_match(cleaned)
        if existing_id:
            concept = self.concepts_by_id[existing_id]
            # Add as alias if different from canonical name
            if cleaned.lower() != concept.concept_name.lower():
                concept.aliases.add(cleaned)
                self.lookup[cleaned.lower()] = existing_id
            if aliases:
                for a in aliases:
                    clean_a = self.clean_name(a)
                    if clean_a and clean_a.lower() != concept.concept_name.lower():
                        concept.aliases.add(clean_a)
                        self.lookup[clean_a.lower()] = existing_id

            # Update definition if existing is empty or shorter
            if definition and (not concept.definition or len(definition) > len(concept.definition)):
                concept.definition = definition.strip()
                concept.evidence = evidence.strip() or concept.evidence
                concept.chapter = chapter or concept.chapter
                concept.section = section or concept.section
                concept.page = page or concept.page
                concept.chunk_id = chunk_id or concept.chunk_id

            # Refine concept type if not default
            if concept_type and concept_type != "Component":
                concept.concept_type = concept_type

            return concept

        # Create new canonical concept
        cid = self._generate_id()
        alias_set = set()
        if aliases:
            for a in aliases:
                clean_a = self.clean_name(a)
                if clean_a and clean_a.lower() != cleaned.lower():
                    alias_set.add(clean_a)

        concept = NormalizedConcept(
            concept_id=cid,
            concept_name=cleaned,
            aliases=alias_set,
            concept_type=concept_type or "Component",
            definition=definition.strip(),
            chapter=chapter,
            section=section,
            page=page,
            chunk_id=chunk_id,
            evidence=evidence.strip(),
        )

        self.concepts_by_id[cid] = concept
        self.lookup[cleaned.lower()] = cid
        for a in alias_set:
            self.lookup[a.lower()] = cid

        return concept

    def get_all_concepts(self) -> List[NormalizedConcept]:
        """Returns all canonical concepts sorted by ID."""
        return sorted(self.concepts_by_id.values(), key=lambda c: c.concept_id)
