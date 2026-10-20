# Educational Knowledge Graph: Evaluation Report

**Project:** LearnKG / GAPGRAPH (latent prerequisite detection from a textbook)
**Test book:** CK-12 Basic Geometry (12 chapters, 59 sections)
**Status date:** 2026-10-15
**Scope:** everything evaluated so far, what it shows, what it cannot show, and what remains to be done.

Every number below comes from a generated output file (listed in section 10). Evidence types are labelled:

| Label | Meaning |
|---|---|
| **[GT]** | Measured against independent reference labels (here: AL-CPL prerequisite labels only) |
| **[AUTO]** | Automatic consistency or evidence checks; *not* accuracy |
| **[GROUND]** | Textual grounding (BIGS); *not* correctness |
| **[EXPL]** | Exploratory or descriptive |
| **[NOT DONE]** | Cannot be measured yet: labels or data are missing |

---

## 1. Summary

1. **Only the Prerequisite relation can be evaluated against ground truth.** The only independent reference dataset is AL-CPL geometry (prerequisite pairs). There is no annotated dataset for Part-of, Application, Similarity or Extension, so their precision, recall and F1 are **not computed**. They have automatic diagnostics only.
2. **The extracted prerequisite edges are near chance [GT].** Rule-based KG: ROC-AUC 0.513, recall 0.027. LLM KG (kgx_v2): AUC 0.503, recall 0.015.
3. **Textbook order is the dominant prerequisite signal [GT].** Book order alone scores F1 0.736, AUC 0.868, NDCG@10 0.891, and it puts the prerequisite first for 251 of 260 AL-CPL positives. The best graph (the v2 hybrid, closure F1 0.786) is built *from* book order, so its score is not independent evidence of extraction quality.
4. **The AHP edge weight carries some signal, almost all of it from co-occurrence [GT, prerequisite ranking only].** AHP NDCG@10 is 0.709 against 0.582 for random. Co-occurrence alone gets 0.723 and the raw co-occurrence count 0.742. The semantic-similarity (S) and chapter-proximity (P) factors score at about random level on their own. The weight is exactly symmetric, so it cannot judge edge direction, and it is unvalidated for the other four relation types.
5. **Concept coverage caps achievable recall [GT, partial].** 65 of 89 AL-CPL concepts are found. 43% of gold prerequisite pairs involve a missing concept, so recall can reach at most about 0.56. 13 of the 24 missing concepts do not occur in the book at all.
6. **Several pipeline bugs were found and fixed during evaluation** (section 5). Edge correctness barely changed.
7. **The intended application, question-level knowledge-gap detection, has not been evaluated [NOT DONE].** A concept-level proxy shows that following the rule-based or LLM graph's prerequisite edges finds few real prerequisites. Lower-bound P@5 is 0.07 and 0.05, against 0.46 for book order.
8. **Everything is from one textbook.** No result shows generalisation.

---

## 2. What was evaluated

### 2.1 Pipelines

| Pipeline | How it builds the graph | Notes |
|---|---|---|
| `educational_pipeline` (rule-based) | Regex and keyword concept and relation extraction, a neural prerequisite extractor, and the AHP edge weight `w = 0.52·S + 0.24·C + 0.09·P + 0.15·E` | Contains a hard-coded geometry vocabulary and 37 geometry regex rules: tuned to the test book |
| `kg_extract` (LLM) | Grounded concept extraction (headings, definitions, spaCy, LLM), candidate concept pairs, an LLM (qwen2.5:7b) that classifies each pair | Domain-agnostic; no hard-coded vocabulary |
| `kg_extract.hybrid` | Rebuilds Prerequisite edges from book order filtered by text relatedness; keeps the LLM's other relations | **Uses book order**, so direction checks against the same book are circular |

### 2.2 Graphs evaluated

| Name | Built by | Concepts | Edges (Prerequisite / Part-of / Application / Similarity / Extension) |
|---|---|---|---|
| rule_2026-10-11 | rule-based, before all fixes | 130 | 90 (34 / 6 / 2 / 46 / 2) |
| rule_v3 | rule-based, current code | 130 | 84 (27 / 7 / 2 / 46 / 2) |
| kgx_v2 | LLM pipeline | 204 | 545 (54 / 216 / 228 / 4 / 43) |
| kgx_v2_hybrid | v2 + hybrid prerequisites | 204 | 669 (518 / 71 / 63 / 1 / 16) |

