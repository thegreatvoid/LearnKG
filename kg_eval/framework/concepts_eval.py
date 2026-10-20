"""Phase 2: concept extraction evaluation (separate from relations).

Reference: the AL-CPL geometry concept list (89 Wikipedia titles) is a PARTIAL reference: it gives coverage
(recall of those 89) but not precision, because the book contains many concepts AL-CPL does not list.
Precision/recall/F1 over the book are NOT computed: there is no concept annotation of the book. A template for
one is written to annotation/concepts/.

  python -m kg_eval.framework.concepts_eval
"""

import random
import re

import pandas as pd

from educational_pipeline.concept_extractor import DOMAIN_TERMS
from ..prereq_gold import gold_text_terms
from .common import KG, KGS, book_chunks, book_text, gold, out_dir, write_json

INVESTIGATED = ["SSS", "SAS", "ASA", "AAS", "HL", "Special Right Triangles", "Area", "Similarity", "Sine"]
HEADING = re.compile(r"^\s*(?:chapter\s+\d+\b.*|\d+(?:\.\d+)+\s+\S.*)$", re.I)


def where_in_book(terms):
    """'body' if a term occurs in a non-heading line, 'heading_only' if only in heading lines, 'absent' otherwise."""
    pats = [re.compile(r"\b" + r"[\s\-]+".join(map(re.escape, re.findall(r"[a-z0-9]+", t.lower()))) + r"(?:s|es)?\b", re.I)
            for t in terms if re.findall(r"[a-z0-9]+", t.lower())]
    body = heading = False
    for line in book_text().splitlines():
        if any(p.search(line) for p in pats):
            if HEADING.match(line):
                heading = True
            else:
                body = True
    return "body" if body else ("heading_only" if heading else "absent")


def candidate_reason(kg: KG, terms):
    """Why a term is not a concept: kg_extract keeps a candidate log; the rule pipeline does not."""
    log = kg.path / "concept_candidates.csv"
    if log.exists():
        cc = pd.read_csv(log, keep_default_na=False)
        names = cc.name.str.lower()
        for t in terms:
            for v in (t.lower(), t.lower() + "s", t.lower().rstrip("s")):
                hit = cc[names == v]
                if len(hit):
                    r = hit.iloc[0]
                    return f"candidate '{r['name']}' dropped: {r.dropped or 'kept but merged/renamed'} (cues {r.cues}, freq {r.freq})"
        return "never proposed as a candidate"
    t0 = terms[0]
    if re.fullmatch(r"[A-Z]{1,2}", t0):
        return "rule pipeline: acronyms shorter than 3 letters are dropped (concept_extractor)"
    return "rule pipeline: not proposed (not capitalised in text, no 'called X' pattern, not in hard-coded DOMAIN_TERMS)"


def evaluate(kg: KG, g: pd.DataFrame):
    m = kg.gold_matches(g)
    names = sorted(m)
    pos = g[g.label == 1]
    missing = [n for n in names if not m[n]["cid"]]
    rows = []
    for n in missing:
        terms = gold_text_terms(n)
        rows.append({"alcpl_concept": n, "in_book": where_in_book(terms),
                     "positive_pairs_involving": int(((pos.concept == n) | (pos.prereq == n)).sum()),
                     "labelled_pairs_involving": int(((g.concept == n) | (g.prereq == n)).sum()),
                     "reason": candidate_reason(kg, terms) if where_in_book(terms) != "absent" else
                     "not in the textbook (reference/book mismatch, not an extraction error)"})
    present = {n.lower() for n in kg.concepts.concept_name} | {
        a.strip().lower() for al in kg.concepts.aliases for a in al.split(",") if a.strip()}
    domain = {d.lower() for d in DOMAIN_TERMS}
    matched_cids = {v["cid"] for v in m.values() if v["cid"]}
    hard_coded_matched = sorted(kg.name_of[c] for c in matched_cids if kg.name_of[c].lower() in domain)
    valid = kg.valid_definitions
    inv = []
    for t in INVESTIGATED:
        has = any(v in present for v in (t.lower(), t.lower() + "s"))
        inv.append({"term": t, "present": has, "in_book": where_in_book([t]),
                    "in_hard_coded_list": t.lower() in domain,
                    "reason_if_absent": "" if has else candidate_reason(kg, [t])})
    pos_aff = pos[pos.concept.isin(missing) | pos.prereq.isin(missing)]
    return {
        "kg": kg.name, "desc": kg.desc, "n_concepts": len(kg.concepts),
        "concept_names_found_in_book": sum(1 for p in kg.positions.values() if p is not None),
        "alcpl_concepts": len(names), "alcpl_matched": len(names) - len(missing),
        "alcpl_matched_high_conf": sum(1 for v in m.values() if v["cid"] and v["confidence"] == "high"),
        "alcpl_coverage": (len(names) - len(missing)) / len(names),
        "missing": rows,
        "missing_by_cause": pd.Series([r["in_book"] for r in rows]).value_counts().to_dict() if rows else {},
        "positive_pairs_total": len(pos), "positive_pairs_with_missing_concept": len(pos_aff),
        "max_prerequisite_recall_given_concepts": 1 - len(pos_aff) / len(pos),
        "matched_concepts_also_in_hard_coded_list": hard_coded_matched,
        "kg_concepts_in_hard_coded_list": int(sum(n.lower() in domain for n in kg.concepts.concept_name)),
        "definitions_valid": int(sum(valid.values())), "definitions_total": len(valid),
        "definition_kind": kg.concepts["definition_kind"].value_counts().to_dict() if "definition_kind" in kg.concepts else None,
        "investigated_terms": inv,
    }


