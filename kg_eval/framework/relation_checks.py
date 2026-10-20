"""Phase 4: AUTOMATIC VALIDATION DIAGNOSTICS for all five relation types (not ground truth).

Every check below is a heuristic consistency or evidence check. Passing a check does not make an edge correct,
failing one does not make it wrong; flagged edges are kept and listed with reasons. No precision/recall is
computed here (no labels for Part-of / Application / Similarity / Extension; see annotation/).

Checks (per edge s -[type]-> t, documented convention: source s, target t):
  support        book sentences mentioning both concepts (sentence co-occurrence = textual support only)
  grounding      cosine distance of "s type t" to the nearest book sentence (per-edge BIGS<-; lower = closer)
  cue            a validator cue lexicon (separate from the pipeline's ONTOLOGY_PATTERNS) in a support sentence,
                 with concept positions: 'supports' the stored direction, 'reverse', or 'none'.
                 For rule KG edges created by the keyword extractor this is NOT independent (flag `cue_not_independent`).
  reciprocal     the same type stored in both directions (for directed types: contradiction; Similarity: duplicate)
  cycle          edge lies on a directed cycle of its own type (Prerequisite, Part-of, Extension)
  book_order     Prerequisite: s first mentioned before t; Extension: t before s (circular for book-order KGs)
  alcpl          Prerequisite only, where AL-CPL labels the pair: correct / reversed / negative / unlabelled
  name_head      Part-of and Similarity: s's name ends with t's name ("right triangle" vs "triangle"): a kind-of
                 pattern, i.e. possible Extension rather than Part-of / Similarity
  congruence     Similarity: evidence or names involve congruence (geometric congruence is not conceptual similarity)
  def_embedding / def_lexical   Similarity: cosine of definition embeddings and Jaccard of definition words (separate)
  type_conflict  the same unordered pair carries another relation type; Extension s->t together with Prerequisite s->t

  python -m kg_eval.framework.relation_checks
"""

import re
from collections import Counter, defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from educational_pipeline.relation_extractor import jaccard, _word_set
from .common import KG, KGS, RELATION_TYPES, book_sentences, gold, out_dir, write_json

# forward = "<source> CUE <target>" supports s->t ; reverse = "<target> CUE <source>" supports s->t
CUES = {
    "Prerequisite": {"forward": ["is needed for", "is needed to", "is used to define", "is the basis of", "is required for",
                                 "is necessary for", "comes before", "leads to"],
                     "reverse": ["requires", "require", "depends on", "is defined using", "is built from", "uses", "use",
                                 "using", "based on", "builds on", "recall", "from"]},
    "Part-of": {"forward": ["part of", "component of", "piece of", "portion of", "side of", "vertex of", "segment of",
                            "edge of", "face of", "belongs to", "lies on", "lies in", "contained in", "inside", "of a", "of the"],
                "reverse": ["has", "have", "consists of", "contains", "includes", "is made of", "is composed of",
                            "is formed by", "formed by", "made up of", "with"]},
    "Application": {"forward": ["used to", "used for", "used in", "is applied", "applies to", "to find", "to calculate",
                                "to prove", "to solve", "to determine", "helps", "allows"],
                    "reverse": ["uses", "use", "using", "by applying", "with the help of", "applying"]},
    "Extension": {"forward": ["special case of", "type of", "kind of", "extension of", "extends", "generalizes",
                              "generalization of", "variant of", "derived from", "converse of", "based on", "builds on"],
                  "reverse": ["is extended by", "can be generalized to", "special cases", "types of", "kinds of"]},
    "Similarity": {"any": ["similar to", "like", "same as", "analogous", "both", "whereas", "unlike", "compared",
                           "congruent", "equal", "corresponding", "resembles", "also"]},
}
ANY_CUE = re.compile(r"\b(?:" + "|".join(sorted({re.escape(c) for d in CUES.values() for v in d.values() for c in v},
                                                 key=len, reverse=True)) + r")\b", re.I)


