"""LLM-as-judge scoring for generated answers.

Known limitation, stated up front rather than glossed over: the judge is the
same local llama3.1:8b that generates the answers being judged. A model
scoring its own output family is a weak, potentially lenient judge — this is
a secondary, more nuanced signal alongside the deterministic keyword score
in rag_eval_set.py, not a replacement for it. See decision_log.md.
"""

from dataclasses import dataclass
import re

from langchain_ollama import ChatOllama

from multiagent_poc.config import settings
from multiagent_poc.observability.langfuse_client import get_callback_handler, observe

JUDGE_PROMPT = """Jesteś surowym recenzentem odpowiedzi asystenta operacyjnego sieci sklepów convenience.
Oceń, czy ODPOWIEDŹ poprawnie i w duchu PROCEDURY odpowiada na PYTANIE.

PYTANIE: {question}

PROCEDURA (fragment, źródło prawdy):
{context}

ODPOWIEDŹ ASYSTENTA:
{answer}

Oceń w skali 1-5 (1 = całkowicie błędna/sprzeczna z procedurą, 5 = w pełni poprawna i zgodna z procedurą).
Odpowiedz WYŁĄCZNIE w formacie:
SCORE: <liczba 1-5>
REASON: <jedno zdanie uzasadnienia>
"""


@dataclass
class JudgeResult:
    score: int | None
    reason: str
    raw: str


@observe(name="llm_judge")
def judge_answer(question: str, context: str, answer: str) -> JudgeResult:
    llm = ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0)
    prompt = JUDGE_PROMPT.format(question=question, context=context, answer=answer)
    response = llm.invoke([("human", prompt)], config={"callbacks": [get_callback_handler()]})
    raw = response.content

    score_match = re.search(r"SCORE:\s*(\d)", raw)
    score = int(score_match.group(1)) if score_match else None
    reason_match = re.search(r"REASON:\s*(.+)", raw)
    reason = reason_match.group(1).strip() if reason_match else raw.strip()

    return JudgeResult(score=score, reason=reason, raw=raw)
