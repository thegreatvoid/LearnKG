"""Regenerate the educational-pipeline flowcharts from the real step CSVs (documentation only).

  python -m educational_pipeline.dump_steps --data-dir ck12_geometry      # (re)creates the 01-10 CSVs
  python docs/make_pipeline_figures.py                                      # writes docs/educational_pipeline_*.{png,svg,mmd}

Every value drawn comes from data_output/ck12_geometry_steps/*.csv; nothing is typed in by hand. The traced example is
the chunk whose section is "1.4 Angle Pairs" and the relation Angle -> Vertical Angles (R0004); the concept-merge
example is "Equilateral Triangle" / "Equilateral Triangles". Long values are abbreviated with an ellipsis.
"""

import sys
import tempfile
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STEPS = ROOT / "data_output" / "ck12_geometry_steps"
OUT = ROOT / "docs"
EX_SECTION, EX_REL, EX_MERGE = "1.4 Angle Pairs", "R0004", "Equilateral Triangle"

COL = {"source": "#e8f1fb", "intermediate": "#fff6e0", "final": "#e6f6e9", "graph": "#f3e8fb"}
MONO = "DejaVu Sans Mono"


def rd(name):
    return pd.read_csv(STEPS / name, dtype=str, keep_default_na=False)


def short(v, n=34):
    v = str(v).replace("\n", "\\n")
    return v if len(v) <= n else v[: n - 1] + "…"


def load():
    t = {k: rd(v) for k, v in {
        "01": "01_parsed_blocks.csv", "02": "02_structured_blocks.csv", "03": "03_chunks.csv",
        "04": "04_concept_candidates.csv", "05": "05_normalized_concepts.csv", "06": "06_concept_definitions.csv",
        "07": "07_relation_candidates.csv", "08": "08_relations_classified.csv", "09": "09_relation_weights.csv",
        "10c": "10_dataset_concepts.csv", "10r": "10_dataset_relations.csv"}.items()}
    ex = {}
    chunk = t["03"][t["03"].section == EX_SECTION].iloc[0]
    ex["chunk_id"] = chunk.chunk_id
    rel = t["09"][t["09"].relation_id == EX_REL].iloc[0]
    ex["rel"] = rel
    ex["src"], ex["tgt"] = rel.source_id, rel.target_id
    names = t["05"].set_index("concept_id").concept_name
    ex["src_name"], ex["tgt_name"] = names[rel.source_id], names[rel.target_id]
    return t, ex


def selectors(t, ex):
    """Rows (and columns) displayed for each CSV: real rows chosen by identifier, abbreviated for display."""
    cid, sn, tn = ex["chunk_id"], ex["src_name"], ex["tgt_name"]
    S = {}
    s01 = t["01"][t["01"].text.str.startswith(EX_SECTION)]
    S["01"] = (s01.index[:1], ["page", "chapter", "section", "is_heading", "text"])
    s02 = t["02"][t["02"].text.str.startswith(EX_SECTION)]
    S["02"] = (s02.index[:1], ["idx", "block_type", "page", "chapter", "section", "text"])
    S["03"] = (t["03"][t["03"].chunk_id == cid].index, ["chunk_id", "block_type", "page", "section", "n_chars", "text"])
    c4 = t["04"][(t["04"].chunk_id == cid) & t["04"].candidate.isin([sn, tn, "Linear Pair"])]
    m4 = t["04"][t["04"].candidate.str.startswith(EX_MERGE)]
    S["04"] = (list(c4.index) + list(m4.index), ["chunk_id", "page", "chapter", "candidate"])
    S["05"] = (t["05"][t["05"].concept_name.isin([sn, tn, EX_MERGE])].index,
               ["concept_id", "concept_name", "aliases", "concept_type", "chapter", "page"])
    S["06"] = (t["06"][(t["06"].chunk_id == cid) & t["06"].concept.isin([sn, tn])].index,
               ["chunk_id", "concept", "definition", "evidence"])
    r7 = t["07"][(t["07"].source_name == sn) & (t["07"].target_name == tn)]
    S["07"] = (r7.index, ["source_name", "target_name", "raw_predicate", "evidence", "chunk_id"])
    S["08"] = (r7.index, ["relation_id", "source_name", "target_name", "raw_predicate", "classified_type", "status", "evidence"])
    S["09"] = (t["09"][t["09"].relation_id == EX_REL].index,
               ["relation_id", "relation_type", "weight", "weight_source", "cooccurrence_count",
                "semantic_similarity", "chapter_proximity", "educational_context"])
    S["10c"] = (t["10c"][t["10c"].concept_id.isin([ex["src"], ex["tgt"]])].index,
                ["concept_id", "concept_name", "concept_type", "definition", "chapter", "section", "page", "chunk_id"])
    S["10r"] = (t["10r"][t["10r"].relation_id == EX_REL].index,
                ["relation_id", "source_id", "target_id", "relation_type", "weight", "weight_source", "chunk_id", "evidence"])
    return S


