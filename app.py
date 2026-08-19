"""Streamlit UI — single page, two sections: employee question form and a
simulated HITL operator panel. Run with `streamlit run app.py`.

Session-state model: one graph instance is shared across all users
(st.cache_resource — the LangGraph MemorySaver checkpointer holds every
thread's state internally, keyed by thread_id, so sharing the graph object
itself is safe). Each browser session gets its own thread_id and history.
"""

from pathlib import Path
import tempfile
import uuid

from langgraph.types import Command
import streamlit as st

from multiagent_poc.graph.pipeline_graph import build_graph
from multiagent_poc.intents import INTENT_DESCRIPTIONS, Intent

st.set_page_config(page_title="Retail Ops Assistant (PoC)", page_icon="🧭", layout="centered")


@st.cache_resource
def get_graph():
    return build_graph()


def _init_session():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "history" not in st.session_state:
        st.session_state.history = []
    if "pending" not in st.session_state:
        st.session_state.pending = None  # {"question": ..., "reason": ...} while waiting for HITL


def _config():
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def _save_uploaded_pdf(uploaded_file) -> Path:
    tmp_dir = Path(tempfile.gettempdir()) / "multiagent_poc_uploads"
    tmp_dir.mkdir(exist_ok=True)
    dest = tmp_dir / f"{uuid.uuid4()}_{uploaded_file.name}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _run_graph(question: str, attachment_path: Path | None):
    graph = get_graph()
    inputs = {"question": question}
    if attachment_path is not None:
        inputs["attachment_path"] = str(attachment_path)

    try:
        result = graph.invoke(inputs, config=_config())
    except Exception as e:  # AttachmentRejected etc. can still surface here (raised before the try/except node)
        st.session_state.history.append({"question": question, "answer": f"Odrzucono: {e}", "meta": None})
        return

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        st.session_state.pending = {"question": question, "reason": payload.get("reason")}
        return

    st.session_state.history.append(
        {
            "question": question,
            "answer": result.get("answer"),
            "meta": {
                "intent": result.get("intent"),
                "confidence": result.get("confidence"),
                "should_escalate": result.get("should_escalate"),
                "rejected": result.get("rejected"),
                "used_attachment": result.get("used_attachment"),
                "sources": result.get("sources") or [],
            },
        }
    )


def _resume_with_human_answer(human_answer: str):
    graph = get_graph()
    result = graph.invoke(Command(resume=human_answer), config=_config())
    st.session_state.history.append(
        {
            "question": st.session_state.pending["question"],
            "answer": result.get("answer"),
            "meta": {"resolved_by": "człowiek (HITL)", "sources": []},
        }
    )
    st.session_state.pending = None


_init_session()

st.title("🧭 Retail Ops Assistant (PoC)")
st.caption(
    "Multi-agent asystent operacyjny — klasyfikacja intencji, RAG nad runbookami, "
    "walidacja, HITL. Zadaj pytanie jak pracownik sklepu."
)

with st.expander("Katalog intencji obsługiwanych przez system"):
    for intent, desc in INTENT_DESCRIPTIONS.items():
        st.markdown(f"- **{intent.value}**: {desc}")

st.divider()
st.subheader("1. Zadaj pytanie (rola: pracownik)")

if st.session_state.pending is not None:
    st.info(
        "Poprzednie pytanie czeka na odpowiedź operatora w panelu HITL poniżej — "
        "rozwiąż je, zanim zadasz kolejne."
    )
else:
    with st.form("question_form", clear_on_submit=True):
        question = st.text_area("Pytanie", placeholder="np. Dostawca przywiózł inny towar niż zamówiony...")
        uploaded_pdf = st.file_uploader("Załącznik (opcjonalnie, PDF)", type=["pdf"])
        submitted = st.form_submit_button("Wyślij")

    if submitted and question.strip():
        attachment_path = _save_uploaded_pdf(uploaded_pdf) if uploaded_pdf is not None else None
        with st.spinner("Przetwarzanie (walidacja → klasyfikacja → RAG/eskalacja)..."):
            _run_graph(question.strip(), attachment_path)
        st.rerun()

st.divider()
st.subheader("2. Panel HITL (rola: operator/kierownik)")

if st.session_state.pending is None:
    st.caption("Brak pytań oczekujących na eskalację.")
else:
    st.warning(f"**Eskalowane pytanie:** {st.session_state.pending['question']}")
    st.caption(f"Powód eskalacji: {st.session_state.pending['reason']}")
    with st.form("hitl_form"):
        human_answer = st.text_area("Odpowiedź operatora")
        resolve = st.form_submit_button("Wyślij odpowiedź do pracownika")
    if resolve and human_answer.strip():
        _resume_with_human_answer(human_answer.strip())
        st.rerun()

st.divider()
st.subheader("Historia rozmowy")

if not st.session_state.history:
    st.caption("Brak pytań w tej sesji.")
else:
    for item in reversed(st.session_state.history):
        st.markdown(f"**Q:** {item['question']}")
        st.markdown(f"**A:** {item['answer']}")
        if item["meta"]:
            with st.expander("Szczegóły techniczne"):
                meta = item["meta"]
                if meta.get("rejected"):
                    st.write("Odrzucone przez warstwę walidacji.")
                elif "resolved_by" in meta:
                    st.write("Rozwiązane przez: człowiek (HITL)")
                else:
                    confidence = meta.get("confidence")
                    st.write(f"Intencja: `{meta.get('intent')}`")
                    st.write(f"Confidence: `{confidence:.2f}`" if confidence is not None else "Confidence: `—`")
                    st.write(f"Eskalowane: `{meta.get('should_escalate')}`")
                    st.write(f"Użyto załącznika: `{meta.get('used_attachment')}`")
                    if meta.get("sources"):
                        st.write(f"Źródła (runbooki): `{meta['sources']}`")
        st.markdown("---")