The relation types are very unevenly represented in every graph. Any pooled "overall" score would be dominated by one type, so all results are reported per type.

### 2.3 Reference data

| Data | Used for | Independent? | Limitations |
|---|---|---|---|
| AL-CPL geometry (`geometry.pairs`, `geometry.preqs`) | Prerequisite **[GT]** | Yes: external annotators, Wikipedia concepts | 1,681 labelled pairs (524 positive); prerequisite only; its positives are already transitively closed; concept names are matched to the KG heuristically, including a hand-written geometry synonym map |
| AL-CPL concept list (89 concepts) | Concept coverage **[GT, partial]** | Yes | Lists only some of the book's concepts: gives recall of these 89, not precision |
| `gold_pairs.csv` (133 pairs) | Annotation pilot only | No | One author, no guideline, positives only, inconsistent direction convention; not used as ground truth |
| Part-of / Application / Similarity / Extension labels | — | — | **Do not exist [NOT DONE]** |
| Questions with expected prerequisites | — | — | **Do not exist [NOT DONE]** |

---

## 3. Methodology

### 3.1 Prerequisite correctness [GT]
- **Gold:** an AL-CPL pair "B is a prerequisite of A" is recovered by a KG Prerequisite edge B → A. Direction is strict.
- **Coverage:** a gold pair counts as *covered* only if both concepts match KG concepts. Uncovered pairs are reported as coverage loss, never as negatives.
- **Common set:** the main comparison uses the 868 pairs covered by **every** KG, so all methods are scored on identical pairs.
- **Unlabelled edges:** KG edges between concept pairs that AL-CPL never labelled are counted as *unknown*, not as false positives.
- **Metrics:** precision, recall and F1 for edges and for their transitive closure; ROC-AUC; per-query NDCG@5 and @10, P@5 and R@10 (ties broken randomly 20 times); direction accuracy.
- **Uncertainty:** 95% confidence intervals by bootstrap over query concepts; Wilson intervals for direction accuracy.
- **Baselines on the same pairs:** book order (B is first mentioned before A) and random.

### 3.2 Edge-weight evaluation [GT, prerequisite ranking only]
- **Setup:** for each AL-CPL query concept (58 queries), rank its labelled candidate concepts (892 pairs, 289 relevant). Every method ranks exactly the same candidates.
- **Methods:** AHP, each factor alone, AHP without each factor, 0.8·C + 0.2·E, the raw co-occurrence count, NPMI, book order, random, and coefficients learned by cross-validation (held-out folds only).
- **Statistics:** paired differences with bootstrap CIs and a sign-flip randomisation test.

### 3.3 Other relation types [AUTO]
Heuristic checks on every edge:
- **Support:** is there a book sentence mentioning both concepts?
- **Cue direction:** an independent cue lexicon, checked against the order of the two concepts in the sentence.
- **Structure:** reciprocal edges, cycles, and conflicts between relation types on the same pair.
- **Order:** book-order consistency.
- **Name and wording patterns:** the "kind of" name pattern and congruence wording.
- **Grounding:** per-edge distance to the nearest book sentence.

These are **diagnostics, not accuracy**.

### 3.4 Grounding [GROUND]
BIGS (Lermanda, Ojeda and Reutter, ESWC 2026), checked against the paper's equations:
- **BIGS→:** how well the triples cover the book's sentences.
- **BIGS←:** how close each triple is to some sentence.
- **Setup:** same corpus and embedder (`all-MiniLM-L6-v2`) for every graph, and size-matched subsets, because larger graphs trivially improve coverage.

### 3.5 Knowledge-gap proxy [GT, concept level]
- **Task:** for each AL-CPL target concept, rank all other KG concepts as candidate missing prerequisites.
- **Two views:** "judged only" removes candidates AL-CPL never labelled; "lower bound" counts them as not relevant.
- **Scope:** this is concept-level prerequisite ranking, **not** question-level gap detection.

---

## 4. Results

### 4.1 Concept extraction [GT, partial]