def stage_specs(t, ex):
    cnt = lambda k: len(t[k])
    return [
        dict(k="01", n=1, name="Parse", file="01_parsed_blocks.csv", kind="intermediate",
             code="parser.parse_document -> parse_text_file",
             io=f"IN  ck12_basic_geometry_concepts.txt\nOUT {cnt('01')} ParsedBlock rows",
             op="split on blank lines; detect chapter/section headings;\nestimate page (~2500 chars/page); carry chapter+section"),
        dict(k="02", n=2, name="Structure detection", file="02_structured_blocks.csv", kind="intermediate",
             code="structure_detector.detect_educational_structures",
             io=f"IN  01 blocks\nOUT {cnt('02')} StructuredBlock rows",
             op="regex cues (Definition/Theorem/Example/...);\nheadings -> Chapter/Section; default Explanation"),
        dict(k="03", n=3, name="Chunking", file="03_chunks.csv", kind="intermediate",
             code="chunker.create_structure_aware_chunks",
             io=f"IN  02 blocks\nOUT {cnt('03')} chunks (uuid chunk_id)",
             op="buffer Explanations to <=1500 chars; flush on\nsection/chapter change; atomic types stay whole"),
        dict(k="04", n=4, name="Concept candidates", file="04_concept_candidates.csv", kind="intermediate",
             code="concept_extractor.extract_candidate_concepts_from_text",
             io=f"IN  03 chunk text (per chunk)\nOUT {cnt('04')} candidate rows",
             op="regex: Capitalised phrases, acronyms, quotes,\n'called X', 110-term geometry list; drop boilerplate"),
        dict(k="05", n=5, name="Normalise / merge", file="05_normalized_concepts.csv", kind="intermediate",
             code="normalizer.ConceptNormalizer.register_concept",
             io=f"IN  04 candidates (+06 definitions)\nOUT {cnt('05')} canonical concepts (C000n)",
             op="clean name; merge exact / plural / acronym matches\ninto one concept; extra spellings -> aliases"),
        dict(k="06", n=6, name="Definitions + evidence", file="06_concept_definitions.csv", kind="intermediate",
             code="definition_extractor.extract_grounded_definition",
             io=f"IN  candidate name + its chunk text\nOUT {cnt('06')} rows (1 per candidate)",
             op="'X is/are a ...' pattern in the chunk, else any\n30-250 char sentence mentioning X; no model"),
        dict(k="07", n=7, name="Relation candidates", file="07_relation_candidates.csv", kind="intermediate",
             code="RelationManager.extract_relations_from_sentences",
             io=f"IN  chunk sentences + 05 concepts\nOUT {cnt('07')} proposals (every add_relation call)",
             op="38 geometry regex rules; >=2 concepts in a sentence\n+ keyword cue => proposal (Prerequisite order by page)"),
        dict(k="08", n=8, name="Classify + merge", file="08_relations_classified.csv", kind="intermediate",
             code="relation_extractor.classify_relation; add_relation",
             io=f"IN  07 proposals\nOUT same {cnt('08')} rows + classified_type + status",
             op="map predicate to 5 types (exact, keyword, default\nApplication); key (src,tgt,type): new or duplicate_merged"),
        dict(k="09", n=9, name="Edge weights", file="09_relation_weights.csv", kind="intermediate",
             code="relation_extractor.ahp_components / calculate_ahp_weight",
             io=f"IN  new relations (08 status=new)\nOUT {cnt('09')} weighted relations",
             op="w = .52*S + .24*C + .09*P + .15*E; kept max on\nduplicates; neural/LLM weight would bypass (not used)"),
        dict(k="10c", n=10, name="Final dataset: concepts", file="10_dataset_concepts.csv", kind="final",
             code="dataset_builder.build_and_save_dataset",
             io=f"IN  normalizer registry\nOUT {cnt('10c')} concepts",
             op="dump registry (definition/evidence/chunk from the\nlongest definition seen) with newlines removed"),
        dict(k="10r", n=10, name="Final dataset: relations", file="10_dataset_relations.csv", kind="final",
             code="dataset_builder.build_and_save_dataset",
             io=f"IN  RelationManager.relations\nOUT {cnt('10r')} relations",
             op="dump relation list (= 09 content, evidence cleaned);\nids link to concepts via source_id/target_id"),
    ]


