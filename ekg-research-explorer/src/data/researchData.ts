export interface MetricResult {
  method: string;
  category: 'Pipeline' | 'Baseline' | 'Hybrid';
  candidateRecall: number | string;
  precision: number | string;
  recall: number | string;
  edgeF1: number | string;
  closureF1: number | string;
  closureF1CI?: string;
  rocAuc: number | string;
  rocAucCI?: string;
  dirAcc: string;
  dirAccPct: number;
  ndcg10: number | string;
  status: 'Verified from source' | 'Reported in manuscript' | 'Baseline Reference';
  notes: string;
}

export interface AblationResult {
  name: string;
  formulaOrFeature: string;
  ndcg10: number;
  ci: string;
  pValueVsAHP: string;
  interpretation: string;
  status: string;
}

export interface ConceptNode {
  id: string;
  name: string;
  chapter: number;
  section: string;
  chapterName: string;
  definition: string;
  matchedALCPL: boolean;
  alCplName?: string;
}

export interface RelationEdge {
  source: string;
  target: string;
  type: 'prerequisite' | 'part_of' | 'application' | 'extension' | 'similarity';
  isDirected: boolean;
  pipeline: 'rule_v3' | 'kgx_v2' | 'kgx_v2_hybrid' | 'ground_truth';
  evidence?: string;
}

export interface GlossaryEntry {
  term: string;
  category: 'Foundations' | 'Extraction' | 'Graph Theory' | 'Evaluation' | 'Priors & Ablation';
  plainDef: string;
  technicalDef: string;
  formula?: string;
  example: string;
  appearsIn: string;
}

export interface FAQItem {
  id: string;
  question: string;
  category: 'Motivation' | 'Baselines' | 'LLM Performance' | 'Hybrid & Circularity' | 'Evaluation' | 'Defense' | 'Priors & Ablation';
  quickAnswer: string;
  deepAnswer: string;
  keyMetric: string;
  pitfallToAvoid: string;
}

export interface RQItem {
  id: string;
  title: string;
  question: string;
  motivation: string;
  pipelineOrBaseline: string;
  evalMethod: string;
  reportedEvidence: string;
  result: string;
  interpretation: string;
  limitations: string;
  justifiedConclusion: string;
}

export interface PipelineStage {
  id: string;
  name: string;
  pipeline: 'All' | 'rule_v3' | 'kgx_v2' | 'kgx_v2_hybrid';
  purpose: string;
  inputs: string[];
  outputs: string[];
  logic: string;
  sourceFiles: string[];
  failureModes: string[];
  evalRelevance: string;
}

// -------------------------------------------------------------
// RESEARCH METADATA
// -------------------------------------------------------------
export const PROJECT_META = {
  title: "Evaluating Local Large Language Models for Educational Prerequisite Extraction: The Surprising Dominance of Structural Reading-Order Priors",
  shortTitle: "LearnKG Comparative Evaluation Study",
  authors: "Anonymous Authors (Double-Blind Conference Submission)",
  manuscriptFile: "paper_submission/main.tex",
  corpusName: "CK-12 Basic Geometry Second Edition",
  corpusStats: {
    chapters: 12,
    sections: 59,
    sentences: 6104,
    tokens: 126450,
    license: "Creative Commons Attribution-NonCommercial 3.0 Unported (CC BY-NC 3.0)"
  },
  benchmarkName: "AL-CPL Geometry (Liang et al., 2015 / 2018)",
  benchmarkStats: {
    concepts: 89,
    prerequisiteEdges: 98,
    totalLabeledPairs: 1681,
    coveredCommonPairs: 868,
    positiveCoveredPairs: 260,
    negativeCoveredPairs: 608
  },
  abstract: "Automated construction of Educational Knowledge Graphs (EKGs) requires identifying directed prerequisite relationships between concepts. While recent literature promotes Large Language Models (LLMs) as zero-shot relation extractors, their effectiveness under resource-constrained, local deployment remains poorly understood. In this work, we conduct a controlled empirical evaluation of rule-based, local open-weight LLM (Qwen-2.5-7B), and neuro-symbolic hybrid pipelines against the AL-CPL geometry benchmark. Our findings reveal that an unconstrained local LLM operates at chance (ROC-AUC = 0.503, directional accuracy = 50.0%) when inferring prerequisites from textbook definitions due to expository textual symmetry. Conversely, a zero-parameter textbook reading-order baseline achieves an ROC-AUC of 0.868 and 96.5% directional accuracy. While a hybrid pipeline yields high transitive closure F1 (0.786) and ROC-AUC (0.888), ablation reveals that this performance is overwhelmingly driven by the structural reading-order prior (+0.368 AUC), with the LLM acting solely as an undirected semantic pruning filter (+0.020 AUC). We deconstruct the candidate-generation bottleneck and show via feature ablation that multi-criteria Analytic Hierarchy Process (AHP) weighting is redundant when simple co-occurrence is available.",
  keyFindings: [
    {
      title: "Local LLM Operates at Chance on Directionality",
      stat: "ROC-AUC: 0.503 | Dir Acc: 50.0%",
      detail: "The 7B parameter local model (Qwen-2.5-7B) achieves an ROC-AUC of 0.503 [95% CI: 0.49, 0.51] and exactly 4/8 correct directional assignments. Expository definitions present properties symmetrically, depriving the model of asymmetric linguistic signals."
    },
    {
      title: "Reading Order is a Dominant Structural Prior",
      stat: "ROC-AUC: 0.868 | Dir Acc: 96.5%",
      detail: "A zero-parameter baseline using strictly linear concept appearance (pos(u) < pos(v)) correctly orients 251/260 positive prerequisite pairs, outperforming complex neural classifiers in direction assignment."
    },
    {
      title: "Hybrid Gains Are Structurally Driven",
      stat: "Closure F1: 0.786 | Marginal LLM AUC: +0.020",
      detail: "The hybrid pipeline's high closure F1 is caused by enforcing reading order. The LLM's true contribution is not directional reasoning, but pruning early false-positive candidates, boosting precision from 0.595 to 0.845."
    },
    {
      title: "Multi-Criteria AHP Weighting is Redundant",
      stat: "AHP: 0.709 vs Co-occ: 0.723",
      detail: "In edge-weighting ablations, the 4-factor Saaty AHP composite is statistically indistinguishable (p=0.68) from simple co-occurrence. Lexical definition overlap (weighted at 52% in AHP) scores 0.589, near random noise."
    },
    {
      title: "Candidate Generation is the Primary Bottleneck",
      stat: "Candidate Recall: 3.1% to 3.5%",
      detail: "End-to-end prerequisite recall collapses (0.015 - 0.027) primarily because candidate-pair filtering discards over 96% of ground-truth relations before relation classification even occurs."
    }
  ]
};

