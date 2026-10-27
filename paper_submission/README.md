# Conference Paper Submission Directory: LearnKG Comparative Study

This directory contains the complete, modular LaTeX source code, figures, tables, bibliography, and audit documentation for the comparative evaluation research paper:

> **Evaluating Local Large Language Models for Educational Prerequisite Extraction: The Surprising Dominance of Structural Reading-Order Priors**

---

## 1. Directory Structure

```text
paper_submission/
├── main.tex                         # Master document (packages, layout, section imports)
├── references.bib                   # Clean, verified BibTeX bibliography (10 verified citations)
├── sections/                        # Modular manuscript sections
│   ├── abstract.tex                 # Abstract (context, benchmark results, core insight)
│   ├── introduction.tex             # Introduction (motivation, problem, research questions, contributions)
│   ├── related_work.tex             # Related work (CPL, EKGs, LLM extraction, structural priors)
│   ├── problem_formulation.tex      # Mathematical definitions & 5-relation ontology
│   ├── methodology.tex              # Comprehensive descriptions of Pipelines, Baselines & Ablations
│   ├── experimental_setup.tex       # Corpus (CK-12), Benchmark (AL-CPL), alignment & matching
│   ├── results.tex                  # Main empirical results & edge-weighting ablations
│   ├── error_analysis.tex           # Qualitative & quantitative failure mode diagnostics
│   ├── discussion.tex               # Architectural implications & de-confounding structural priors
│   ├── threats_to_validity.tex      # Internal, construct, and external threats
│   ├── reproducibility.tex          # Exact environment, data provenance & execution commands
│   └── conclusion.tex               # Summary of findings and concrete future work
├── figures/                         # Standalone TikZ vector figures
│   ├── methodology_flowchart.tex    # Complete pipeline architecture & evaluation flow
│   └── methodology_comparison.tex   # Taxonomy of information sources used by each approach
├── tables/                          # Professional LaTeX tables
│   ├── methodology_comparison.tex   # 16-dimension comparative analysis matrix (table*)
│   ├── main_results.tex             # Primary benchmark evaluation table on covered AL-CPL pairs
│   └── weighting_ablation.tex       # Edge ranking ablation comparison (NDCG@10, p-values)
├── artifact_inventory.md            # Complete provenance mapping of all repository artifacts
├── claim_traceability.md            # Empirical claim traceability matrix (Tier 1-4 audit)
├── final_review.md                  # Critical conference review report & submission checklist
└── README.md                        # Compilation instructions and project documentation (this file)
```

---

## 2. LaTeX Requirements and Dependencies

The manuscript is written in standard standard LaTeX2e using a neutral, double-blind conference layout (`10pt, twocolumn, a4paper`).

### Required LaTeX Packages
- **Layout & Typography:** `geometry`, `fontenc`, `inputenc`, `times`, `microtype`, `enumitem`, `xcolor`
- **Mathematics:** `amsmath`, `amssymb`
- **Tables:** `booktabs`, `tabularx`, `multirow`
- **Graphics:** `graphicx`, `tikz`
- **TikZ Libraries:** `arrows.meta`, `positioning`, `shapes.geometric`, `fit`, `calc`, `backgrounds`
- **Hyperlinks:** `hyperref`, `url`
- **Bibliography:** Standard `plain` or venue-specific BibTeX style

---

## 3. Compilation Instructions

To compile the LaTeX manuscript into a PDF on any standard TeX Live / MacTeX / MikTeX installation, execute:

```bash
cd paper_submission/

# Step 1: Initial pass to generate auxiliary files
pdflatex main.tex

# Step 2: Compile citations with BibTeX
bibtex main

# Step 3: Second pass to resolve cross-references and citations
pdflatex main.tex

# Step 4: Final pass to resolve table and TikZ positions
pdflatex main.tex
```

Or using `latexmk` for automated builds:

```bash
latexmk -pdf main.tex
```

*Note on Local Environment:* If compiling inside a minimal Docker or headless sandbox lacking `texlive-full`, install the compiler via `sudo apt-get install texlive-latex-extra texlive-fonts-recommended texlive-pictures` or compile on Overleaf by uploading the contents of `paper_submission/`.

---

## 4. Adapting to Specific Conference Templates

When the final submission target is selected:
1. **Springer LNCS (ESWC / ISWC):** Replace `\documentclass[10pt,twocolumn,a4paper]{article}` with `\documentclass{llncs}` in `main.tex`, switch `\bibliographystyle{plain}` to `\bibliographystyle{splncs04}`, and adjust author/affiliation blocks according to LNCS guidelines.
2. **ACM SIGCONF (EDM / L@S / KDD):** Replace documentclass with `\documentclass[sigconf,review,anonymous]{acmart}`.
3. **ACL / EMNLP / ARR:** Use `\documentclass[11pt]{article}` with `\usepackage{acl}`.

All tables, TikZ diagrams, and modular section files in `sections/` are fully compatible across all standard academic document classes.