W_IN = 15.0
RH = 0.19          # table row height, inches
TABLE_X, TABLE_W = 5.0, 9.8


def _cw(fs):
    return fs * 0.62 / 72  # monospace character width in inches


def draw_table(ax, x, y, cols, rows, fs=6.4):
    """Draw a header+rows table with top-left at (x, y) in inch coordinates; shrink cell text until it fits TABLE_W."""
    maxw = 60
    while True:
        widths = [max([len(c)] + [len(short(r[c], maxw)) for r in rows]) + 2 for c in cols]
        if sum(widths) * _cw(fs) <= TABLE_W or maxw <= 8:
            break
        maxw -= 2
    cw = _cw(fs)
    cx = x
    for c, w in zip(cols, widths):
        ax.add_patch(Rectangle((cx, y - RH), w * cw, RH, fc="#d9d9d9", ec="#888", lw=0.4))
        ax.text(cx + 0.03, y - RH / 2, c, fontsize=fs, family=MONO, weight="bold", va="center")
        cx += w * cw
    for i, r in enumerate(rows, 1):
        cx = x
        for c, w in zip(cols, widths):
            ax.add_patch(Rectangle((cx, y - RH * (i + 1)), w * cw, RH, fc="white", ec="#aaa", lw=0.3))
            ax.text(cx + 0.03, y - RH * (i + 0.5), short(r[c], maxw), fontsize=fs, family=MONO, va="center")
            cx += w * cw
    return RH * (len(rows) + 1)


def stage_box(ax, s, rows, cols, top, note_fs=6.6):
    """One stage box (left: purpose/code/IO/operation, right: real CSV rows). Returns box height in inches."""
    box_h = max(1.35, RH * (len(rows) + 1) + 0.35)
    ax.add_patch(Rectangle((0.15, top - box_h), W_IN - 0.3, box_h, fc=COL[s["kind"]], ec="#555", lw=0.8))
    ax.text(0.25, top - 0.08, f"STAGE {s['n']} - {s['name']}", fontsize=9, weight="bold", va="top")
    ax.text(0.25, top - 0.30, s["file"], fontsize=7.4, family=MONO, va="top", color="#003a8c")
    ax.text(0.25, top - 0.47, s["code"], fontsize=5.6, family=MONO, va="top", color="#444")
    ax.text(0.25, top - 0.64, s["io"], fontsize=note_fs, va="top", linespacing=1.3)
    ax.text(0.25, top - 0.98, s["op"], fontsize=note_fs, va="top", linespacing=1.3, color="#333")
    draw_table(ax, TABLE_X, top - 0.12, cols, rows)
    return box_h


def figure(title, subtitle, stages, t, S, specs, max_rows, fname, notes=None):
    spec = {s["k"]: s for s in specs}
    heights = [max(1.35, RH * (min(max_rows, len(S[k][0])) + 1) + 0.35) for k in stages]
    n_note_lines = (notes.count("\n") + 1) if notes else 0
    H = 1.0 + sum(heights) + 0.35 * len(stages) + 0.18 * n_note_lines + 0.3
    fig = plt.figure(figsize=(W_IN, H)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_IN); ax.set_ylim(0, H); ax.axis("off")
    ax.text(W_IN / 2, H - 0.1, title, ha="center", va="top", fontsize=13, weight="bold")
    ax.text(W_IN / 2, H - 0.45, subtitle, ha="center", va="top", fontsize=8, style="italic")
    y = H - 0.9
    prev_bottom = None
    for k in stages:
        s = spec[k]
        rows = [t[k].loc[i] for i in list(S[k][0])[:max_rows]]
        h = stage_box(ax, s, rows, S[k][1], y)
        if prev_bottom is not None:
            ax.add_patch(FancyArrowPatch((W_IN / 2, prev_bottom), (W_IN / 2, y), arrowstyle="-|>", mutation_scale=14, color="#222", lw=1.3, zorder=5))
        prev_bottom = y - h
        y = y - h - 0.35
    if notes:
        ax.text(0.2, y + 0.1, notes, fontsize=7, va="top", linespacing=1.4)
    plt.savefig(OUT / f"{fname}.png", dpi=130, bbox_inches="tight")
    plt.savefig(OUT / f"{fname}.svg", bbox_inches="tight")
    plt.close(fig)