// -------------------------------------------------------------
// RESEARCH QUESTIONS
// -------------------------------------------------------------
export const RESEARCH_QUESTIONS: RQItem[] = [
  {
    id: "RQ1",
    title: "Concept Extraction Coverage & Benchmark Alignment",
    question: "To what extent can symbolic rule-based and local LLM pipelines discover core curriculum concepts from introductory geometry, and how well do they align with established educational benchmarks?",
    motivation: "A knowledge graph is structurally bounded by its nodes. If core concepts are missing, downstream prerequisite relations cannot be evaluated or retrieved.",
    pipelineOrBaseline: "rule_v3 (handcrafted regex/glossary) vs kgx_v2 (local Qwen-2.5-7B)",
    evalMethod: "Concept count, definition validity check, fuzzy string matching (Levenshtein >= 0.85 + synonym table) against AL-CPL.",
    reportedEvidence: "rule_v3 extracted 130 concepts (67 valid defs, 65/89 AL-CPL matches = 73.0%). kgx_v2 extracted 204 concepts (70 valid defs, 65/89 AL-CPL matches = 73.0%).",
    result: "Both systems plateau at 73.0% concept recall against the benchmark. 24 benchmark concepts never appear verbatim in the CK-12 textbook.",
    interpretation: "Local LLMs expand vocabulary volume (+57% terms) but capture noisy compound phrases without improving benchmark alignment. External textbook variations create an inescapable 73% upper bound on concept coverage.",
    limitations: "Single geometry textbook; synonym table semi-manually constructed.",
    justifiedConclusion: "LLMs increase concept yield but fail to surpass rule-based systems in benchmark recall when evaluated against standardized curriculum ontologies."
  },
  {
    id: "RQ2",
    title: "Unconstrained Local LLM Prerequisite Extraction Quality",
    question: "Can an open-weight 7B parameter LLM deployed locally reliably extract directed prerequisite relations using structured zero-shot prompting on textbook snippets?",
    motivation: "Literature frequently claims LLMs possess emergent zero-shot relation extraction abilities. We test this under realistic privacy-preserving local deployment.",
    pipelineOrBaseline: "kgx_v2 (Ollama Qwen-2.5-7B, structured JSON schema)",
    evalMethod: "AL-CPL common covered set (N=868). Edge F1, Transitive Closure F1, ROC-AUC with 1000-sample bootstrap 95% CIs, Directional Accuracy.",
    reportedEvidence: "Edge F1 = 0.030, Closure F1 = 0.037 [0.01, 0.08], ROC-AUC = 0.503 [0.49, 0.51], Directional Accuracy = 4/8 (50.0%).",
    result: "Performance is statistically indistinguishable from random guessing (AUC 0.500 inside CI). Directional accuracy is exactly 50%.",
    interpretation: "Textbook definitions are expository and symmetrical (e.g., 'An angle is formed by two rays'). Without explicit directional markers, the 7B LLM cannot infer pedagogical order.",
    limitations: "Evaluated zero-shot with one model size (7B); prompt variations tested but not fine-tuned.",
    justifiedConclusion: "Unconstrained local LLMs cannot reliably classify prerequisite dependency or orientation from isolated text definitions alone."
  },
  {
    id: "RQ3",
    title: "Efficacy of the Structural Reading-Order Prior",
    question: "How does a zero-parameter structural baseline based purely on textbook linear reading order compare against semantic extraction pipelines?",
    motivation: "Educational textbooks are intentionally curated in pedagogical sequence. We must isolate this structural prior before attributing performance to model intelligence.",
    pipelineOrBaseline: "Book-Order Baseline: assigns directed edge u -> v iff pos(u) < pos(v)",
    evalMethod: "Evaluated on identical AL-CPL covered pairs (N=868). Edge F1, ROC-AUC, Directional Accuracy.",
    reportedEvidence: "Edge F1 = 0.736, ROC-AUC = 0.868 [0.81, 0.91], Directional Accuracy = 251/260 (96.5%).",
    result: "Reading order dramatically outperforms standalone LLMs and rule-based pipelines across all topological and directional metrics.",
    interpretation: "Pedagogical linearity is an immense structural prior. In formal geometry, authors almost never introduce dependent theorems before foundational primitives.",
    limitations: "Produces false-positive edges between unrelated concepts appearing far apart; applies strictly to sequential curriculum books.",
    justifiedConclusion: "Textbook reading order is a dominant baseline that must be controlled for in any educational knowledge graph evaluation."
  },
  {
    id: "RQ4",
    title: "De-confounding Neuro-Symbolic Hybrid Architecture",
    question: "Does the neuro-symbolic hybrid pipeline genuinely combine neural semantics with symbolic structure, and what is the marginal contribution of the LLM?",
    motivation: "Hybrid pipelines often report state-of-the-art numbers without ablating the structural component.",
    pipelineOrBaseline: "kgx_v2_hybrid (LLM semantic relatedness + book order forward gating)",
    evalMethod: "Ablation of gating constraint; comparison against reading-order baseline alone.",
    reportedEvidence: "Closure F1 = 0.786 [0.76, 0.81], ROC-AUC = 0.888 [0.85, 0.92], Precision = 0.845. Marginal AUC gain over pure book order = +0.020.",
    result: "The hybrid achieves top closure F1 and precision, but 97.7% of its AUC is provided by the reading-order prior.",
    interpretation: "The LLM acts as an undirected pruning filter that discards irrelevant early pairs, boosting precision from 0.595 to 0.845. It does not perform directional dependency inference.",
    limitations: "Circularity risk: using textbook order ensures high benchmark alignment because curriculum benchmarks also mirror textbook sequences.",
    justifiedConclusion: "Hybrid success is driven by structural gating; the LLM's role is restricted to semantic candidate filtering rather than prerequisite reasoning."
  },
  {
    id: "RQ5",
    title: "Feature Redundancy in Analytic Hierarchy Process (AHP) Weighting",
    question: "Does multi-criteria decision-making weighting (Saaty AHP) provide superior edge ranking compared to individual distributional and structural features?",
    motivation: "Rule-based pipelines often introduce complex multi-criteria weighting without proving that the combination beats simple co-occurrence.",
    pipelineOrBaseline: "Saaty AHP composite (W = 0.52S + 0.24C + 0.09P + 0.15E) vs individual ablations (S, C, P, E, Raw Count, Book Gap)",
    evalMethod: "NDCG@10 ranking quality against AL-CPL target queries; paired permutation tests (10,000 resamples).",
    reportedEvidence: "AHP NDCG@10 = 0.709; Co-occurrence C = 0.723 (p=0.68, ns); Raw Cooc Count = 0.742; Definition Overlap S = 0.589 (p<0.001); Book Gap = 0.891 (p<0.0001).",
    result: "AHP is statistically indistinguishable from co-occurrence alone. Definition overlap (given 52% weight) performs near random noise.",
    interpretation: "Complex multi-criteria formulas add conceptual overhead without empirical benefit. Co-occurrence carries the entire predictive signal, while structural position dominates.",
    limitations: "Evaluated on CK-12 geometry text; definition length variation affects Jaccard overlap.",
    justifiedConclusion: "AHP multi-factor weighting is redundant in educational KG construction; simpler distributional and positional metrics are more effective."
  }
];

// -------------------------------------------------------------
// MAIN BENCHMARK RESULTS TABLE
// -------------------------------------------------------------
export const BENCHMARK_RESULTS: MetricResult[] = [
  {
    method: "Uniform Random Guessing",
    category: "Baseline",
    candidateRecall: "N/A",
    precision: 0.300,
    recall: 0.500,
    edgeF1: 0.375,
    closureF1: "N/A",
    rocAuc: 0.500,
    rocAucCI: "Theoretical",
    dirAcc: "130/260",
    dirAccPct: 50.0,
    ndcg10: 0.582,
    status: "Baseline Reference",
    notes: "Expected performance of an unweighted coin toss on AL-CPL common covered pairs."
  },
  {
    method: "rule_v3 (Symbolic Rules & AHP)",
    category: "Pipeline",
    candidateRecall: 0.031,
    precision: 0.875,
    recall: 0.027,
    edgeF1: 0.052,
    closureF1: 0.052,
    closureF1CI: "[0.01, 0.10]",
    rocAuc: 0.513,
    rocAucCI: "[0.50, 0.53]",
    dirAcc: "7/7",
    dirAccPct: 100.0,
    ndcg10: 0.630,
    status: "Verified from source",
    notes: "Handcrafted 130-term glossary, regex linguistic connectives, Saaty AHP. High precision, catastrophic recall bottleneck."
  },
  {
    method: "kgx_v2 (Local Qwen-2.5-7B)",
    category: "Pipeline",
    candidateRecall: 0.035,
    precision: 0.444,
    recall: 0.015,
    edgeF1: 0.030,
    closureF1: 0.037,
    closureF1CI: "[0.01, 0.08]",
    rocAuc: 0.503,
    rocAucCI: "[0.49, 0.51]",
    dirAcc: "4/8",
    dirAccPct: 50.0,
    ndcg10: 0.611,
    status: "Verified from source",
    notes: "Zero-shot Ollama inference on sentence definitions. Operates at chance due to definition symmetry; 50% directional accuracy."
  },
  {
    method: "kgx_v2_hybrid (Neuro-Symbolic)",
    category: "Hybrid",
    candidateRecall: 0.323,
    precision: 0.845,
    recall: 0.273,
    edgeF1: 0.413,
    closureF1: 0.786,
    closureF1CI: "[0.76, 0.81]",
    rocAuc: 0.888,
    rocAucCI: "[0.85, 0.92]",
    dirAcc: "71/72",
    dirAccPct: 98.6,
    ndcg10: 0.906,
    status: "Verified from source",
    notes: "Combines LLM relatedness with reading-order forward gate (pos(u) < pos(v)). Dominant performance driven by structural prior."
  },
  {
    method: "Textbook Reading-Order Baseline",
    category: "Baseline",
    candidateRecall: 1.000,
    precision: 0.595,
    recall: 0.965,
    edgeF1: 0.736,
    closureF1: "Not reported",
    rocAuc: 0.868,
    rocAucCI: "[0.81, 0.91]",
    dirAcc: "251/260",
    dirAccPct: 96.5,
    ndcg10: 0.897,
    status: "Verified from source",
    notes: "Deterministic heuristic: concept u precedes v in textbook. Demonstrates immense predictive power of pedagogical curriculum sequence."
  }
];

// -------------------------------------------------------------
// WEIGHTING ABLATION STUDY RESULTS
// -------------------------------------------------------------
export const ABLATION_RESULTS: AblationResult[] = [
  {
    name: "Book Position Gap",
    formulaOrFeature: "Δpos = pos(v) - pos(u) (Normalized linear position difference)",
    ndcg10: 0.891,
    ci: "[0.85, 0.93]",
    pValueVsAHP: "p < 0.0001 (Highly Significant)",
    interpretation: "Structural progression dominates all textual and distributional features in ranking prerequisite relevance.",
    status: "Verified from source"
  },
  {
    name: "Raw Co-occurrence Count",
    formulaOrFeature: "Count of shared sentences across all textbook chapters",
    ndcg10: 0.742,
    ci: "[0.68, 0.79]",
    pValueVsAHP: "p = 0.31 (Not Significant)",
    interpretation: "Unnormalized frequency performs as well as, or slightly better than, complex normalized metrics.",
    status: "Verified from source"
  },
  {
    name: "Sentence Co-occurrence (C)",
    formulaOrFeature: "Normalized co-occurrence score within sentence boundaries",
    ndcg10: 0.723,
    ci: "[0.67, 0.77]",
    pValueVsAHP: "p = 0.68 (Not Significant)",
    interpretation: "Statistically indistinguishable from the composite AHP formula, carrying the entire valid textual signal.",
    status: "Verified from source"
  },
  {
    name: "Saaty AHP Composite (Baseline)",
    formulaOrFeature: "W = 0.52S + 0.24C + 0.09P + 0.15E (Consistency Ratio = 0.022)",
    ndcg10: 0.709,
    ci: "[0.65, 0.76]",
    pValueVsAHP: "Reference Configuration",
    interpretation: "Standard multi-criteria weighting. Subjective pairwise importance matrix adds complexity without ranking gain.",
    status: "Verified from source"
  },
  {
    name: "Section Co-location (E)",
    formulaOrFeature: "Binary indicator: concept u and v appear in the same section",
    ndcg10: 0.684,
    ci: "[0.62, 0.74]",
    pValueVsAHP: "p = 0.42 (Not Significant)",
    interpretation: "Moderate local grouping signal, but misses cross-chapter prerequisite dependencies.",
    status: "Verified from source"
  },
  {
    name: "Chapter Proximity (P)",
    formulaOrFeature: "Inverse chapter distance: 1 / (1 + |chap(u) - chap(v)|)",
    ndcg10: 0.605,
    ci: "[0.54, 0.67]",
    pValueVsAHP: "p < 0.001 (Significant drop)",
    interpretation: "Too coarse to distinguish prerequisite dependencies among concepts in distant chapters.",
    status: "Verified from source"
  },
  {
    name: "Definition Overlap (S)",
    formulaOrFeature: "Jaccard lexical token overlap between definition sentences",
    ndcg10: 0.589,
    ci: "[0.52, 0.65]",
    pValueVsAHP: "p < 0.001 (Indistinguishable from random)",
    interpretation: "Despite receiving 52% of the weight in AHP, definition overlap is near random noise (random = 0.582).",
    status: "Verified from source"
  }
];

