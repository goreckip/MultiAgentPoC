"""Week 2 experiment: compare fixed-size vs section chunking retrieval quality
on the example question from docs/runbooks/README.md.
"""

from multiagent_poc.rag.index import COLLECTION_FIXED, COLLECTION_SECTION
from multiagent_poc.rag.retrieval import retrieve

QUESTION = "Dostawca przywiózł inny towar niż zamówiony, kierowca już odjechał, co robię?"


def show(collection_name: str):
    print(f"\n=== {collection_name} ===")
    for i, chunk in enumerate(retrieve(QUESTION, collection_name, k=3), start=1):
        print(f"\n--- result {i} (distance={chunk.distance:.4f}, source={chunk.source}) ---")
        print(f"heading_path: {chunk.heading_path!r}")
        print(chunk.text[:300])


if __name__ == "__main__":
    print(f"Question: {QUESTION}")
    show(COLLECTION_FIXED)
    show(COLLECTION_SECTION)