def annotation_template(kgs, n_sections=8, seed=0):
    """Blind concept-presence template: section text + union of proposed terms; who proposed what is in a key file."""
    chunks = [c for c in book_chunks() if c.section]
    by_chapter = {}
    for c in chunks:
        by_chapter.setdefault(c.chapter, []).append(c)
    rng = random.Random(seed)
    chapters = sorted(by_chapter, key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 0)
    picks = [rng.choice(by_chapter[ch]) for ch in rng.sample(chapters, min(n_sections, len(chapters)))]
    items, key, texts = [], [], []
    for si, c in enumerate(picks, 1):
        texts.append(f"### S{si}: {c.section}\n\n{c.text}\n")
        proposed = {}
        for kg in kgs:
            for cid, obj in kg.objects.items():
                for t in [obj.concept_name, *obj.aliases]:
                    if re.search(r"\b" + re.escape(t) + r"\b", c.text, re.I):
                        proposed.setdefault(obj.concept_name.lower(), set()).add(kg.name)
                        break
        for j, term in enumerate(sorted(proposed), 1):
            iid = f"S{si}-T{j:03d}"
            items.append({"item_id": iid, "section": c.section, "term": term, "is_concept": "",
                          "annotator_id": "", "confidence_1to3": "", "notes": ""})
            key.append({"item_id": iid, "proposed_by": ";".join(sorted(proposed[term]))})
        for j in range(1, 6):  # free rows for concepts no KG proposed
            items.append({"item_id": f"S{si}-NEW{j}", "section": c.section, "term": "", "is_concept": "",
                          "annotator_id": "", "confidence_1to3": "", "notes": "concept missed by all KGs"})
    d = out_dir("annotation", "concepts")
    pd.DataFrame(items).to_csv(d / "concept_presence_items.csv", index=False)
    pd.DataFrame(key).to_csv(d / "concept_presence_KEY_do_not_show_annotators.csv", index=False)
    (d / "sections.md").write_text("# Sections to annotate (sampled one per chapter, seed 0)\n\n" + "\n".join(texts))
    return {"sections": [c.section for c in picks], "items": len(items)}


def main():
    g = gold()
    kgs = [KG(n) for n in KGS]
    res = {k.name: evaluate(k, g) for k in kgs}
    same = set(KG("kgx_v2").concepts.concept_name) == set(KG("kgx_v2_hybrid").concepts.concept_name)
    res["_notes"] = {"kgx_v2_and_hybrid_have_identical_concepts": same,
                     "reference": "AL-CPL geometry concept list (partial; coverage only, no precision)",
                     "annotation_template": annotation_template(kgs)}
    d = out_dir("concepts")
    write_json(d / "concepts_report.json", res)
    rows = []
    for k in kgs:
        r = res[k.name]
        rows += [{"kg": k.name, **{x: r[x] for x in ("alcpl_concept", "in_book", "positive_pairs_involving", "reason")}}
                 for r in [dict(x, alcpl_concept=x["alcpl_concept"]) for x in r["missing"]]]
    pd.DataFrame(rows).to_csv(d / "missing_alcpl_concepts.csv", index=False)
    for k in kgs:
        r = res[k.name]
        print(f"{k.name:16s} concepts={r['n_concepts']:4d} AL-CPL coverage={r['alcpl_matched']}/{r['alcpl_concepts']} "
              f"positives touching a missing concept={r['positive_pairs_with_missing_concept']}/{r['positive_pairs_total']} "
              f"defs valid={r['definitions_valid']}/{r['definitions_total']} in hard-coded list={r['kg_concepts_in_hard_coded_list']}")
        print("   missing by cause:", r["missing_by_cause"], "| investigated present:",
              {x["term"]: x["present"] for x in r["investigated_terms"]})


if __name__ == "__main__":
    main()