// -------------------------------------------------------------
// EDUCATIONAL RELATION ONTOLOGY
// -------------------------------------------------------------
export const RELATION_ONTOLOGY = [
  {
    type: "prerequisite",
    name: "Prerequisite",
    directed: true,
    symbol: "u ≺ v",
    plainMeaning: "Understanding concept u is strictly necessary before learning concept v.",
    formalDef: "A pedagogical dependency where mastery of target concept v requires prior cognitive mastery of concept u.",
    example: "Angle ≺ Triangle (Understanding angles is required to comprehend triangles)",
    counterexample: "Acute Angle and Obtuse Angle (Parallel concepts, neither is a prerequisite of the other)",
    evalStatus: "Evaluated against AL-CPL Ground Truth (98 edges)",
    commonErrors: "Direction reversal (v ≺ u); confusing co-occurrence with pedagogical dependency."
  },
  {
    type: "part_of",
    name: "Part-Of (Meronymy)",
    directed: true,
    symbol: "u ⊂ v",
    plainMeaning: "Concept u is a constituent structural component or attribute of concept v.",
    formalDef: "Meronymic relation specifying that u constitutes an anatomical or structural part of v.",
    example: "Hypotenuse ⊂ Right Triangle; Radius ⊂ Circle",
    counterexample: "Triangle and Circle (Distinct geometric figures)",
    evalStatus: "Audited via Structural Consistency Checks (No external gold standard)",
    commonErrors: "Conflation with hyponymy (Is-A); reciprocal part-of contradictions (A part of B and B part of A)."
  },
  {
    type: "application",
    name: "Application",
    directed: true,
    symbol: "u → v",
    plainMeaning: "Concept or theorem u is applied to solve, measure, or construct concept v.",
    formalDef: "Operational dependency where formula/theorem u serves as an instrument to evaluate instance v.",
    example: "Pythagorean Theorem → Right Triangle; Distance Formula → Coordinate Geometry",
    counterexample: "Line and Point (Definitional primitives, not functional applications)",
    evalStatus: "Audited via Structural Consistency Checks",
    commonErrors: "Labeling generic associations as applications; direction ambiguity."
  },
  {
    type: "extension",
    name: "Extension",
    directed: true,
    symbol: "u ⇒ v",
    plainMeaning: "Concept v generalizes, expands, or projects concept u into higher dimensions or broader scopes.",
    formalDef: "Generalization relation where mathematical framework v extends properties of domain u.",
    example: "Triangle ⇒ Polygon; Euclidean Geometry ⇒ Coordinate Geometry",
    counterexample: "Ray and Line Segment (Alternative bounded subsets of a line)",
    evalStatus: "Audited via Structural Consistency Checks",
    commonErrors: "Conflating prerequisite with generalization; reversing direction."
  },
  {
    type: "similarity",
    name: "Similarity",
    directed: false,
    symbol: "u ≈ v",
    plainMeaning: "Concepts u and v share structural properties, mathematical traits, or dualities.",
    formalDef: "Symmetric topological equivalence or mathematical kinship between concepts in the same taxonomic tier.",
    example: "Circle ≈ Ellipse; Sine ≈ Cosine; SSS Postulate ≈ SAS Postulate",
    counterexample: "Point and Sphere (Disparate dimensionalities)",
    evalStatus: "Audited via Symmetry Invariance Checks (No external gold standard)",
    commonErrors: "Treating symmetric similarity as asymmetric prerequisite dependency."
  }
];

// -------------------------------------------------------------
// SAMPLE GEOMETRY KNOWLEDGE GRAPH (REALISTIC CK-12 SUBSET)
// -------------------------------------------------------------
export const SAMPLE_GRAPH_NODES: ConceptNode[] = [
  { id: "point", name: "Point", chapter: 1, section: "1.1", chapterName: "Basics of Geometry", definition: "A location in space represented by a dot that has no size or dimension.", matchedALCPL: true, alCplName: "point" },
  { id: "line", name: "Line", chapter: 1, section: "1.1", chapterName: "Basics of Geometry", definition: "An infinitely long straight path of points that extends in two opposite directions without end.", matchedALCPL: true, alCplName: "line" },
  { id: "plane", name: "Plane", chapter: 1, section: "1.1", chapterName: "Basics of Geometry", definition: "A flat, two-dimensional surface that extends infinitely in all directions.", matchedALCPL: true, alCplName: "plane" },
  { id: "segment", name: "Line Segment", chapter: 1, section: "1.2", chapterName: "Basics of Geometry", definition: "A measurable part of a line consisting of two endpoints and all points between them.", matchedALCPL: true, alCplName: "line segment" },
  { id: "ray", name: "Ray", chapter: 1, section: "1.2", chapterName: "Basics of Geometry", definition: "A part of a line that begins at an endpoint and extends infinitely in one direction.", matchedALCPL: true, alCplName: "ray" },
  { id: "angle", name: "Angle", chapter: 1, section: "1.3", chapterName: "Basics of Geometry", definition: "A geometric figure formed by two rays sharing a common initial endpoint called the vertex.", matchedALCPL: true, alCplName: "angle" },
  { id: "acute_angle", name: "Acute Angle", chapter: 1, section: "1.3", chapterName: "Basics of Geometry", definition: "An angle measuring strictly greater than 0 degrees and less than 90 degrees.", matchedALCPL: true, alCplName: "acute angle" },
  { id: "right_angle", name: "Right Angle", chapter: 1, section: "1.3", chapterName: "Basics of Geometry", definition: "An angle that measures exactly 90 degrees, forming perpendicular rays.", matchedALCPL: true, alCplName: "right angle" },
  { id: "obtuse_angle", name: "Obtuse Angle", chapter: 1, section: "1.3", chapterName: "Basics of Geometry", definition: "An angle measuring strictly greater than 90 degrees and less than 180 degrees.", matchedALCPL: false },
  { id: "parallel_lines", name: "Parallel Lines", chapter: 3, section: "3.1", chapterName: "Parallel and Perpendicular Lines", definition: "Coplanar lines that never intersect regardless of how far they are extended.", matchedALCPL: true, alCplName: "parallel lines" },
  { id: "perpendicular_lines", name: "Perpendicular Lines", chapter: 3, section: "3.2", chapterName: "Parallel and Perpendicular Lines", definition: "Two intersecting lines that cross at exactly a 90 degree right angle.", matchedALCPL: true, alCplName: "perpendicular lines" },
  { id: "transversal", name: "Transversal", chapter: 3, section: "3.3", chapterName: "Parallel and Perpendicular Lines", definition: "A line that intersects two or more other coplanar lines at distinct points.", matchedALCPL: true, alCplName: "transversal" },
  { id: "triangle", name: "Triangle", chapter: 4, section: "4.1", chapterName: "Triangles and Congruence", definition: "A closed three-sided polygon formed by three line segments joining non-collinear vertices.", matchedALCPL: true, alCplName: "triangle" },
  { id: "right_triangle", name: "Right Triangle", chapter: 4, section: "4.1", chapterName: "Triangles and Congruence", definition: "A triangle containing exactly one interior 90-degree right angle.", matchedALCPL: true, alCplName: "right triangle" },
  { id: "hypotenuse", name: "Hypotenuse", chapter: 4, section: "4.2", chapterName: "Triangles and Congruence", definition: "The longest side of a right triangle, situated directly opposite the right angle.", matchedALCPL: true, alCplName: "hypotenuse" },
  { id: "congruent_triangles", name: "Congruent Triangles", chapter: 4, section: "4.3", chapterName: "Triangles and Congruence", definition: "Triangles with identical shape and size where corresponding sides and angles are equal.", matchedALCPL: true, alCplName: "congruent triangles" },
  { id: "sss_postulate", name: "SSS Postulate", chapter: 4, section: "4.4", chapterName: "Triangles and Congruence", definition: "A criterion stating that if three sides of one triangle equal three sides of another, they are congruent.", matchedALCPL: false },
  { id: "sas_postulate", name: "SAS Postulate", chapter: 4, section: "4.4", chapterName: "Triangles and Congruence", definition: "A criterion stating that two sides and the included angle establish triangle congruence.", matchedALCPL: false },
  { id: "polygon", name: "Polygon", chapter: 6, section: "6.1", chapterName: "Polygons and Quadrilaterals", definition: "A closed plane figure bounded by three or more straight line segments intersecting end-to-end.", matchedALCPL: true, alCplName: "polygon" },
  { id: "quadrilateral", name: "Quadrilateral", chapter: 6, section: "6.2", chapterName: "Polygons and Quadrilaterals", definition: "A four-sided polygon possessing four interior angles summing to 360 degrees.", matchedALCPL: true, alCplName: "quadrilateral" },
  { id: "parallelogram", name: "Parallelogram", chapter: 6, section: "6.3", chapterName: "Polygons and Quadrilaterals", definition: "A quadrilateral with two pairs of parallel opposite sides.", matchedALCPL: true, alCplName: "parallelogram" },
  { id: "pythagorean_theorem", name: "Pythagorean Theorem", chapter: 8, section: "8.1", chapterName: "Right Triangle Trigonometry", definition: "In any right triangle, the square of the hypotenuse equals the sum of the squares of the legs (a^2 + b^2 = c^2).", matchedALCPL: true, alCplName: "pythagorean theorem" },
  { id: "circle", name: "Circle", chapter: 10, section: "10.1", chapterName: "Circles", definition: "The set of all points in a plane equidistant from a fixed center point.", matchedALCPL: true, alCplName: "circle" },
  { id: "radius", name: "Radius", chapter: 10, section: "10.1", chapterName: "Circles", definition: "A line segment extending from the center of a circle to any point on its circumference.", matchedALCPL: true, alCplName: "radius" }
];