| Graph | Concepts | AL-CPL matched | AL-CPL positives touching a missing concept | Max reachable prerequisite recall | Valid definitions |
|---|---|---|---|---|---|
| rule_2026-10-11 | 130 | 65 / 89 | 229 / 524 | 0.563 | 47 / 130 |
| rule_v3 | 130 | 65 / 89 | 229 / 524 | 0.563 | 67 / 130 |
| kgx_v2 (= hybrid) | 204 | 65 / 89 | 227 / 524 | 0.567 | 70 / 204 |

The 24 missing AL-CPL concepts break down as:
- **13 absent from the book.** For example Hendecagon: a mismatch between the reference and this book, not an extraction error.
- **11 present in the book but not extracted.**

Specific terms that were investigated:

| Term | Where it occurs in the book | rule_v3 | kgx_v2 |
|---|---|---|---|
| SSS, SAS, ASA, AAS | Section headings only | Present | Dropped: occurs only in a heading, so its body frequency is 0 |
| HL | Section heading only | Dropped: acronyms shorter than 3 letters are filtered | Never proposed |
| Special Right Triangles | Heading only | Present (from the hard-coded list) | Dropped: heading only |
| Area | Body (22 mentions) | Present (from the hard-coded list) | Dropped: common-word filter |
| Similarity | Body | Present (from the hard-coded list) | Dropped: common-word filter |
| Sine | Body | Present (from the hard-coded list) | Dropped: top-k cut |

The rule-based graph's better coverage of these terms comes from its **hard-coded geometry list**, which will not transfer to another subject. Concept precision over the whole book is **[NOT DONE]**: it needs concept annotation.

### 4.2 Prerequisite correctness [GT]

Common set: 868 AL-CPL pairs covered by every graph.

| Graph / method | Edge P / R / F1 | Closure F1 [95% CI] | ROC-AUC [95% CI] | NDCG@5 / @10 | Direction correct / decided |
|---|---|---|---|---|---|
| rule_2026-10-11 | 0.778 / 0.027 / 0.052 | 0.052 [0.01, 0.10] | 0.512 [0.50, 0.52] | 0.539 / 0.630 | 7 / 8 |
| rule_v3 | 0.875 / 0.027 / 0.052 | 0.052 [0.01, 0.10] | 0.513 [0.50, 0.53] | 0.539 / 0.630 | 7 / 7 |
| kgx_v2 | 0.444 / 0.015 / 0.030 | 0.037 [0.01, 0.08] | 0.503 [0.49, 0.51] | 0.518 / 0.611 | 4 / 8 |
| kgx_v2_hybrid *(circular)* | 0.845 / 0.273 / 0.413 | **0.786** [0.76, 0.81] | **0.888** [0.85, 0.92] | 0.881 / 0.906 | 71 / 72 |
| Book order | 0.595 / 0.965 / 0.736 | — | 0.868 [0.81, 0.91] | 0.868 / 0.897 | 251 / 260 |
| Random | 0.300 / 0.500 / 0.375 (expected) | — | 0.500 | 0.511 / 0.607 | — |

What this shows:
- **Rule-based and LLM edges:** the few edges that exist are often right (precision 0.44–0.88), but they reach almost none of the gold pairs (recall ≤ 0.03), so the ranking is at chance.
- **The hybrid:** it is the best graph, but most of its signal is book order. Its gain over book order alone is small and was not established in the paired comparisons.
- **Direction:** the extracted edges decide direction for too few gold pairs (7–8) to judge.

### 4.3 Edge weights: AHP vs alternatives [GT, prerequisite ranking only]

Concept inventory rule_v3: 58 queries, 892 pairs, 289 relevant. kgx_v2 concepts give the same pattern.