def term_re(terms):
    parts = [r"[\s\-]+".join(map(re.escape, re.findall(r"[a-z0-9]+", t.lower()))) for t in terms]
    parts = [p for p in parts if p]
    return re.compile(r"\b(?:" + "|".join(parts) + r")(?:s|es)?\b", re.I) if parts else None


def cue_direction(sentence, s_re, t_re, rel):
    """'supports' / 'reverse' / 'none' for one sentence (first mentions of s and t, cue between them)."""
    ms, mt = s_re.search(sentence), t_re.search(sentence)
    if not ms or not mt:
        return "none"
    cues = CUES[rel]
    if "any" in cues:
        return "supports" if any(re.search(rf"\b{re.escape(c)}\b", sentence, re.I) for c in cues["any"]) else "none"
    lo, hi = sorted([ms, mt], key=lambda m: m.start())
    between = sentence[lo.end():hi.start()]
    s_first = ms.start() < mt.start()
    for kind in ("forward", "reverse"):
        for c in cues[kind]:
            if re.search(rf"\b{re.escape(c)}\b", between, re.I):
                ok = (kind == "forward") == s_first
                return "supports" if ok else "reverse"
    return "none"


CONTRADICTION = {"cue_suggests_reverse_direction", "reciprocal_contradiction", "on_cycle", "alcpl_negative",
                 "alcpl_reversed", "book_order_backward", "book_order_backward(circular_kg)",
                 "extension_base_introduced_later", "extension_contradicts_prerequisite_direction"}
WEAK_EVIDENCE = {"no_support_sentence", "support_without_relation_cue", "no_Prerequisite_cue", "no_Part-of_cue",
                 "no_Application_cue", "no_Similarity_cue", "no_Extension_cue"}
SEMANTIC = {"kind_of_name_pattern", "possible_congruence_confusion", "type_conflict", "reciprocal_duplicate"}


def cycle_edges(edges):
    G = nx.DiGraph(edges)
    on = set()
    for comp in nx.strongly_connected_components(G):
        if len(comp) > 1:
            on |= {(u, v) for u, v in G.subgraph(comp).edges}
    return on