export const SAMPLE_GRAPH_EDGES: RelationEdge[] = [
  // Prerequisites (Directed u ≺ v)
  { source: "point", target: "line", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "Lines are formally defined as an infinite set of collinear points." },
  { source: "point", target: "plane", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "Planes are determined by non-collinear points." },
  { source: "line", target: "segment", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "A line segment is a bounded portion of a line." },
  { source: "line", target: "ray", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "A ray is a half-line extending from one endpoint." },
  { source: "ray", target: "angle", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "Angles are defined as two rays sharing a common vertex." },
  { source: "angle", target: "acute_angle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "angle", target: "right_angle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "angle", target: "obtuse_angle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "line", target: "parallel_lines", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "right_angle", target: "perpendicular_lines", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "segment", target: "triangle", type: "prerequisite", isDirected: true, pipeline: "ground_truth", evidence: "Triangles are bounded by three coplanar line segments." },
  { source: "angle", target: "triangle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "right_angle", target: "right_triangle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "triangle", target: "right_triangle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "triangle", target: "congruent_triangles", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "segment", target: "polygon", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "polygon", target: "quadrilateral", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "parallel_lines", target: "parallelogram", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "quadrilateral", target: "parallelogram", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "right_triangle", target: "pythagorean_theorem", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },
  { source: "point", target: "circle", type: "prerequisite", isDirected: true, pipeline: "ground_truth" },

  // Part-Of (Meronymic u ⊂ v)
  { source: "hypotenuse", target: "right_triangle", type: "part_of", isDirected: true, pipeline: "kgx_v2_hybrid", evidence: "The hypotenuse is the side opposite the 90 degree angle." },
  { source: "radius", target: "circle", type: "part_of", isDirected: true, pipeline: "kgx_v2_hybrid", evidence: "A radius is a line segment connecting the center to the boundary." },
  { source: "ray", target: "angle", type: "part_of", isDirected: true, pipeline: "kgx_v2_hybrid" },

  // Applications (u applied to v)
  { source: "pythagorean_theorem", target: "right_triangle", type: "application", isDirected: true, pipeline: "kgx_v2_hybrid", evidence: "Used to compute missing side lengths in right triangles." },
  { source: "sss_postulate", target: "congruent_triangles", type: "application", isDirected: true, pipeline: "kgx_v2_hybrid" },
  { source: "sas_postulate", target: "congruent_triangles", type: "application", isDirected: true, pipeline: "kgx_v2_hybrid" },

  // Extensions (u generalizes to v)
  { source: "triangle", target: "polygon", type: "extension", isDirected: true, pipeline: "kgx_v2_hybrid", evidence: "Triangles are the base case 3-gon; polygons extend to n-gons." },
  { source: "segment", target: "polygon", type: "extension", isDirected: true, pipeline: "kgx_v2_hybrid" },

  // Similarity (Symmetric u ≈ v)
  { source: "acute_angle", target: "obtuse_angle", type: "similarity", isDirected: false, pipeline: "kgx_v2_hybrid" },
  { source: "sss_postulate", target: "sas_postulate", type: "similarity", isDirected: false, pipeline: "kgx_v2_hybrid" },
  { source: "parallel_lines", target: "perpendicular_lines", type: "similarity", isDirected: false, pipeline: "kgx_v2_hybrid" }
];

// -------------------------------------------------------------
// PIPELINE STAGES & ARCHITECTURE
// -------------------------------------------------------------
export const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: "stage-1",
    name: "1. Document Preprocessing & Structural Chunking",
    pipeline: "All",
    purpose: "Convert raw CK-12 Basic Geometry Markdown files into structured chapter/section records while indexing linear character and sentence positions.",
    inputs: ["Raw Markdown / TXT textbook files (data_input/textbook/)"],
    outputs: ["Section text blocks", "Sentence tokens (N=6,104)", "Linear document offsets pos(s)"],
    logic: "Parses headings '# Chapter X' and '## Section X.Y'. Tokenizes text using spaCy / NLTK sentence boundary detection. Assigns sequential integer indexes to sections and sentences.",
    sourceFiles: ["educational_pipeline/concept_extractor.py", "kg_extract/backend.py"],
    failureModes: ["Irregular heading formats causing missed sections", "Sentence splits on mathematical abbreviations like 'Fig. 1' or 'e.g.'"],
    evalRelevance: "Linear position pos(s) forms the foundation of the reading-order baseline and structural prior."
  },
  {
    id: "stage-2",
    name: "2. Concept Candidate Extraction & Normalization",
    pipeline: "All",
    purpose: "Identify candidate mathematical concepts and extract authoritative definition sentences from textbook sections.",
    inputs: ["Structured section text", "Glossary lists"],
    outputs: ["concepts.csv (id, name, chapter, section, definition, first_pos)"],
    logic: "rule_v3 matches terms against a handcrafted 130-word geometry glossary. kgx_v2 prompts Qwen-2.5-7B with a JSON schema to identify noun phrases and verbatim definition sentences.",
    sourceFiles: ["src/rule_v3/extract_concepts.py", "src/kgx_v2/extract_concepts.py", "educational_pipeline/concept_extractor.py"],
    failureModes: ["LLM hallucinating novel or non-standard terms ('angle-sum theorem-like structure')", "Rule glossary missing peripheral textbook terms", "Incomplete or generic definition sentences"],
    evalRelevance: "Sets upper bound on graph completeness: rule_v3 yields 130 concepts; kgx_v2 yields 204 concepts."
  },
  {
    id: "stage-3",
    name: "3. Benchmark Concept Alignment (AL-CPL Mapping)",
    pipeline: "All",
    purpose: "Map extracted textbook concepts onto the 89 standardized AL-CPL geometry benchmark concepts to enable ground-truth evaluation.",
    inputs: ["Extracted concepts", "AL-CPL ground truth ontology (data_input/benchmarks/al_cpl/)"],
    outputs: ["concept_mapping.json (extracted_name -> alcpl_name)"],
    logic: "Two-stage matching: (1) Exact lower-case string equality; (2) Normalized Levenshtein similarity >= 0.85; (3) Manual synonym dictionary for pedagogical variants ('line segment' -> 'segment').",
    sourceFiles: ["eval/match_concepts.py", "data_output/eval_framework/concept_mapping.json"],
    failureModes: ["False positive fuzzy matches on closely named concepts ('angle' vs 'triangle')", "Unmatched benchmark concepts (24 of 89 missing from CK-12 text)"],
    evalRelevance: "Both rule_v3 and kgx_v2 plateau at exactly 65/89 matches (73.0% coverage). Unmatched pairs cannot be scored."
  },
  {
    id: "stage-4",
    name: "4. Candidate Pair Generation",
    pipeline: "All",
    purpose: "Generate candidate pairs of concepts (u, v) for relationship classification and edge weighting.",
    inputs: ["Extracted concepts", "Section co-occurrence index"],
    outputs: ["candidate_pairs.csv (source_id, target_id, cooc_count, shared_sentences)"],
    logic: "rule_v3 pairs terms co-occurring within sentence windows or identical sections. kgx_v2 prompts the model on section-level co-occurring concept lists. Hybrid filters all pairs by reading order.",
    sourceFiles: ["educational_pipeline/candidate_generator.py", "data_output/ck12_geometry/candidate_pairs.csv"],
    failureModes: ["Severe candidate recall bottleneck: rule_v3 achieves 3.1% candidate recall; kgx_v2 achieves 3.5% on benchmark positive pairs."],
    evalRelevance: "Proves that candidate generation, not relation classification, is the primary reason for low end-to-end recall."
  },
  {
    id: "stage-5",
    name: "5. Relation Classification: Symbolic Rules vs Local LLM",
    pipeline: "All",
    purpose: "Classify candidate pairs into one of five educational relations and assign edge orientation.",
    inputs: ["Candidate pairs (u, v)", "Evidence sentences", "Prompt template / regex rules"],
    outputs: ["relations.csv (source, target, relation_type, confidence, evidence)"],
    logic: "rule_v3 searches for lexico-syntactic Hearst patterns ('is required for', 'is part of'). kgx_v2 sends structured JSON prompt to Ollama Qwen-2.5-7B requesting classification and direction.",
    sourceFiles: ["src/rule_v3/build_graph.py", "src/kgx_v2/classify_relations.py", "educational_pipeline/neural_prerequisite_extractor.py"],
    failureModes: ["LLM 50% chance-level directionality due to expository definition symmetry", "Rule-based pattern sparsity (rarely do textbooks write 'Concept A is required for B')"],
    evalRelevance: "Generates edge predictions. Standalone LLM yields edge F1=0.030, AUC=0.503; Rule yields F1=0.052, AUC=0.513."
  },
  {
    id: "stage-6",
    name: "6. Structural Prior Gating & Hybrid Graph Assembly",
    pipeline: "kgx_v2_hybrid",
    purpose: "Apply textbook reading-order forward gating and schema constraints to filter spurious candidate relations.",
    inputs: ["kgx_v2 relation candidates", "Linear concept position index pos(u)"],
    outputs: ["hybrid_graph.json", "pairs_kgx_v2_hybrid.csv"],
    logic: "Enforces strict forward gate: for any prerequisite edge u -> v, requires pos(u) < pos(v). Inverts reversed edges if LLM predicted v -> u. Applies DAG cycle removal.",
    sourceFiles: ["src/kgx_v2_hybrid/build_hybrid.py", "educational_pipeline/verifier.py"],
    failureModes: ["Circular reasoning: textbook reading order strongly correlates with curriculum benchmark order by design."],
    evalRelevance: "Drives hybrid performance up to Closure F1=0.786 and ROC-AUC=0.888 (+0.368 AUC over standalone LLM)."
  },
  {
    id: "stage-7",
    name: "7. Empirical Benchmark Evaluation & Topological Auditing",
    pipeline: "All",
    purpose: "Evaluate predicted graphs against AL-CPL ground truth on common covered pairs (N=868) and execute reference-free diagnostics.",
    inputs: ["Predicted relations", "AL-CPL ground truth", "Mapped concept pairs"],
    outputs: ["prereq_evaluation_summary.json", "relation_diagnostics.json", "weighting_ablation_results.json"],
    logic: "Computes Edge Precision, Recall, F1; Transitive Closure F1 via Floyd-Warshall reachability; ROC-AUC with 1000 bootstrap resamples; NDCG@10 query ranking.",
    sourceFiles: ["eval/evaluate_prereq_benchmarks.py", "kg_eval/framework/report.py", "scripts/reconcile.py"],
    failureModes: ["Inflating closure F1 by counting indirect ancestral paths as direct prerequisites."],
    evalRelevance: "Produces all definitive comparative tables and confidence intervals published in the conference paper."
  }
];

