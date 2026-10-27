# Deliverable 10: Ten-Point Action Plan for Publication

**Audit Date:** 2026-10-24  
**Project:** LearnKG Submission Execution Plan  
**Auditor:** Senior AI Researcher & Academic Publication Strategist

---

## The Ten Prioritized Actions

| Priority | Action Item | Detailed Objective & Implementation Task | Expected Output Artifact | Completion Verification Criteria |
|---|---|---|---|---|
| **1** | **Freeze Empirical Core & Re-run Tests** | Execute `test_framework.py` and `test_kg_extract.py` to ensure regression hygiene. Verify all numbers in `prerequisite_report.json` and `weights_report.json`. | Clean terminal test logs with status `OK`. | `python3 kg_eval/framework/test_framework.py` exits with 0 errors. |
| **2** | **Update Terminology in LaTeX Draft** | Replace all instances of "student knowledge gap detection" with *"Prerequisite Retrieval as a Structural Proxy for Curricular Tracing"* in `paper_conference_revision.tex`. | Revised LaTeX manuscript lines in Abstract, Intro, and Section 8. | `grep -i "student knowledge gap" paper_conference_revision.tex` returns 0 hits. |
| **3** | **Enforce Hybrid Circularity Transparency** | Ensure that Table 1 in the manuscript contains the explicit footnote: *"The hybrid pipeline incorporates book order in its forward gate (`uses_book_order: true`); its directional accuracy cannot be evaluated as an independent finding."* | Formatted footnote in LaTeX table. | Clear visual caveat present on Table 1 in compiled PDF. |
| **4** | **Add Standalone RefD Baseline Column** | Extract sentence-level RefD (Liang et al., 2015) computed in `kg_extract/hybrid.py` and add it as an explicit comparative baseline column in the main results table. | RefD ROC-AUC and $F_1$ row added to Table 1. | Directly compares our structural baselines against the standard external metric on identical pairs. |
| **5** | **Demarcate Pending Experiments Honestly** | Verify that Section 7 (*Limitations and Threats to Validity*) explicitly lists Multi-Model Scaling (3B/14B) and Cross-Domain Physics replication as frozen protocols / future work, rather than missing data. | Explicit subsections in LaTeX draft under Limitations. | Zero `[TODO]` placeholders in the compiled PDF. |
| **6** | **Generate High-Resolution Vector Figures** | Compile the pipeline architecture diagram and the recall bottleneck cascade bar chart into clean `.pdf` or `.png` vector assets. | `docs/figures/pipeline_cascade.pdf` and `docs/figures/roc_curves.pdf`. | Figures render crisply at 300+ DPI in two-column format. |
| **7** | **Validate LaTeX Compilation** | Run `pdflatex` or `latexmk` on `paper_conference_revision.tex` to ensure zero compilation warnings, missing citations, or broken reference links. | Compiled two-column conference draft PDF (`paper_conference_revision.pdf`). | Clean PDF generated with correct page count (within 6 pages for Short Track). |
| **8** | **Package Open Reproducibility Artifacts** | Verify that `REPRODUCING.md` contains the single-line command: `python3 -m kg_eval.framework.run_all --out data_output/eval_framework` and that all dependencies are listed in `requirements.txt`. | Self-contained, working reproduction bundle. | Execution on a fresh environment successfully regenerates all JSON artifacts. |
| **9** | **Select Target Venue & Finalize Deadlines** | Cross-reference conference call-for-papers (EDM, AIED, ESWC, ISWC Resources Track, or ACL Evaluation Track) and format the manuscript using the official conference style file. | Venue-specific LaTeX template (ACM / Springer LNCS / ACL style). | Abstract and page limit conform to exact venue specifications. |
| **10** | **Final Peer & Blind Review Pass** | Conduct a full blinded read-through using the criteria from `DELIVERABLE_8_CONFERENCE_REVIEWER_ASSESSMENT.md` to ensure zero promotional hyperbole and complete objectivity. | Polished, anonymized camera-ready review submission draft. | Full compliance with double-blind review guidelines. |