def check_kg(kg: KG, model, sent_emb, sents):
    rel = kg.relations
    by_type = {t: list(zip(rel.loc[rel.relation_type == t, "source_id"], rel.loc[rel.relation_type == t, "target_id"]))
               for t in RELATION_TYPES}
    cycles = {t: cycle_edges(by_type[t]) for t in ("Prerequisite", "Part-of", "Extension")}
    pair_types = defaultdict(set)
    for s, t, ty in zip(rel.source_id, rel.target_id, rel.relation_type):
        pair_types[frozenset((s, t))].add(ty)
    directed = {(s, t, ty) for s, t, ty in zip(rel.source_id, rel.target_id, rel.relation_type)}
    res_cache = {cid: term_re(kg.terms(cid)) for cid in kg.objects}
    pos = kg.positions
    valid = kg.valid_definitions
    g = gold()
    m = kg.gold_matches(g)
    gold_lab = {}
    for a, b, y in zip(g.concept, g.prereq, g.label):
        ca, cb = m[a]["cid"], m[b]["cid"]
        if ca and cb:
            gold_lab[(cb, ca)] = int(y)
    sources = rel["sources"] if "sources" in rel else pd.Series([""] * len(rel))
    triples = [f"{kg.name_of[s]} {ty} {kg.name_of[t]}" for s, t, ty in zip(rel.source_id, rel.target_id, rel.relation_type)]
    tri_emb = model.encode(triples, normalize_embeddings=True)
    ground = (1.0 - tri_emb @ sent_emb.T).min(axis=1)
    def_text = {cid: (o.definition if valid[cid] else o.concept_name) for cid, o in kg.objects.items()}
    rows = []
    need_emb = sorted({c for s, t, ty in zip(rel.source_id, rel.target_id, rel.relation_type) if ty == "Similarity" for c in (s, t)})
    demb = dict(zip(need_emb, model.encode([def_text[c] for c in need_emb], normalize_embeddings=True))) if need_emb else {}
    for i, (s, t, ty, ev, src) in enumerate(zip(rel.source_id, rel.target_id, rel.relation_type, rel.evidence, sources)):
        sr, tr = res_cache[s], res_cache[t]
        sup = [x for x in sents if sr and tr and sr.search(x) and tr.search(x)]
        r = {"relation_id": rel.relation_id.iloc[i], "source": kg.name_of[s], "target": kg.name_of[t], "type": ty,
             "n_support_sentences": len(sup), "grounding_distance": round(float(ground[i]), 4),
             "edge_sources": src, "cue_not_independent": "keyword" in str(src)}
        flags = []
        if not sup:
            flags.append("no_support_sentence")
        cue = "none"
        for x in sup:
            d = cue_direction(x, sr, tr, ty)
            if d == "supports":
                cue = "supports"
                break
            if d == "reverse":
                cue = "reverse"
        r["cue"] = cue
        if sup and cue == "none":
            flags.append("support_without_relation_cue" if not any(ANY_CUE.search(x) for x in sup) else f"no_{ty}_cue")
        if cue == "reverse" and ty in ("Prerequisite", "Part-of", "Application", "Extension"):
            flags.append("cue_suggests_reverse_direction")
        if (t, s, ty) in directed:
            flags.append("reciprocal_duplicate" if ty == "Similarity" else "reciprocal_contradiction")
        if ty in cycles and (s, t) in cycles[ty]:
            flags.append("on_cycle")
        ps, pt = pos.get(s), pos.get(t)
        if ty == "Prerequisite" and ps is not None and pt is not None:
            r["book_order_consistent"] = ps < pt
            if ps > pt:
                flags.append("book_order_backward" + ("(circular_kg)" if kg.uses_book_order else ""))
        if ty == "Extension" and ps is not None and pt is not None:
            r["book_order_consistent"] = pt < ps
            if pt > ps:
                flags.append("extension_base_introduced_later")
        if ty == "Prerequisite":
            lab = gold_lab.get((s, t))
            rev = gold_lab.get((t, s))
            r["alcpl"] = ("correct" if lab == 1 else "negative" if lab == 0 else
                          "reversed" if rev == 1 else "unlabelled")
            if r["alcpl"] in ("negative", "reversed"):
                flags.append(f"alcpl_{r['alcpl']}")
        sn, tn = kg.name_of[s].lower(), kg.name_of[t].lower()
        if ty in ("Part-of", "Similarity") and sn != tn and (sn.endswith(" " + tn) or tn.endswith(" " + sn)):
            flags.append("kind_of_name_pattern")
        if ty == "Similarity":
            text = " ".join([ev, sn, tn] + sup[:3]).lower()
            if "congruen" in text:
                flags.append("possible_congruence_confusion")
            r["def_embedding"] = round(float(demb[s] @ demb[t]), 4)
            r["def_lexical"] = round(jaccard(_word_set(def_text[s]), _word_set(def_text[t])), 4)
        others = pair_types[frozenset((s, t))] - {ty}
        if others:
            flags.append("type_conflict:" + "+".join(sorted(others)))
        if ty == "Extension" and (s, t, "Prerequisite") in directed:
            flags.append("extension_contradicts_prerequisite_direction")
        r["flags"] = ";".join(flags)
        r["example_sentence"] = sup[0] if sup else ev
        rows.append(r)
    df = pd.DataFrame(rows)
    summary = {}
    for ty in RELATION_TYPES:
        d = df[df.type == ty]
        if d.empty:
            summary[ty] = {"edges": 0}
            continue
        fl = Counter(f.split(":")[0] for x in d["flags"] for f in x.split(";") if f)
        summary[ty] = {
            "edges": len(d), "with_support_sentence": int((d.n_support_sentences > 0).sum()),
            "cue_supports": int((d.cue == "supports").sum()), "cue_reverse": int((d.cue == "reverse").sum()),
            "cue_none": int((d.cue == "none").sum()), "cue_not_independent": int(d.cue_not_independent.sum()),
            "flagged_any": int((d["flags"] != "").sum()), "flag_counts": dict(fl),
            "flagged_contradiction": int(d["flags"].apply(lambda x: any(f.split(":")[0] in CONTRADICTION for f in x.split(";") if f)).sum()),
            "flagged_weak_evidence": int(d["flags"].apply(lambda x: any(f in WEAK_EVIDENCE for f in x.split(";") if f)).sum()),
            "flagged_semantic_or_type": int(d["flags"].apply(lambda x: any(f.split(":")[0] in SEMANTIC for f in x.split(";") if f)).sum()),
            "co_occurrence_only": int(d["flags"].str.contains("support_without_relation_cue").sum()),
            "direction_inconsistencies": int(sum(fl.get(k, 0) for k in ("cue_suggests_reverse_direction", "reciprocal_contradiction",
                                                                       "book_order_backward", "book_order_backward(circular_kg)",
                                                                       "extension_base_introduced_later"))),
            "structural_violations": int(fl.get("on_cycle", 0) + fl.get("extension_contradicts_prerequisite_direction", 0)),
            "grounding_distance_median": float(d.grounding_distance.median()),
            "grounding_distance_iqr": [float(d.grounding_distance.quantile(.25)), float(d.grounding_distance.quantile(.75))],
        }
        if ty == "Prerequisite":
            summary[ty]["alcpl"] = d["alcpl"].value_counts().to_dict()
            if "book_order_consistent" in d:
                summary[ty]["book_order_forward_rate"] = float(d.book_order_consistent.dropna().astype(bool).mean())
        if ty == "Similarity":
            summary[ty]["def_embedding_median"] = float(d.def_embedding.median())
            summary[ty]["def_lexical_median"] = float(d.def_lexical.median())
        ok = d[(d["flags"] == "") & (d.cue == "supports")].head(3)
        bad = d[d["flags"].apply(lambda x: any(f.split(":")[0] in CONTRADICTION for f in x.split(";") if f))].head(3)
        summary[ty]["examples_pass"] = ok[["source", "target", "example_sentence"]].to_dict("records")
        summary[ty]["examples_flagged"] = bad[["source", "target", "flags", "example_sentence"]].to_dict("records")
    return df, summary


