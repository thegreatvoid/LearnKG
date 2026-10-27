# Deliverable 6: Strategy Analysis: Internal vs. External Comparison

**Audit Date:** 2026-10-24  
**Project:** LearnKG Comparative Evaluation  
**Auditor:** Senior AI Researcher & Knowledge Graph Evaluation Specialist

---

## 1. Evaluation of Three Research Strategies

### Strategy A: Internal-Only Comparison (Existing Pipelines & Baselines)
* **Description:** The paper compares only the methodologies and baselines currently implemented in the repository: `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, Book Order, and the Saaty AHP weight ablations on CK-12 Geometry.
* **Scientific Value:** High forensic value. It directly answers whether local 7B LLMs provide any measurable value over zero-parameter structural priors and simple rules in educational KG construction.
* **Weaknesses & Reviewer Objections:**
  - Reviewers at ESWC/ISWC/ACL may dismiss the work as an "internal engineering post-mortem" or an ablation of custom code rather than a contribution to the broader field.
  - Skeptical reviewers will ask: *"Why compare a weak 7B LLM against your own rules instead of comparing against standard published prerequisite learners like RefD or cross-encoders?"*
* **When is it defensible?** If submitted as a **Short Empirical / Evaluation Paper (4–6 pages)** focused explicitly on: *"Do local LLMs learn prerequisites, or are they riding reading-order priors?"* In a short paper track, an internal audit with rigorous benchmarking on AL-CPL is fully acceptable and often praised for conciseness.

---

### Strategy B: Compare Best Methodology Against External Baselines
* **Description:** Select the best-performing pipeline (`kgx_v2_hybrid`) and compare it exclusively against published prerequisite learning models from the literature (e.g., Liang et al.'s RefD, Alzetta et al.'s linguistic classifier, or a standard BERT cross-encoder).
* **Scientific Value:** Traditional competitive benchmarking. Proves whether the proposed system beats the state-of-the-art.
* **Risks & Feasibility Hurdles:**
  1. **Incompatible Assumptions & Corpora:** Most external prerequisite methods (e.g., Liang et al., 2015; AAAI 2018) were designed for Wikipedia article networks where explicit hyperlink cross-references exist. An expository textbook does not contain hyperlinks; computing RefD requires adapting it to sentence co-occurrence (which our repository already did in `kg_extract/hybrid.py`).
  2. **Risk of Cross-Paper Number Copying:** Copying numbers directly from Liang et al. (2015) or Roy et al. (2019) would be scientifically fraudulent because they evaluated cross-validation splits over Wikipedia pages, whereas our evaluation tests extraction from a single coherent high-school textbook.
  3. **Lack of Multi-Relation Scope:** External baselines evaluate *only* binary prerequisites. They cannot evaluate *Part-of*, *Application*, *Extension*, or *Similarity*.

---

### Strategy C: Combined Internal & External Strategy (The Gold Standard)
* **Description:** 
  1. **Internal Component Comparison:** Compares `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, and `Book Order` under controlled Setting A ($N=868$) to dissect the failure modes of local LLMs and multi-criteria weighting.
  2. **External Baseline Integration:** Directly evaluates standardized, reproducible external baselines on the **exact same textbook text and AL-CPL pairs**:
     - **RefD (Reference Distance, Liang et al. 2015):** Already implemented in `kg_extract/hybrid.py` using sentence co-citation.
     - **Pretrained Cross-Encoder Baseline (MiniLM / BERT):** Pairwise semantic dependency classifier (already partially present in `educational_pipeline/neural_prerequisite_extractor.py`).
     - **Zero-Parameter Reading Order:** The canonical baseline from textbook instructional design literature (Alzetta et al., 2020).
* **Scientific Value:** Outstanding. It prevents the paper from looking like an insular project report while simultaneously grounding the findings in established NLP and Educational Data Mining literature.

---

## 2. Strategy Comparison Matrix

| Strategy | Main Objective | Strengths | Weaknesses | Additional Work Required | Scientific Credibility | Publication Potential | Recommendation |
|---|---|---|---|---|---|---|---|
| **Strategy A: Internal Only** | Compare existing `rule_v3`, `kgx_v2`, `hybrid`, and book order. | Zero additional coding; experiments are 100% complete, verified, and logged in `prerequisite_report.json`. | Risk of appearing as a private project audit; reviewers may demand external baselines. | Low (Drafting manuscript and packaging artifacts). | Moderate to High (if framed as a critical benchmark). | **Strong for Short Paper** (EDM / AIED / ESWC Evaluation Track). | **Recommended Fallback / Short Track.** |
| **Strategy B: External Only** | Pitch `kgx_v2_hybrid` against external SOTA prerequisite models. | Standard competitive narrative. | Masks the crucial scientific findings (the LLM's chance performance and the dominance of book order); ignores multi-relation ontology. | High (Re-implementing 2–3 external algorithms on CK-12 text). | Moderate (if external methods suffer under text adaptation). | Moderate (Vulnerable to circularity critique). | **Not Recommended.** |
| **Strategy C: Combined (Internal + Feasible External)** | Dissect internal pipeline components and compare against adapted RefD, Reading Order, and Pretrained Cross-Encoder. | **Maximum scientific rigor.** Explains *why* models fail internally and proves where the system stands relative to established literature baselines on identical data. | Requires consolidating the existing RefD and Cross-Encoder scripts into the unified benchmark table. | Low to Moderate (RefD is already computed in `hybrid.py`; cross-encoder exists in `evaluate_prerequisite_extraction.py`). | **Highest.** Reviewers cannot fault the baselines or the experimental controls. | **Strong for Full Conference Paper** (ESWC, ISWC, EDM, AIED). | **PRIMARY RECOMMENDATION.** |

---

## 3. Feasibility Audit of Specific External Baselines

1. **RefD (Reference Distance, Liang et al. 2015):**  
   - *Status:* **Fully Feasible & Already Available.**  
   - *Implementation:* In [kg_extract/hybrid.py](file:///home/dino/finyr/LearnKG/kg_extract/hybrid.py#L6-L10), sentence-level co-citation RefD is already computed across the entire corpus. It can be isolated and reported as an independent standalone baseline column in Table 1 with zero new inference needed.
2. **Textbook Reading Order (Alzetta et al. 2020):**  
   - *Status:* **Fully Feasible & Already Evaluated.**  
   - *Implementation:* Evaluated in `kg_eval.framework.prereq_eval` ($F_1 = 0.736$, AUC = $0.868$). Represents the strongest structural baseline in educational literature.
3. **Cross-Encoder / Sentence-Transformer Baseline:**  
   - *Status:* **Feasible with Minor Script Unification.**  
   - *Implementation:* Pretrained pairwise sentence-transformer scoring exists in `educational_pipeline/neural_prerequisite_extractor.py`.
