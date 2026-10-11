"""Run the educational pipeline on the CK-12 geometry textbook."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from educational_pipeline import run_educational_pipeline

concepts_csv, relations_csv, G = run_educational_pipeline(
    data_dir="ck12_geometry",
    use_llm=False,
    output_html="./docs/ck12_geometry.html",
    show_edge_labels=False,
    show_edge_tooltips=True,
)
print("Pipeline complete.")
print(f"Concepts: {G.number_of_nodes()}")
print(f"Relations: {G.number_of_edges()}")