| Method | NDCG@5 [CI] | NDCG@10 [CI] | P@5 | Δ NDCG@10 vs AHP [CI] | p |
|---|---|---|---|---|---|
| AHP (0.52S + 0.24C + 0.09P + 0.15E) | 0.621 [0.55, 0.69] | 0.709 [0.66, 0.77] | 0.453 | — | |
| C only (co-occurrence) | 0.666 | 0.723 | 0.485 | +0.014 [−0.02, +0.05] | 0.43 |
| 0.8·C + 0.2·E | 0.674 | 0.737 | 0.484 | +0.028 [−0.00, +0.06] | 0.11 |
| Raw co-occurrence count | 0.691 | 0.742 | 0.492 | +0.033 [+0.00, +0.07] | 0.05 |
| E only (section overlap) | 0.609 | 0.693 | 0.457 | −0.016 | 0.43 |
| NPMI (frequency-normalised) | 0.566 | 0.649 | 0.440 | −0.060 | 0.01 |
| S only (definition overlap) | 0.470 | 0.591 | 0.380 | −0.118 | <0.001 |
| P only (chapter proximity) | 0.491 | 0.608 | 0.376 | −0.101 | <0.001 |
| Random | 0.487 | 0.582 | 0.389 | −0.127 | <0.001 |
| *Book order (reference)* | *0.868* | *0.891* | *0.659* | *+0.182* | *<0.001* |

Findings:
- **AHP beats random.** Co-occurrence carries almost all of its signal: removing C is the only ablation that clearly hurts (−0.07 at NDCG@5, CI excluding 0).
- **S and P carry no signal on their own.** Correcting the concept definitions (section 5) did not change this: S alone went from 0.496 to 0.471, and the embedding-based variant from 0.560 to 0.518.
- **The coefficients are expert judgement** from an AHP pairwise matrix (consistency ratio 0.022). Internal consistency is not predictive validity, and the data put almost all weight on C. They are kept as the documented baseline. They are not replaced, because no independent validation set exists.
- **The weight is exactly symmetric** (w(A,B) = w(B,A) on all edges), so it cannot decide whether a directed edge points the right way.
- **Inside book order, C adds nothing.** Ranking forward candidates by C is not better than ranking them by book-order gap (−0.032 at NDCG@10, p = 0.09).
- **For the other four relation types the weight is unvalidated [NOT DONE].** Descriptively: AHP weight correlates with the number of supporting sentences (ρ = 0.85 for Part-of, 0.49 for Similarity), which only shows that the weight tracks co-occurrence.

### 4.4 Co-occurrence [EXPL]
- **Definition:** the number of sentences mentioning both concepts. C = min(1, n/3), with no frequency normalisation. Co-occurrence is *not* a relation type: it generates candidate pairs and feeds the C factor.
- **Most pairs never co-occur:** 628 of 892 candidate pairs have n = 0, and 74 saturate C.
- **Frequent concepts:** relevance correlates with candidate frequency (ρ = 0.47). Hub concepts (the 10% most frequent) are 14% of candidates but 34% of relevant ones (relevance rate 0.80 against 0.25 for others).
- **Reading:** foundational concepts are frequent and are genuinely more often prerequisites. Part of C's prerequisite signal is therefore concept frequency. NPMI, which removes it, ranks worse. This is a property of prerequisites in this book, not evidence that co-occurrence identifies any relation type.
- **Overlap with E:** ρ(C, E) = 0.78, so the section-overlap factor is largely redundant with C.

### 4.5 Other relation types: automatic diagnostics [AUTO], not accuracy

**rule_v3:**

| Type | Edges | With support sentence | Cue supports / reverse | Contradiction flags | Semantic/type flags |
|---|---|---|---|---|---|
| Prerequisite | 27 | 15 | 1 / 0 | 8 | 5 |
| Part-of | 7 | 7 | 2 / 2 | 2 | 0 |
| Application | 2 | 1 | 0 / 1 | 1 | 1 |
| Similarity | 46 | 15 | 15 / 0 | 0 | 43 |
| Extension | 2 | 2 | 0 / 0 | 1 | 1 |

**kgx_v2:**

| Type | Edges | With support sentence | Cue supports / reverse | Contradiction flags | Co-occurrence only |
|---|---|---|---|---|---|
| Prerequisite | 54 | 43 | 1 / 0 | 31 | 8 |
| Part-of | 216 | 147 | 36 / 27 | 27 | 18 |
| Application | 228 | 188 | 6 / 2 | 2 | 51 |
| Similarity | 4 | 3 | 3 / 0 | 0 | 0 |
| Extension | 43 | 36 | 0 / 0 | 20 | 13 |