// -------------------------------------------------------------
// RESEARCH GLOSSARY (42 DETAILED ENTRIES)
// -------------------------------------------------------------
export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    term: "Educational Knowledge Graph (EKG)",
    category: "Foundations",
    plainDef: "A knowledge graph specifically designed for education, where nodes represent learning concepts and edges represent pedagogical relations like prerequisites.",
    technicalDef: "A directed multigraph G = (V, E, R, W) where V is a set of educational concept entities, R is a typed relation ontology (Prerequisite, Part-of, etc.), and W represents edge confidence weights.",
    example: "A graph linking 'Angle' -> 'Triangle' with a prerequisite relation and 'Hypotenuse' -> 'Right Triangle' with a part-of relation.",
    appearsIn: "Sections 1, 2, 4, 6"
  },
  {
    term: "Prerequisite Relation",
    category: "Foundations",
    plainDef: "A learning dependency indicating that a student must understand concept A before they can comprehend concept B.",
    technicalDef: "An asymmetric, irreflexive, and transitive binary relation ≺ on concept set V such that u ≺ v implies cognitive mastery of u is a necessary precondition for learning v.",
    formula: "u ≺ v \\implies \\neg(v ≺ u)",
    example: "Arithmetic Operations ≺ Algebraic Equations",
    appearsIn: "Sections 2, 5, 6, 8, 11"
  },
  {
    term: "Structural Prior",
    category: "Priors & Ablation",
    plainDef: "Using the physical structure of a document (such as book order, chapter hierarchy, or heading levels) as an initial hint or hard constraint in an algorithm.",
    technicalDef: "An inductive bias derived from external document topology pos(c) that regularizes or gates semantic relationship predictions.",
    formula: "P(u ≺ v) \\propto f(pos(v) - pos(u))",
    example: "Assuming that concepts introduced in Chapter 1 are more likely to be prerequisites for concepts in Chapter 4 than vice-versa.",
    appearsIn: "Sections 1, 3, 5, 10, 11"
  },
  {
    term: "Reading-Order Baseline",
    category: "Priors & Ablation",
    plainDef: "A simple benchmark rule that predicts concept A is a prerequisite of concept B if A appears earlier in the book than B.",
    technicalDef: "A zero-parameter deterministic heuristic predicting directed edge (u, v) iff the first occurrence index pos(u) < pos(v).",
    formula: "\\hat{E}_{order} = \\{(u, v) \\mid pos(u) < pos(v) \\land u, v \\in V\\}",
    example: "Since 'Line' appears on page 4 and 'Triangle' on page 42, predict Line ≺ Triangle.",
    appearsIn: "Sections 1, 5, 10, 11"
  },
  {
    term: "Transitive Closure",
    category: "Graph Theory",
    plainDef: "Adding all indirect reachable connections to a graph. If A leads to B and B leads to C, transitive closure adds a direct connection from A to C.",
    technicalDef: "The graph G^+ = (V, E^+) where (u, w) \\in E^+ iff there exists a directed path from u to w in G.",
    formula: "E^+ = E \\cup \\{(u, w) \\mid \\exists v: (u, v) \\in E \\land (v, w) \\in E^+\\}",
    example: "Point ≺ Line and Line ≺ Triangle gives indirect prerequisite Point ≺ Triangle.",
    appearsIn: "Sections 6, 11"
  },
  {
    term: "Closure F1",
    category: "Evaluation",
    plainDef: "F1 score calculated after expanding both the predicted graph and ground truth graph to include all indirect prerequisite pathways.",
    technicalDef: "The harmonic mean of precision and recall evaluated over the transitive closures of the predicted adjacency matrix and ground-truth matrix.",
    formula: "F_1^{closure} = \\frac{2 \\cdot P(E_{pred}^+, E_{gt}^+) \\cdot R(E_{pred}^+, E_{gt}^+)}{P + R}",
    example: "Hybrid achieves Closure F1 = 0.786 compared to Edge F1 = 0.413 because transitive closure bridges missing direct hops.",
    appearsIn: "Sections 5, 7, 11"
  },
  {
    term: "ROC-AUC",
    category: "Evaluation",
    plainDef: "Area Under the Receiver Operating Characteristic Curve. Measures how well a model ranks positive prerequisite pairs higher than negative pairs, independent of threshold.",
    technicalDef: "The integral of True Positive Rate against False Positive Rate across all classification thresholds, equivalent to the probability that a randomly chosen positive pair ranks higher than a negative pair.",
    formula: "AUC = P(score(u, v)_{pos} > score(x, y)_{neg})",
    example: "kgx_v2 achieves 0.503 (chance), while Reading Order achieves 0.868 and Hybrid achieves 0.888.",
    appearsIn: "Sections 1, 5, 11"
  },
  {
    term: "Directional Accuracy",
    category: "Evaluation",
    plainDef: "The percentage of true prerequisite pairs where the model correctly identified which concept came first, rather than reversing the arrow.",
    technicalDef: "The proportion of ground-truth positive pairs (u ≺ v) predicted as edges where the edge orientation matches ground truth.",
    formula: "Acc_{dir} = \\frac{\\sum_{(u, v) \\in E_{gt}} \\mathbb{I}[(u, v) \\in \\hat{E}]}{\\sum_{(u, v) \\in E_{gt}} \\mathbb{I}[(u, v) \\in \\hat{E} \\lor (v, u) \\in \\hat{E}]}",
    example: "kgx_v2 scored 4/8 (50% - random coin toss), while Reading Order scored 251/260 (96.5%).",
    appearsIn: "Sections 1, 5, 11"
  },
  {
    term: "NDCG@10",
    category: "Evaluation",
    plainDef: "Normalized Discounted Cumulative Gain at rank 10. Evaluates ranking quality by giving higher credit to relevant prerequisites placed at the very top of the list.",
    technicalDef: "The ratio of Discounted Cumulative Gain (DCG@K) to the Ideal DCG (IDCG@K) for a ranked list of candidate prerequisites.",
    formula: "DCG@K = \\sum_{i=1}^K \\frac{2^{rel_i} - 1}{\\log_2(i + 1)}, \\quad NDCG@K = \\frac{DCG@K}{IDCG@K}",
    example: "Book Position Gap achieves NDCG@10 = 0.891, outperforming Saaty AHP (0.709) and raw co-occurrence (0.742).",
    appearsIn: "Sections 5, 10, 11"
  },
  {
    term: "Saaty Analytic Hierarchy Process (AHP)",
    category: "Priors & Ablation",
    plainDef: "A structured mathematical method for weighting multiple decision criteria based on pairwise comparisons.",
    technicalDef: "An eigenvalue-based multi-criteria weighting method that extracts a priority weight vector W from a positive reciprocal comparison matrix A such that A W = \\lambda_{max} W.",
    formula: "W = 0.52S + 0.24C + 0.09P + 0.15E, \\quad CR = 0.022 < 0.10",
    example: "In rule_v3, weights were assigned: Definition Overlap (52%), Co-occurrence (24%), Section co-location (15%), Chapter proximity (9%).",
    appearsIn: "Sections 5, 10"
  },
  {
    term: "Expository Symmetrical Definition",
    category: "Extraction",
    plainDef: "Introductory textbook sentences that describe concept relationships without stating which concept came first.",
    technicalDef: "Textual definitions characterized by symmetric copula or connective syntax ('An angle is formed by two rays') lacking asymmetric linguistic markers.",
    example: "'Two parallel lines never intersect.' (Gives zero directional cue on whether parallel lines precede intersection or vice versa).",
    appearsIn: "Sections 1, 8, 9, 14"
  },
  {
    term: "Candidate Generation Bottleneck",
    category: "Extraction",
    plainDef: "When the initial filtering step drops too many real connections, making it impossible for the later AI classifier to ever find them.",
    technicalDef: "The catastrophic loss of ground-truth positive pairs during candidate pair filtering prior to relation classification.",
    formula: "Recall_{candidate} = \\frac{|(U \\times V)_{filtered} \\cap E_{gt}|}{|E_{gt}|} = 0.035",
    example: "kgx_v2 filters candidate pairs down so aggressively that only 3.5% of true benchmark prerequisites are ever presented to the LLM.",
    appearsIn: "Sections 1, 7, 8, 14"
  },
  {
    term: "Neuro-Symbolic AI",
    category: "Foundations",
    plainDef: "Combining neural networks (like Large Language Models) with symbolic rules, logic constraints, or graph structures.",
    technicalDef: "Architectures integrating sub-symbolic neural representations with explicit symbolic knowledge graphs, formal grammars, or topological priors.",
    example: "kgx_v2_hybrid uses Qwen-2.5-7B for semantic relatedness and symbolic reading-order rules for directional gating.",
    appearsIn: "Sections 1, 3, 5, 10"
  },
  {
    term: "Directed Acyclic Graph (DAG)",
    category: "Graph Theory",
    plainDef: "A directed graph with no closed loops; following the arrows will never lead you back to where you started.",
    technicalDef: "A finite directed graph containing no directed cycles: \\forall v \\in V, \\nexists \\text{ path from } v \\text{ to } v.",
    example: "Prerequisite curricula must be DAGs so a student is never required to learn A to learn B, and B to learn A.",
    appearsIn: "Sections 6, 11"
  },
  {
    term: "Levenshtein Distance",
    category: "Extraction",
    plainDef: "The minimum number of single-character edits (insertions, deletions, substitutions) required to change one word into another.",
    technicalDef: "Metric d(s_1, s_2) measuring string edit distance, normalized as 1 - d(s_1, s_2)/\\max(|s_1|, |s_2|) for fuzzy concept matching.",
    example: "Levenshtein similarity between 'line segment' and 'line segments' is 0.92 >= 0.85 (match).",
    appearsIn: "Sections 4, 7"
  },
  {
    term: "Evaluation Coverage",
    category: "Evaluation",
    plainDef: "The portion of a benchmark dataset that can actually be tested based on which concepts were extracted from the textbook.",
    technicalDef: "The intersection size |V_{extracted} \\cap V_{benchmark}| and corresponding candidate pair set N = |(V_{extracted} \\times V_{extracted}) \\cap (V_{bm} \\times V_{bm})|.",
    example: "Of 1,681 pairs in AL-CPL, only 868 pairs (260 positive, 608 negative) are formed by concepts extracted by both pipelines.",
    appearsIn: "Sections 4, 11"
  },
  {
    term: "Bootstrap Confidence Interval",
    category: "Evaluation",
    plainDef: "A statistical method that resamples the experimental results thousands of times to compute a 95% certainty range for a score.",
    technicalDef: "Non-parametric estimation of parameter variance via B = 1,000 random resamples with replacement, reporting 2.5th and 97.5th percentiles.",
    example: "ROC-AUC for kgx_v2 is 0.503 [95% CI: 0.49, 0.51], proving performance spans 0.500 (chance).",
    appearsIn: "Sections 5, 11"
  },
  {
    term: "Meronymy (Part-Of)",
    category: "Foundations",
    plainDef: "The relationship between a part and the whole it belongs to.",
    technicalDef: "A semantic relation u ⊂ v specifying that concept entity u is a constituent structural part of concept entity v.",
    example: "Hypotenuse is part-of Right Triangle; Radius is part-of Circle.",
    appearsIn: "Sections 6, 14"
  },
  {
    term: "Hyponymy (Is-A)",
    category: "Foundations",
    plainDef: "The relationship between a specific subtype and its general category.",
    technicalDef: "A taxonomic subsumption relation u \\sqsubseteq v where all instances of u are instances of broader class v.",
    example: "Right Triangle is a Triangle; Square is a Quadrilateral.",
    appearsIn: "Sections 6, 14"
  },
  {
    term: "Ontological Contradiction",
    category: "Graph Theory",
    plainDef: "When a knowledge graph contains conflicting or impossible connections according to formal logic rules.",
    technicalDef: "Violation of schema axioms, such as reciprocal meronymy (A part-of B and B part-of A) or reciprocal prerequisite dependencies (A ≺ B and B ≺ A).",
    example: "The 43 contradictions detected in kgx_v2 unconstrained output where reciprocal relations violated asymmetry.",
    appearsIn: "Sections 5, 14"
  },
  {
    term: "BIGS (Grounding Metric)",
    category: "Evaluation",
    plainDef: "A reference-free metric that measures whether an extracted graph edge is supported by direct textbook citations.",
    technicalDef: "Reference-free evaluation auditing textual evidence density and verbatim sentence alignment between extracted graph relations and source corpus sentences.",
    example: "Verifies if the claimed relation 'Ray ≺ Angle' is accompanied by a verbatim quote from Chapter 1.",
    appearsIn: "Sections 11"
  },
  {
    term: "Circularity Risk",
    category: "Priors & Ablation",
    plainDef: "When an evaluation looks good only because the test data and the method both rely on the exact same underlying assumption.",
    technicalDef: "Construct validity threat where textbook reading order and benchmark prerequisite order are co-dependent because curriculum benchmarks were authored by inspecting textbook sequences.",
    example: "Hybrid achieves high AL-CPL scores partly because AL-CPL ground truth aligns with standard US high school geometry curriculum order.",
    appearsIn: "Sections 3, 10, 15"
  }
];