def main():
    from ..bigs import load_embedder
    from ..data import read_source, split_sentences
    model = load_embedder()
    bigs_sents = split_sentences(read_source(__import__("kg_eval.data", fromlist=["DEFAULT_SOURCE"]).DEFAULT_SOURCE))
    sent_emb = model.encode(bigs_sents, normalize_embeddings=True)
    sents = book_sentences()
    out = out_dir("relations")
    report = {"disclaimer": "Automatic validation diagnostics only: not ground-truth precision or recall. Flags: contradiction = the evidence or structure points against the stored edge/direction; weak_evidence = no supporting sentence or no explicit cue (common for genuine relations too); semantic_or_type = possible type confusion.",
              "cue_lexicon": CUES, "kgs": {}}
    for name in KGS:
        kg = KG(name)
        df, summary = check_kg(kg, model, sent_emb, sents)
        df.to_csv(out / f"edge_checks_{name}.csv", index=False)
        report["kgs"][name] = {"desc": kg.desc, "uses_book_order": kg.uses_book_order, "by_type": summary}
        print(f"\n## {name}")
        for ty, s in summary.items():
            if s["edges"]:
                print(f"  {ty:12s} edges={s['edges']:4d} support={s['with_support_sentence']:4d} cue+={s['cue_supports']:3d} "
                      f"cue-rev={s['cue_reverse']:3d} contra={s['flagged_contradiction']:4d} weak={s['flagged_weak_evidence']:4d} "
                      f"sem={s['flagged_semantic_or_type']:3d} dir_incons={s['direction_inconsistencies']:3d} "
                      f"struct={s['structural_violations']:3d} ground_med={s['grounding_distance_median']:.3f}")
    write_json(out / "relation_checks_report.json", report)


if __name__ == "__main__":
    main()