def graph_facts(t, ex):
    """Run the project's own graph builder on the final CSVs (output HTML goes to a temp dir)."""
    from educational_pipeline.graph_builder import build_educational_graph
    tmp = Path(tempfile.mkdtemp()) / "g.html"
    G = build_educational_graph(STEPS / "10_dataset_concepts.csv", STEPS / "10_dataset_relations.csv", output_html=tmp)
    e = G.edges[ex["src"], ex["tgt"]]
    return G, {k: e.get(k) for k in ("relation_type", "weight", "value", "color")}, {k: G.nodes[ex["src"]].get(k) for k in ("label", "concept_type", "group", "size")}


def graph_figure(t, ex, specs, S, G, eattr, nattr):
    spec = {s["k"]: s for s in specs}
    txt = (f"STAGE 11 - Knowledge graph  (graph_builder.build_educational_graph; networkx.DiGraph = directed)\n"
           f"result on this run: {G.number_of_nodes()} nodes, {G.number_of_edges()} directed edges\n"
           f"node <- one 10_dataset_concepts row (key = concept_id); attrs: label, concept_type, definition, tooltip(aliases, chapter, page);\n"
           f"        then added: community group (Girvan-Newman) and size (PageRank)\n"
           f"edge <- one 10_dataset_relations row, arrow = source_id -> target_id; attrs: relation_type, weight, colour, tooltip(evidence);\n"
           f"        Similarity rows also get a reverse edge; rows whose endpoints are not nodes are skipped\n"
           f"traced edge {ex['src']} ({ex['src_name']}) -> {ex['tgt']} ({ex['tgt_name']}):\n"
           f"        {eattr}\n"
           f"traced node {ex['src']}: {nattr}\n"
           f"export: pyvis HTML (docs/ck12_geometry.html via run_geometry_pipeline.py); graph_stats.py is a separate consumer of the CSVs.\n"
           f"NOT carried into the graph: weight_source, cooccurrence_count and the S/P/E factors; pyvis from_nx() renames edge 'weight' to 'value'.")
    nl = txt.count("\n") + 1
    rows_h = [RH * (min(3, len(S[k][0])) + 1) + 0.35 for k in ("10c", "10r")]
    H = 1.0 + sum(max(1.35, h) for h in rows_h) + 0.4 + 0.2 * nl + 0.6
    fig = plt.figure(figsize=(W_IN, H)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W_IN); ax.set_ylim(0, H); ax.axis("off")
    ax.text(W_IN / 2, H - 0.1, "FIGURE 4 - Final dataset assembly and graph construction", ha="center", va="top", fontsize=13, weight="bold")
    ax.text(W_IN / 2, H - 0.45, "build_and_save_dataset writes 10_*.csv; graph_builder.build_educational_graph reads them (separate stage). Values abbreviated with '…'.", ha="center", va="top", fontsize=8, style="italic")
    y = H - 0.9
    prev = None
    for k in ("10c", "10r"):
        rows = [t[k].loc[i] for i in list(S[k][0])[:3]]
        h = stage_box(ax, spec[k], rows, S[k][1], y)
        y -= h + 0.2
    ax.add_patch(FancyArrowPatch((W_IN / 2, y + 0.2), (W_IN / 2, y - 0.1), arrowstyle="-|>", mutation_scale=14, color="#222", lw=1.3))
    y -= 0.2
    hh = 0.2 * nl + 0.3
    ax.add_patch(Rectangle((0.15, y - hh), W_IN - 0.3, hh, fc=COL["graph"], ec="#555", lw=0.8))
    ax.text(0.25, y - 0.1, txt, fontsize=6.8, va="top", family=MONO, linespacing=1.45)
    plt.savefig(OUT / "educational_pipeline_fig4_graph.png", dpi=130, bbox_inches="tight")
    plt.savefig(OUT / "educational_pipeline_fig4_graph.svg", bbox_inches="tight")
    plt.close(fig)


