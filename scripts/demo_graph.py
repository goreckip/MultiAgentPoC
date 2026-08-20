"""Week 4 demo: full graph end to end — auto-handled question, rejected
question (validation), and an escalated question that pauses on interrupt()
and resumes with a human answer.
"""

import uuid

from langfuse import get_client
from langgraph.types import Command

from multiagent_poc.graph.pipeline_graph import build_graph, invoke_graph


def run_case(graph, label: str, question: str):
    print(f"\n=== {label} ===")
    print(f"Q: {question}")
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = invoke_graph(graph, {"question": question}, config=config)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print(f"[PAUSED for human] reason: {payload['reason']}")
        human_answer = "Wstaw naklejke z obnizona cena i sprzedaj w pierwszej kolejnosci (odpowiedz operatora)."
        result = invoke_graph(graph, Command(resume=human_answer), config=config)
        print("[RESUMED]")

    print(f"intent={result.get('intent')} escalate={result.get('should_escalate')} rejected={result.get('rejected')}")
    print(f"answer: {result.get('answer')}")
    if result.get("sources"):
        print(f"sources: {result['sources']}")


def run():
    graph = build_graph()

    run_case(graph, "auto-handled (dostawy)",
              "Dostawca przywiózł inny towar niż zamówiony, kierowca już odjechał, co robię?")

    run_case(graph, "rejected (PESEL)",
              "Jaki jest numer PESEL kierownika zmiany? 44051401359")

    run_case(graph, "escalated -> HITL resume",
              "Sanepid zapowiedział kontrolę na jutro, na co mam zwrócić uwagę?")

    get_client().flush()  # short-lived script — make sure traces land before exit


if __name__ == "__main__":
    run()
