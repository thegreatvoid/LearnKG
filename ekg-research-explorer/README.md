# LearnKG Research Explorer & Interactive Documentation Platform

This is the complete, self-contained interactive research documentation website for the study:

> **Evaluating Local Large Language Models for Educational Prerequisite Extraction: The Surprising Dominance of Structural Reading-Order Priors**

Built with **React 19 + TypeScript + Vite + Lucide Icons**. Optimized for instant, static **Netlify Drag-and-Drop Deployment** with zero server or database dependencies.

---

## 1. Quick Netlify Drag-and-Drop Deployment (30 Seconds)

You do **NOT** need to install Node.js, run terminal commands, or set up environment variables on Netlify. The production build has already been generated and packaged for you.

### Option A: Drag the `dist/` Folder
1. Log in to [Netlify](https://app.netlify.com/).
2. Navigate to **Sites** &rarr; Scroll down to **"Want to deploy a new site without connecting to Git? Drag and drop your site output folder here"**.
3. Drag and drop the folder:
   ```text
   ekg-research-explorer/dist/
   ```
4. Your website is instantly live with an SSL certificate and custom Netlify URL!

### Option B: Upload the Pre-Built ZIP
1. Upload the ready-to-deploy zip archive:
   ```text
   ekg-research-explorer/dist-netlify.zip
   ```
2. Netlify will unpack and host the static files automatically.

*Note on Client-Side Routing:* The `dist/_redirects` file (`/* /index.html 200`) ensures that direct links and browser refreshes on sub-routes work seamlessly without 404 errors.

---

## 2. Running Locally

If you want to run or edit the website locally:

```bash
# Navigate to the project folder
cd ekg-research-explorer

# Start the local development server with Hot Module Replacement (HMR)
npm run dev

# Or preview the production build locally at http://localhost:4173
npm run preview
```

To rebuild the static output from source:
```bash
npm run build
```

---

## 3. Platform Architecture & Interactive Features

The platform provides a comprehensive reference across 7 major thematic tracks:

1. **Research Overview:**
   - **Research Home (`#home`):** Abstract, 5 core empirical discoveries, visual research flow blueprint, and evidence status legend.
   - **Problem & Motivation (`#motivation`):** First principles of Educational Knowledge Graphs (EKGs), Euclidean axiomatic ladder (Point &rarr; Proof), and why auto KG construction is hard.
   - **Research Questions (`#rqs`):** Complete, rigorous breakdowns of RQ1 to RQ5 with empirical evidence, confidence intervals, and justified conclusions.

2. **Corpus & Pipelines:**
   - **Dataset & Benchmark (`#dataset`):** Audit of CK-12 Basic Geometry (12 ch, 59 sec, 6,104 sentences), AL-CPL ground truth (89 concepts, 98 edges), 73% coverage ceiling, and the evaluation coverage funnel ($N=868$).
   - **Pipeline Architecture (`#pipelines`):** Interactive SVG flowchart with stage inspection (inputs, logic, outputs, source code, failure modes) for `rule_v3`, `kgx_v2`, and `kgx_v2_hybrid`.
   - **Local LLM Methodology (`#llm`):** Ollama `Qwen-2.5-7B`, structured JSON schema enforcement, and the empirical root cause of directional failure (expository textual symmetry).
   - **Structural Priors & Hybrid (`#priors`):** Textbook reading-order mechanics, positional gap $\Delta pos$, Saaty AHP, and transparent disclosure of curriculum benchmark circularity.

3. **EKG & Graph Theory:**
   - **EKG & 5 Relation Types (`#fundamentals`):** Formal graph theory axioms (DAGs, reachability, irreflexivity) and complete specifications of *Prerequisite*, *Part-of*, *Application*, *Extension*, and *Similarity*.
   - **Interactive Knowledge Graph (`#graph-explorer`):** Interactive SVG graph visualizer with relation type filter toggles, zoom/pan, prerequisite ancestor/descendant pathway highlighting, and node inspector drawer.
   - **Extraction & Bottlenecks (`#extraction`):** 130 glossary terms vs 204 LLM terms, definition validity rates, and the 3.1%–3.5% candidate generation bottleneck.

4. **Empirical Evaluation:**
   - **Evaluation Tutorial (`#evaluation`):** Formal mathematical definitions, step-by-step numerical examples, bootstrap 95% CIs ($B=1,000$), directional accuracy, and NDCG@10.
   - **Metric Calculator (`#calculator`):** Hands-on interactive sandbox where users adjust TP, FP, FN and observe live precision/recall trade-offs and transitive closure reachability.

5. **Experimental Results:**
   - **Results Dashboard (`#results`):** Interactive bar charts and comparative tables on the common covered pair set ($N=868$) comparing Random, `rule_v3`, `kgx_v2`, `kgx_v2_hybrid`, and Reading Order.
   - **Ablation Study Explorer (`#ablations`):** Feature component matrix, NDCG@10 query ranking comparisons, and paired permutation test significance ($p < 0.0001$ for Book Gap vs $p = 0.68$ for Co-occurrence vs AHP).
   - **Diagnostics & Error Analysis (`#diagnostics`):** Real failure cases, including the 43 ontological contradictions in unconstrained LLM graphs.

6. **Scientific Discussion:**
   - **Interpretation & Validity (`#discussion`):** 3-layer explanations (Beginner Intuition, Technical Interpretation, Scientific Caveat) and comprehensive internal, construct, and external threats to validity.
   - **Related Work (`#related-work`):** Verified bibliography (Liang, Alzetta, Chen, Roy, Carta, Trajanoska, Kommineni, Ji, Saaty, Hearst) and scholarly positioning matrix.
   - **Code Map & Reproducibility (`#implementation`):** File-by-file source code inventory and exact reproduction commands.

7. **Reference & Defense:**
   - **Searchable Glossary (`#glossary`):** 42 formal definitions with mathematical formulas, plain-English analogies, concrete geometry examples, and manuscript cross-references.
   - **Oral Presentation FAQ (`#faq`):** 20 curated defense questions with toggleable 30-second elevator pitches, deep technical defenses, key evidence coordinates, and pitfalls to avoid.

8. **Global Search Modal:**
   - Instant search across all sections, metrics, algorithms, glossary terms, and FAQs via **Cmd+K** or **Ctrl+K**.