Notable problems:
- **Similarity (rule-based):** 42 of 46 edges come from sentences containing "congruent to". The keyword extractor maps that phrase to Similarity, which confuses geometric congruence with conceptual similarity. 31 of the 46 have no sentence mentioning both concepts.
- **Prerequisite (LLM):** 31 of 54 edges point backward in the book.
- **Extension (LLM):** in 20 of 43 edges the base concept is introduced *after* the extension.
- **Part-of (LLM):** 18 edges match a "kind of" name pattern, for example *acute triangle → triangle* and *angle → inscribed angle*. Some are real type confusions, where a kind of X is stored as part of X. Others are false alarms, such as *area of a circle → circle*. Only annotation can separate them.
- **Application (LLM):** 51 edges are supported only by co-occurrence, with no relation cue in any supporting sentence.

A flag is a reason for review, not a verdict: no edge was deleted.

### 4.6 Textual grounding (BIGS) [GROUND]

| Graph | Triples | Full size: BIGS→ / BIGS← | Size-matched (10 triples): BIGS→ / BIGS← |
|---|---|---|---|
| rule_v3 | 84 | 0.466 / 0.287 | 0.603 / 0.289 |
| kgx_v2 | 545 | 0.283 / 0.279 | 0.596 / 0.278 |
| kgx_v2_hybrid | 669 | 0.294 / 0.309 | 0.597 / 0.311 |

Lower is better.
- **v2's full-size coverage advantage is graph size.** At equal size the graphs cover the text equally.
- **The hybrid's triples are the least grounded** (BIGS← 0.31), because its prerequisite edges come from book order, not from sentences that state them.
- **BIGS does not measure correctness or direction.** Per-relation-type values are in the framework report.

### 4.7 Concept-level knowledge-gap proxy [GT, concept level]

58 target concepts. "Lower bound" counts unlabelled candidates as non-relevant.

| Graph | Method | Lower-bound P@5 / R@10 / NDCG@10 | Judged-only P@5 / NDCG@10 |
|---|---|---|---|
| rule_v3 | **follow the KG's Prerequisite edges** | 0.073 / 0.120 / 0.123 | 0.394 / 0.598 |
| rule_v3 | book order | 0.455 / 0.621 / 0.480 | 0.659 / 0.889 |
| rule_v3 | AHP weight | 0.249 / 0.471 / 0.367 | 0.453 / 0.709 |
| rule_v3 | co-occurrence | 0.282 / 0.444 / 0.405 | 0.485 / 0.722 |
| rule_v3 | random | 0.056 / 0.066 / 0.065 | 0.389 / 0.577 |
| kgx_v2 | **follow the KG's Prerequisite edges** | 0.047 / 0.093 / 0.073 | 0.414 / 0.609 |
| kgx_v2_hybrid *(circular)* | follow the KG's Prerequisite edges | 0.389 / 0.651 / 0.557 | 0.679 / 0.876 |

What this means for the project goal:
- **The rule-based and LLM graphs** cannot yet be used for gap detection: their prerequisite edges reach few real prerequisites, close to random.
- **The hybrid graph** works much better, but because it is built from book order.
- **Learning-path validity** could only be measured for book-order paths and the hybrid. There it agrees with AL-CPL almost by construction, because AL-CPL prerequisites point forward in this book.

### 4.8 Earlier evaluations that were retired
- **LLM-as-judge with a 3B local model:** judged support (60% supported) and 1–5 "educational importance" ratings. The ratings collapsed (58 of 90 edges rated 4), giving weight–rating correlation ρ = 0.05. Retired: the ratings come from an LLM, not independent annotators, and showed almost no spread.
- **The original `evaluate_prerequisite_extraction.py`:** it counted reversed edges as correct, which inflated scores. Replaced by the strict-direction protocol above.

---

## 5. Defects found and fixed during evaluation