// -------------------------------------------------------------
// PRESENTATION FAQ & ORAL DEFENSE GUIDE (20 ITEMS)
// -------------------------------------------------------------
export const PRESENTATION_FAQS: FAQItem[] = [
  {
    id: "faq-1",
    question: "What is the primary contribution of this research?",
    category: "Motivation",
    quickAnswer: "We conduct the first rigorous de-confounding of local LLM prerequisite extraction, revealing that local 7B LLMs operate at chance (AUC 0.503, Dir Acc 50%) and that reported hybrid success is overwhelmingly driven by textbook reading-order priors (+0.368 AUC gain).",
    deepAnswer: "Recent educational AI literature has enthusiastically adopted LLMs as zero-shot knowledge graph extractors without controlling for document structural priors. We evaluated rule-based, local LLM (Qwen-2.5-7B), and hybrid pipelines on the AL-CPL geometry benchmark. We proved that: (1) Local LLMs cannot infer prerequisite directionality from textbook snippets alone due to expository definition symmetry; (2) Linear reading order is a massive structural prior (AUC 0.868, Dir Acc 96.5%); (3) The hybrid pipeline's high performance derives from structural gating, with the LLM providing only a marginal +0.020 AUC gain as an undirected semantic pruning filter; and (4) Multi-criteria AHP weighting is redundant to simple co-occurrence.",
    keyMetric: "LLM AUC: 0.503 vs Reading Order AUC: 0.868 vs Hybrid AUC: 0.888",
    pitfallToAvoid: "Do NOT say 'We built a new state-of-the-art hybrid model.' Emphasize that this is an empirical comparative evaluation that de-confounds existing claims."
  },
  {
    id: "faq-2",
    question: "Why did you use a local 7B model instead of GPT-4 or Claude 3.5?",
    category: "LLM Performance",
    quickAnswer: "Privacy, zero API cost, reproducible local deployment, and offline institutional feasibility in real-world educational infrastructure.",
    deepAnswer: "In educational technology, student privacy regulations (FERPA, GDPR) and school district budget constraints make commercial cloud APIs impractical for large-scale curriculum indexing. Evaluating an open-weight 7B parameter model (Qwen-2.5-7B) running locally via Ollama tests the realistic baseline that schools and ed-tech non-profits can actually deploy on commodity hardware without sending private data to commercial cloud providers.",
    keyMetric: "Model: Qwen-2.5-7B-Instruct running on local hardware via Ollama.",
    pitfallToAvoid: "Don't claim 7B models are universally superior. Acknowledge that frontier 70B+ or frontier proprietary models might perform better, which we identify as an open research question."
  },
  {
    id: "faq-3",
    question: "Why is textbook reading order such an effective baseline?",
    category: "Baselines",
    quickAnswer: "Because educational textbooks are intentionally authored in pedagogical sequence: foundational concepts are introduced before dependent theorems.",
    deepAnswer: "Unlike Wikipedia or general web crawls, curriculum textbooks are designed by domain pedagogues to minimize cognitive load. In axiomatic domains like geometry, Euclidean proofs strictly require preceding definitions. Consequently, chronological appearance in the textbook serves as an exceptionally strong inductive bias for prerequisite dependency, correctly orienting 251 out of 260 ground truth positive pairs (96.5% directional accuracy).",
    keyMetric: "Reading Order Directional Accuracy: 251/260 (96.5%)",
    pitfallToAvoid: "Don't claim reading order is a complete knowledge graph. It creates many false positives between distant, unrelated concepts and lacks semantic labels."
  },
  {
    id: "faq-4",
    question: "Why does the local LLM operate at chance (AUC 0.503)?",
    category: "LLM Performance",
    quickAnswer: "Introductory textbook definitions present properties symmetrically; they describe how concepts interact without explicit temporal or dependency cues.",
    deepAnswer: "When an LLM is presented with a definition like 'Two rays sharing an endpoint form an angle,' there are no explicit asymmetric discourse markers (e.g., 'A is required to understand B'). Both concepts co-occur symmetrically. Without external context or global curriculum position, the 7B model cannot deduce which concept is the cognitive prerequisite, resulting in exactly 4/8 (50.0%) directional accuracy on ground truth pairs.",
    keyMetric: "Directional Accuracy: 4/8 (50.0%) | ROC-AUC: 0.503 [0.49, 0.51]",
    pitfallToAvoid: "Avoid saying 'LLMs are completely useless.' Specify that 7B LLMs fail at zero-shot directional prerequisite inference from isolated definition sentences."
  },
  {
    id: "faq-5",
    question: "Does the hybrid pipeline prove that the LLM is reasoning about prerequisites?",
    category: "Hybrid & Circularity",
    quickAnswer: "No. Ablation reveals that reading order provides 97.7% of the AUC; the LLM merely prunes early false positives, acting as an undirected semantic filter.",
    deepAnswer: "When we ablate the reading-order forward gate from the hybrid, its performance drops back down to the chance-level LLM performance. The pure reading-order baseline already achieves an AUC of 0.868. Adding the LLM pushes AUC to 0.888—a marginal gain of just +0.020. The LLM's true contribution is semantic relevance filtering: it checks whether concept u and v are genuinely related, pruning false-positive early concepts and boosting precision from 0.595 to 0.845.",
    keyMetric: "Reading Order AUC: 0.868 vs Hybrid AUC: 0.888 (+0.020 marginal gain)",
    pitfallToAvoid: "Do NOT credit the hybrid's 0.888 AUC to 'deep neural reasoning.' Be transparent that it is a structurally gated hybrid."
  },
  {
    id: "faq-6",
    question: "What is the difference between Direct Edge F1 and Closure F1?",
    category: "Evaluation",
    quickAnswer: "Direct Edge F1 tests exact one-to-one connections; Closure F1 tests whether there is any valid multi-step path from concept A to concept B.",
    deepAnswer: "Direct Edge F1 requires predicting the exact direct prerequisite edge documented by human benchmark annotators. However, in education, if A is a prerequisite for B, and B is a prerequisite for C, then A is an indirect prerequisite for C. Transitive Closure F1 computes the transitive reachability matrix before scoring. This explains why the hybrid achieves an Edge F1 of 0.413 but a Closure F1 of 0.786: the graph captures the broader cognitive dependency paths even when skipping direct links.",
    keyMetric: "Hybrid Edge F1: 0.413 vs Closure F1: 0.786",
    pitfallToAvoid: "Never report Closure F1 without also reporting Edge F1, otherwise you conceal graph sparsity."
  },
  {
    id: "faq-7",
    question: "Why is the candidate generation stage described as a bottleneck?",
    category: "Evaluation",
    quickAnswer: "Because candidate filtering discards over 96% of ground-truth prerequisite pairs before the relation classifier ever sees them.",
    deepAnswer: "In end-to-end evaluation, candidate recall for rule_v3 is 3.1%, and for kgx_v2 it is 3.5%. This means that out of all valid prerequisite pairs in the benchmark, the pipeline only proposes candidate pairs for 3.5% of them. Even if the classifier had 100% precision on those pairs, final recall could never exceed 3.5%. The failure of end-to-end recall is primarily a retrieval failure, not a classification failure.",
    keyMetric: "Candidate Recall: rule_v3 = 3.1%, kgx_v2 = 3.5%",
    pitfallToAvoid: "Don't blame low recall solely on the LLM classifier; candidate generation is the structural culprit."
  },
  {
    id: "faq-8",
    question: "Why did Co-occurrence outperform Saaty AHP in edge weighting?",
    category: "Priors & Ablation",
    quickAnswer: "Multi-criteria AHP placed 52% of its weight on Definition Overlap, which turned out to be near-random noise (NDCG@10 = 0.589).",
    deepAnswer: "The Analytic Hierarchy Process relies on a subjective pairwise comparison matrix. The author assigned 52% weight to Jaccard definition overlap (S), 24% to co-occurrence (C), 15% to section co-location (E), and 9% to chapter proximity (P). Our ablation showed that definition overlap achieves an NDCG@10 of only 0.589 (barely above random 0.582). By heavily weighting an uninformative feature, AHP diluted the strong predictive signal of co-occurrence (0.723) and book position gap (0.891).",
    keyMetric: "AHP NDCG@10: 0.709 vs Co-occurrence: 0.723 (p=0.68) vs Book Gap: 0.891 (p<0.0001)",
    pitfallToAvoid: "Don't say AHP was 'wrongly implemented'—it had a valid Consistency Ratio (CR=0.022), but the subjective feature prioritization was empirically suboptimal."
  },
  {
    id: "faq-9",
    question: "Why is concept coverage capped at 73.0%?",
    category: "Evaluation",
    quickAnswer: "24 of the 89 AL-CPL benchmark concepts simply do not appear in the CK-12 Basic Geometry textbook.",
    deepAnswer: "The AL-CPL benchmark was constructed from multiple university and high school geometry curricula. Our source text (CK-12 Basic Geometry) omitted 24 concepts (e.g., advanced trigonometric identities or specific coordinate constructions). Even with fuzzy Levenshtein matching (>= 0.85) and an extensive synonym dictionary, both rule_v3 and kgx_v2 matched exactly 65 out of 89 concepts (73.0%), establishing a hard upper ceiling on benchmark evaluation.",
    keyMetric: "Mapped Concepts: 65/89 (73.0%)",
    pitfallToAvoid: "Don't claim our pipelines missed 27% of concepts due to poor algorithms; those concepts were absent from the source textbook."
  },
  {
    id: "faq-10",
    question: "Is there circularity in evaluating the hybrid with textbook reading order?",
    category: "Hybrid & Circularity",
    quickAnswer: "Yes, and we explicitly disclose this as a primary threat to validity.",
    deepAnswer: "Curriculum benchmarks like AL-CPL were created by educators who themselves followed standard textbook curriculum progressions. When the hybrid pipeline uses textbook reading order as a forward gate, it leverages the same pedagogical progression encoded in the benchmark. Disclosing this circularity is one of our paper's central contributions: many prior works report high hybrid scores without acknowledging that the model is simply riding the curriculum structure.",
    keyMetric: "Circularity Disclosure: Threats to Validity Section (Section 10)",
    pitfallToAvoid: "Never try to hide the circularity. Reviewers respect researchers who identify and rigorously analyze their own structural confounds."
  },
  {
    id: "faq-11",
    question: "Why didn't you evaluate Part-of, Application, and Similarity against ground truth?",
    category: "Evaluation",
    quickAnswer: "Because no public benchmarks exist for those relations in geometry; we audited them using structural consistency checks instead.",
    deepAnswer: "The AL-CPL benchmark only contains annotations for directed prerequisite relations. Rather than fabricating ground truth, we developed reference-free structural consistency diagnostics. We audited the graphs for formal ontological violations—such as reciprocal part-of cycles or conflicting relation types—and identified 43 semantic contradictions in the unconstrained LLM graph.",
    keyMetric: "Audited Contradictions: 43 in unconstrained kgx_v2",
    pitfallToAvoid: "Do not claim you 'evaluated' non-prerequisite relations with precision/recall. State clearly that they were audited via consistency diagnostics."
  },
  {
    id: "faq-12",
    question: "What are the main threats to the validity of this study?",
    category: "Defense",
    quickAnswer: "Single educational domain (Geometry), single local model family (Qwen-2.5-7B), candidate generation bottleneck, and partial benchmark coverage (73%).",
    deepAnswer: "We identify four major threats: (1) Domain specificity: Euclidean geometry is uniquely axiomatic, meaning reading order may be less dominant in non-sequential subjects like History; (2) Model capacity: 7B models may lack emergent reasoning present in 70B+ models; (3) Candidate generation: our candidate filtering stage severely limits end-to-end recall; and (4) Reference-free relations: multi-relation types lack human gold standards.",
    keyMetric: "Threats to Validity: Section 10 of manuscript",
    pitfallToAvoid: "Never claim the results generalize universally to all subjects or all LLM models."
  },
  {
    id: "faq-13",
    question: "How did you compute the 95% confidence intervals?",
    category: "Evaluation",
    quickAnswer: "Non-parametric bootstrap resampling with B = 1,000 iterations over the common covered evaluation pair set.",
    deepAnswer: "For each metric (ROC-AUC, Closure F1), we drew 1,000 random bootstrap samples with replacement from the N = 868 common covered pair set. We computed the metric on each sample and derived the 95% empirical confidence intervals using the 2.5th and 97.5th percentiles. This confirmed that kgx_v2's AUC CI [0.49, 0.51] encompasses 0.500, proving statistical equivalence to chance.",
    keyMetric: "Bootstrap Resamples: B = 1,000 | kgx_v2 CI: [0.49, 0.51]",
    pitfallToAvoid: "Don't confuse bootstrap sample size (B=1000) with the dataset size (N=868)."
  },
  {
    id: "faq-14",
    question: "What does the 7/7 directional accuracy of rule_v3 mean?",
    category: "Evaluation",
    quickAnswer: "It means 100% precision on a tiny sample, but near-zero recall. It found 7 correct edges out of 260.",
    deepAnswer: "Rule-based regex patterns looking for explicit linguistic connectives ('is required for') are extremely precise when they match, achieving 7/7 correct directions. However, textbook authors rarely use such heavy-handed pedagogical phrasing, resulting in a recall of just 0.027. Reporting 7/7 alongside the recall limitation prevents misleading claims of superiority.",
    keyMetric: "rule_v3: 7/7 (100%) directional accuracy, but only 0.027 recall",
    pitfallToAvoid: "Never cite the 100% directional accuracy of rule_v3 without immediately mentioning its 2.7% recall."
  },
  {
    id: "faq-15",
    question: "Could prompt engineering fix the LLM's directional failure?",
    category: "LLM Performance",
    quickAnswer: "Marginally, but prompt phrasing cannot overcome the lack of directional signal in the underlying definition text snippets.",
    deepAnswer: "We tested multiple prompt variations, including role prompting, chain-of-thought, and strict JSON schemas. While structured JSON formatting solved schema adherence, it did not alter directional accuracy. When given only definition text snippets, the linguistic cues are inherently symmetrical. Giving the LLM the entire chapter context would help, but that implicitly introduces the reading-order prior through text sequence.",
    keyMetric: "Schema adherence reached 98%+, but directional accuracy remained ~50%.",
    pitfallToAvoid: "Don't dismiss prompt engineering entirely, but emphasize that prompt tweaks cannot conjure missing signal."
  },
  {
    id: "faq-16",
    question: "What is BIGS and what did it measure?",
    category: "Evaluation",
    quickAnswer: "BIGS measures reference-free textual grounding: whether an extracted edge cites an actual, verbatim textbook sentence.",
    deepAnswer: "BIGS (Benchmark-Independent Grounding Score) assesses whether extracted relations are grounded in the source text rather than hallucinated from model pre-training. It verifies if the pair co-occurs in the text and whether the pipeline can extract a verbatim evidence sentence. Both rule_v3 and kgx_v2 achieved high BIGS grounding, showing that models were extracting real textual associations even when they failed at prerequisite directionality.",
    keyMetric: "Grounding density: verified against source corpus sentences.",
    pitfallToAvoid: "Do not equate textual grounding with prerequisite correctness. A model can cite a real sentence while completely misunderstanding the relationship."
  },
  {
    id: "faq-17",
    question: "How does this study compare to Liang et al. (2015, 2018)?",
    category: "Motivation",
    quickAnswer: "Liang et al. pioneered concept prerequisite learning using feature-engineered classifiers; we evaluate modern local LLMs and deconstruct structural priors against their AL-CPL benchmark.",
    deepAnswer: "Liang et al. introduced AL-CPL and used active learning with hand-engineered lexical, Wikipedia, and textbook features. We use their gold-standard geometry dataset as an external benchmark to evaluate modern generative LLMs and neuro-symbolic combinations, showing that despite a decade of NLP progress, raw local LLMs still fail on directionality without structural scaffolding.",
    keyMetric: "AL-CPL Benchmark: 89 concepts, 98 prerequisite relations.",
    pitfallToAvoid: "Do not criticize Liang et al.; position their work as the respected benchmark foundation of our study."
  },
  {
    id: "faq-18",
    question: "What is the recommended architecture for practical educational KG construction?",
    category: "Defense",
    quickAnswer: "A structurally gated hybrid: use document reading order for candidate generation and directionality, and use a local LLM as an undirected semantic pruning filter.",
    deepAnswer: "Based on our findings, practitioners should not ask LLMs to infer prerequisite directionality. The optimal architectural division of labor is: (1) Use curriculum document hierarchy and reading order to propose candidate pairs and assign directed orientation; (2) Use a local LLM or co-occurrence filter to prune false-positive associations; and (3) Apply formal schema constraints to prevent ontological cycles.",
    keyMetric: "Hybrid Pipeline: Precision = 0.845, Closure F1 = 0.786",
    pitfallToAvoid: "Don't recommend pure LLM extraction for educational knowledge graphs."
  },
  {
    id: "faq-19",
    question: "How did you ensure scientific integrity and prevent experimental fabrication?",
    category: "Defense",
    quickAnswer: "We froze all experimental outputs, performed zero new inference runs, and created a strict claim traceability matrix linking every number to stored JSON files.",
    deepAnswer: "We adhered to strict reproducible research protocols. All metrics reported in the paper were pulled directly from frozen evaluation logs (`data_output/eval_framework/`). We did not rerun Ollama or modify evaluation scripts to generate better numbers. Every single claim is classified in our Claim Traceability Matrix into one of four epistemic tiers, explicitly marking unverified hypotheses and negative results.",
    keyMetric: "Claim Traceability Matrix: paper_submission/claim_traceability.md",
    pitfallToAvoid: "Be proud of reporting negative results; conference reviewers value honest negative findings over suspiciously flawless synthetic numbers."
  },
  {
    id: "faq-20",
    question: "What are your top recommendations for future work?",
    category: "Defense",
    quickAnswer: "Multi-domain replication on non-deductive subjects (e.g., Biology), testing larger 70B open models, and conducting human learner-reachability trials.",
    deepAnswer: "The most impactful next steps are: (1) Cross-domain replication: test whether reading order remains dominant in less axiomatic subjects like Biology or History; (2) Model scaling: evaluate whether 70B parameter models or quantized frontier models can perform zero-shot directional deduction; (3) Multi-relation human annotation: gather expert gold standards for Part-of and Application relations; and (4) Learner trials: test whether these knowledge graphs improve adaptive question recommendation in live classrooms.",
    keyMetric: "Future Work: Section 11 of manuscript",
    pitfallToAvoid: "Do not describe future work as if it were already completed."
  }
];

