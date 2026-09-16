# Educational Knowledge Graph Pipeline

## Overview
The Educational Knowledge Graph Pipeline is designed to process educational texts, specifically textbooks (e.g., *Foundations of Machine Learning*), and automatically generate a structured Knowledge Graph. This graph captures key concepts and their pedagogical relationships, enabling Graph-Augmented Generation (GAG) and advanced Q&A systems.

## Architecture

The pipeline consists of several sequential modules that transform raw text into a final interactive knowledge graph.

### 1. Parser (`parser.py`)
Converts raw text or PDF input into structural `ParsedBlock` objects. 
- **Features:** It handles document-specific artifacts, such as robust page marker handling (e.g., stripping `--- Page X ---`), to prevent irrelevant text from polluting the knowledge extraction process.

### 2. Structure Detector (`structure_detector.py`)
Classifies parsed blocks into pedagogical categories (e.g., Definition, Theorem, Example).
- **Features:** Uses regex-based `RULES` to identify block types. It's customized to handle variations like "Worked Example" mapping to the "Example" block type.

### 3. Chunker (`chunker.py`)
Aggregates classified blocks into `EducationalChunk` objects based on pedagogical boundaries, ensuring context is maintained for downstream extraction.

### 4. Concept Extractor (`concept_extractor.py`)
Identifies and normalizes key educational concepts from the chunks, yielding `NormalizedConcept` objects.
- **Features:** Employs a hybrid approach combining rule-based extraction (e.g., capitalized phrase matching) with a predefined list of domain-specific terms relevant to the textbook (e.g., Machine Learning terminology).

### 5. Relation Extractor (`relation_extractor.py`)
Links extracted concepts using a strict 5-type pedagogical ontology:
- **Prerequisite:** Concept A must be understood before Concept B.
- **Similarity:** Concept A is similar to Concept B.
- **Application:** Concept A is applied in or to Concept B.
- **Extension:** Concept A extends or generalizes Concept B.
- **Part-of:** Concept A is a component of Concept B.
- **Features:** Uses `ONTOLOGY_PATTERNS` and custom `pedagogical_rules` to enforce this ontology and ensure referential integrity.

### 6. Graph Generator
Outputs the final nodes and edges into CSV files (`concepts.csv`, `relations.csv`) and generates an interactive HTML visualization (`docs/index.html`).

## Outputs

- `concepts.csv`: Contains all extracted nodes (concepts) and their properties.
- `relations.csv`: Contains all extracted edges (relationships) matching the 5-type ontology.
- `docs/index.html`: A web-based interactive graph visualization using `vis.js`. 

## How to Run

1. Place your source textbook text file in the appropriate data directory.
2. Run the main pipeline script (e.g., `python main.py` or equivalent entry point).
3. The pipeline will process the text, run validations, and generate the output files in the output directory.
4. Open `docs/index.html` in a web browser to view the interactive Knowledge Graph.

## Recent Updates
- Switched data source from the Cureus healthcare dataset to the *Foundations of Machine Learning* textbook (Chapter 3).
- Implemented robust regex rules to ignore page markers and accurately classify worked examples.
- Enforced the 5-type relation ontology and implemented referential integrity checks during pipeline execution.