| Defect | Effect | Fix | Effect of the fix |
|---|---|---|---|
| Keyword path: Part-of / Application / Extension cues created **no edge** | Those relation types came only from hard-coded rules | Direction taken from the sentence; passive cues reversed; skipped when no direction is stated | +1 edge (Ray → Line, Part-of); prerequisite results unchanged |
| Keyword path: each Similarity sentence proposed **twice**; substring matching ("like" in "unlike") | Inflated co-occurrence counts | One proposal per sentence; whole-word matching | Proposals per Similarity edge 3.24 → 1.61 |
| Weight factor C counted *proposals*, not text | Rule firings inflated the weight | C counts sentences mentioning both concepts | Weight now reproducible from the text |
| Neural extractor scores **replaced** the formula; LLM 1–10 scores silently dropped | Weights not comparable across sources | All edges get the formula weight; extractor scores stored separately | Documented in `docs/ahp_weights.md` |
| Definition assignment: "longest sentence wins"; mid-sentence "X is" matches; rewritten text ("Polygon is lways 360 degrees") | Most concepts had wrong definitions, so S was computed on wrong text | Only defining sentences with the concept as subject; first definition kept; mentions kept as evidence only | Valid definitions 43 → 67 of 130; prerequisite precision 0.636 → 0.700; S still uninformative |
| Concept candidates iterated as a set | Concept IDs and names changed between runs | Sorted | Outputs identical across runs |
| Chapter and section labels (fixed in an earlier commit by the team) | Chapter proximity always 1.0; sections never detected | Parser fix | P and E now vary |

Regression tests cover every fix: 13 + 16 pipeline tests, 10 `kg_extract` tests, and 13 framework tests, all passing.

---

## 6. What the evidence supports

**Supported [GT]:**
- Book order is the strongest prerequisite signal in this textbook, for both existence and direction.
- The rule-based and LLM pipelines' own prerequisite edges are near chance on AL-CPL.
- The AHP weight ranks AL-CPL prerequisites above random, mainly through co-occurrence; S and P add nothing measurable.
- Concept coverage, not only relation extraction, limits prerequisite recall (at most about 0.56).

**Not supported (do not claim):**
- Any accuracy for Part-of, Application, Similarity or Extension.
- That the AHP weight measures "educational relevance", or that it is valid for any type other than Prerequisite.
- That any weight shows a directed edge is correct.
- That the system detects a learner's missing knowledge from a question.
- That results generalise beyond this textbook.

---

## 7. Limitations
- **One textbook, one subject.**
- **Only one relation type has independent labels.**
- **AL-CPL limits:** its concept names are Wikipedia titles, matched to the KG heuristically with a hand-written geometry synonym map. Its positives are already transitively closed, so a "closure" evaluation adds nothing.
- **AL-CPL is not perfectly matched to the book:** 13 of its 89 concepts do not occur in it.
- **Tuned to the test book:** the rule-based pipeline is tuned to this book (hard-coded vocabulary and rules), and the `kg_extract` hub setting was chosen while looking at geometry gold.
- **The 0.8·C + 0.2·E variant was suggested by this same data,** so its score here is optimistic.
- **The automatic diagnostics use heuristic cue lists.** For rule-based keyword edges the cue check is not independent of the extractor.
- **The prerequisite-ranking candidate sets come from AL-CPL's labelled pairs,** not from the whole graph.

---

## 8. Next steps

Ordered by priority. Each step says what it needs.