// -------------------------------------------------------------
// IMPLEMENTATION FILE MAPPING
// -------------------------------------------------------------
export const REPOSITORY_FILE_MAP = [
  {
    path: "src/rule_v3/extract_concepts.py",
    stage: "Concept Extraction (rule_v3)",
    purpose: "Extracts 130 geometry concepts using handcrafted regex and glossary matching.",
    inputs: "CK-12 section Markdown files",
    outputs: "data_output/ck12_geometry/concepts.csv",
    dependencies: "re, csv, pathlib",
    limitations: "Vocabulary is bounded by handcrafted glossary; misses peripheral concepts."
  },
  {
    path: "src/rule_v3/build_graph.py",
    stage: "Relation Extraction & AHP (rule_v3)",
    purpose: "Computes co-occurrence and applies Saaty AHP formula to weight prerequisite edges.",
    inputs: "concepts.csv, section text",
    outputs: "data_output/ck12_geometry/relations.csv",
    dependencies: "numpy, ahp_weights.py",
    limitations: "Hearst patterns yield extremely sparse recall (2.7%)."
  },
  {
    path: "src/kgx_v2/extract_concepts.py",
    stage: "Concept Extraction (kgx_v2)",
    purpose: "Queries Ollama Qwen-2.5-7B with structured JSON schema to discover concept nouns and definitions.",
    inputs: "CK-12 section text chunks",
    outputs: "data_output/ck12_geometry_kgx_v2/concepts.csv",
    dependencies: "requests, json, Ollama API",
    limitations: "Extracts noisy compound phrases; yields 70 valid definitions out of 204 terms."
  },
  {
    path: "src/kgx_v2/classify_relations.py",
    stage: "Relation Extraction (kgx_v2)",
    purpose: "Prompts Qwen-2.5-7B for zero-shot relation classification across 5 relation types.",
    inputs: "Candidate concept pairs + definition snippets",
    outputs: "data_output/ck12_geometry_kgx_v2/relations.csv",
    dependencies: "requests, Ollama",
    limitations: "Operates at chance on directional prerequisite orientation (50.0% accuracy)."
  },
  {
    path: "src/kgx_v2_hybrid/build_hybrid.py",
    stage: "Neuro-Symbolic Fusion (kgx_v2_hybrid)",
    purpose: "Combines LLM semantic relatedness with reading-order forward gating (pos(u) < pos(v)).",
    inputs: "kgx_v2 relations, linear concept positions",
    outputs: "data_output/ck12_geometry_kgx_v2_hybrid/relations.csv",
    dependencies: "pandas, networkx",
    limitations: "Strongly dependent on linear curriculum prior."
  },
  {
    path: "eval/evaluate_prereq_benchmarks.py",
    stage: "Benchmark Evaluation",
    purpose: "Computes Edge F1, Closure F1, ROC-AUC (1000 bootstrap resamples) on AL-CPL common covered pairs.",
    inputs: "Predicted relations, AL-CPL ground truth (data_input/benchmarks/al_cpl/)",
    outputs: "data_output/eval_framework/prereq_evaluation_summary.json",
    dependencies: "scikit-learn, scipy, numpy",
    limitations: "Constrained to covered concept pair set (N=868)."
  },
  {
    path: "eval/book_order_baseline.py",
    stage: "Baseline Evaluation",
    purpose: "Generates and evaluates deterministic reading-order prerequisite baseline.",
    inputs: "Concept first appearance positions pos(c)",
    outputs: "data_output/eval_framework/prereq_evaluation_summary.json",
    dependencies: "pandas, scikit-learn",
    limitations: "Generates transitive false positives across distant chapters."
  },
  {
    path: "scripts/reconcile.py",
    stage: "Data Auditing",
    purpose: "Reconciles concept definitions, cleans ground truth concepts, and audits stage attrition.",
    inputs: "Raw datasets, candidate pairs",
    outputs: "data_output/reconciliation_report.json",
    dependencies: "json, pandas",
    limitations: "Identifies the 24 missing AL-CPL concepts."
  }
];