def mermaid(t, ex, specs):
    lines = ["%% Generated by docs/make_pipeline_figures.py from data_output/ck12_geometry_steps/*.csv", "flowchart TD",
             '  SRC["ck12_basic_geometry_concepts.txt<br/>(source textbook)"]:::source']
    prev = "SRC"
    for s in specs:
        nid = f"S{s['k']}"
        label = f"STAGE {s['n']} {s['name']}<br/><b>{s['file']}</b><br/>{s['io'].splitlines()[-1].replace('OUT ', '')}"
        lines.append(f'  {nid}["{label}"]:::{s["kind"]}')
        if s["k"] not in ("10r",):
            lines.append(f"  {prev} --> {nid}")
            prev = nid
    lines += [f"  S09 --> S10r", "  S05 --> S10c", "  S10c --> G", "  S10r --> G",
              '  G["STAGE 11 Knowledge graph<br/>networkx.DiGraph -> pyvis HTML"]:::graph',
              "  S05 -.->|concept names| S07", "  S03 -.->|chunk text| S04", "  S03 -.->|chunk text| S06", "  S03 -.->|sentences| S07",
              "  classDef source fill:#e8f1fb,stroke:#555", "  classDef intermediate fill:#fff6e0,stroke:#555",
              "  classDef final fill:#e6f6e9,stroke:#555", "  classDef graph fill:#f3e8fb,stroke:#555"]
    (OUT / "educational_pipeline_flowchart.mmd").write_text("\n".join(lines) + "\n")


def main():
    t, ex = load()
    S = selectors(t, ex)
    specs = stage_specs(t, ex)
    sub = f"Traced example: chunk {ex['chunk_id'][:8]}… (section '{EX_SECTION}'), relation {EX_REL}: {ex['src_name']} -> {ex['tgt_name']}. Values abbreviated with '…'."
    figure("FIGURE 1 - Educational pipeline: data lineage with real CSV records (CK-12 Basic Geometry)", sub,
           ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10c", "10r"], t, S, specs, 1, "educational_pipeline_fig1_overview")
    figure("FIGURE 2 - Concept extraction and normalisation (stages 3-6, 10 concepts)", sub, ["03", "04", "05", "06", "10c"], t, S, specs, 4,
           "educational_pipeline_fig2_concepts",
           notes="Many-to-one: 'Equilateral Triangle' appears in 3 chunks and 'Equilateral Triangles' once in 04; 05 holds ONE concept (C0021) with the plural as alias.\n"
                 "04 has no concept_id; the link 04 -> 05 is by (cleaned, case-insensitive) name. 05 does not store the definition: that is kept in the registry and appears in 10.")
    figure("FIGURE 3 - Relation candidates, classification and weighting (stages 7-9)", sub, ["07", "08", "09", "10r"], t, S, specs, 3,
           "educational_pipeline_fig3_relations",
           notes="07 and 08 are the same list (08 = 07 + relation_id/classified_type/status), aligned by row position; 07 has no id.\n"
                 f"R0004 appears twice in 08: first sentence -> status 'new' (an edge is created), second sentence -> 'duplicate_merged' (same src,tgt,type: co-occurrence count 2, weight = max).\n"
                 f"Weight check from the 09 row: .52*{ex['rel'].semantic_similarity} + .24*min(1,{ex['rel'].cooccurrence_count}/3) + .09*{ex['rel'].chapter_proximity} + .15*{ex['rel'].educational_context} = "
                 f"{0.52*float(ex['rel'].semantic_similarity)+0.24*min(1,int(ex['rel'].cooccurrence_count)/3)+0.09*float(ex['rel'].chapter_proximity)+0.15*float(ex['rel'].educational_context):.4f} (09 weight: {ex['rel'].weight}).")
    G, eattr, nattr = graph_facts(t, ex)
    graph_figure(t, ex, specs, S, G, eattr, nattr)
    mermaid(t, ex, specs)
    print("wrote figures to", OUT)


if __name__ == "__main__":
    main()