### A. Get labels for the other four relation types (needs 2 annotators)
1. **Use the prepared kit:** `data_output/eval_framework/annotation/`. It contains 378 blind items: predicted edges (40 per type), 60 hard negatives (concept pairs mentioned in the same sentence that no KG relates), the 133 pilot pairs re-annotated, and 19 AL-CPL calibration pairs.
2. **Guidelines:** `kg_eval/framework/ANNOTATION_GUIDELINES.md`, with definitions, direction conventions, and positive, negative and ambiguous cases for each relation.
3. **Annotate independently:** two annotators, then `annotation_kit agreement A.csv B.csv` (Cohen's κ; target ≥ 0.6, revise the guidelines on a practice set if lower).
4. **Adjudicate** disagreements and record the result in an adjudicated file.
5. **Evaluate:** `annotation_kit evaluate adjudicated.csv` gives per-type TP, FP, FN, precision, recall and F1 with Wilson CIs, plus direction errors, on the annotated sample.
6. **Estimated effort:** about 6–8 hours per annotator.

### B. Concept precision and recall (needs 1–2 annotators, ~2 hours)
7. **Annotate** the 8 sampled sections in `annotation/concepts/`: mark each proposed term as concept or not, and add concepts that every KG missed.

### C. Question-level knowledge-gap evaluation (needs a subject expert)
8. **Write the question set:** 30–50 textbook-level questions in `annotation/questions/questions_TEMPLATE.csv`. For each, list the target concept and the prerequisite concepts **independently of the KG**, with the reference source.
9. **Build a question-level evaluator:** map each question to concepts and score the graph's suggested missing prerequisites with P@k, R@k and NDCG@k, against book order and co-occurrence baselines. This is code still to write once the questions exist.

### D. Fix the pipeline problems found (code only; re-evaluate afterwards)
10. **Concept recall:**
    - Keep section-heading terms (SSS, SAS, ASA, AAS, HL, Special Right Triangles).
    - Allow 2-letter acronyms when they are defined or appear in a heading.
    - Stop the common-word filter dropping frequent domain words (Area, Similarity).
11. **Similarity:** stop mapping "congruent to" to Similarity.
12. **Relation types:** route "kind of" pairs to Extension instead of Part-of.
13. **LLM pair prompt:** it gets direction wrong. Either give it where each concept is introduced, or use the LLM only for relatedness and relation type and take direction from another source.
14. **Freeze the hybrid as the prerequisite method** and decide how to present it: "book order filtered by relatedness".
15. **Weight:** keep AHP as the baseline. Report co-occurrence-only as the simplest supported alternative. Decide between them only on the second domain (below), and don't re-tune on geometry.

### E. Generalisation (needs data, then the steps above)
16. **Commit, then freeze:** commit the code and run `python -m kg_eval.freeze_manifest --write` **before** obtaining any second-domain data.
17. **Choose the subject:** AL-CPL physics or precalculus, with an OpenStax textbook, following `kg_eval/second_domain_protocol.md`.
18. **Run the same framework:** report each textbook and each relation type separately. Check direction against a *second* textbook's order, not the order used to build the graph.

### F. Housekeeping
19. **Commit the work:** everything from these sessions is uncommitted.
20. **Refresh the docs:** regenerate the step dump and pipeline figures (`docs/educational_pipeline_*`), which predate the fixes.

**What can be done right now without people:** steps D10–D15, then re-run the framework (`python -m kg_eval.framework.run_all`) to measure their effect on the prerequisite and concept results. Steps A–C need annotators or a subject expert. Step E needs the code frozen first.

---

## 9. Reproduction

```
# tests
python educational_pipeline/test_keyword_path.py
python educational_pipeline/test_definitions_and_weights.py
python kg_extract/test_kg_extract.py
python kg_eval/framework/test_framework.py

# rebuild the current rule-based graph
python -c "from educational_pipeline import run_educational_pipeline as r; r(data_dir='ck12_geometry', output_base_dir='./data_output/baseline_v3', use_llm=False, embedding_similarity=True, output_html='./docs/ck12_geometry_v3.html')"

# full evaluation framework (about 4 minutes; outputs are byte-identical on rerun)
python -m kg_eval.framework.run_all
```

## 10. Where the numbers come from

| Section | File |
|---|---|
| Framework report (all tables, auto-generated) | `data_output/eval_framework/REPORT.md` |
| 4.1 Concepts | `data_output/eval_framework/concepts/concepts_report.json`, `missing_alcpl_concepts.csv` |
| 4.2 Prerequisite | `data_output/eval_framework/prerequisite/prerequisite_report.json`, `pairs_<kg>.csv` |
| 4.3–4.4 Weights, co-occurrence | `data_output/eval_framework/weights/weights_report.json` |
| 4.5 Relation diagnostics | `data_output/eval_framework/relations/relation_checks_report.json`, `edge_checks_<kg>.csv` |
| 4.6 BIGS | `data_output/eval_framework/bigs/bigs_by_relation.json`, `data_output/bigs_compare.json` |
| 4.7 Gap proxy | `data_output/eval_framework/gap_proxy/gap_proxy_report.json` |
| 5 Fixes, before/after | `kg_eval/README.md` sections 5.10–5.11 |
| Weight formula and factors | `docs/ahp_weights.md` |
| Annotation package | `data_output/eval_framework/annotation/`, `kg_eval/framework/ANNOTATION_GUIDELINES.md` |
