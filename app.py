"""Streamlit UI — single page, two sections: employee question form and a
HITL operator panel showing a *shared* queue of every pending escalation
(across all sessions, not just the current one). Run with `streamlit run app.py`.

Session-state model: one graph instance is shared across all users
(st.cache_resource — the LangGraph MemorySaver checkpointer holds every
thread's state internally, keyed by thread_id). Each *question* gets its own
thread_id (not one thread_id per browser session) so an employee's questions
don't collide with each other, and the module-level HITL queue
(hitl/queue.py) tracks pending/resolved escalations across every session in
this process.
"""

from pathlib import Path
import tempfile
import uuid

from langgraph.types import Command
import streamlit as st

from multiagent_poc.graph.pipeline_graph import build_graph, invoke_graph
from multiagent_poc.hitl import queue as hitl_queue
from multiagent_poc.intents import INTENT_DESCRIPTIONS

st.set_page_config(page_title="Retail Ops Assistant (PoC)", page_icon="🧭", layout="centered")

# Visual style loosely inspired by zabka.pl's public marketing site (colors extracted
# from its published CSS: dominant brand green #006420, accent green #00B05A, yellow
# #FFD500). Font is Inter (free, Google Fonts) as a stand-in for the site's licensed
# "TT Commons" — that font isn't ours to redistribute. This is an independent,
# unofficial portfolio project, not affiliated with or endorsed by Żabka Polska sp. z o.o.
# — see the disclaimer banner below. No Żabka logo or other trademarked assets are used.
_BRAND_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.zabka-inspired-banner {
    background: linear-gradient(135deg, #006420 0%, #00B05A 100%);
    color: #ffffff;
    padding: 1.1rem 1.4rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}
.zabka-inspired-banner h1 {
    color: #ffffff !important;
    font-weight: 800;
    font-size: 1.6rem;
    margin: 0 0 0.2rem 0;
}
.zabka-inspired-banner p {
    color: #EDF8ED;
    margin: 0;
    font-size: 0.92rem;
}

.disclaimer-badge {
    display: inline-block;
    background: #FFD500;
    color: #212121;
    font-weight: 600;
    font-size: 0.78rem;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    margin-bottom: 1rem;
}

.stButton > button, .stFormSubmitButton > button {
    background-color: #00B05A;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background-color: #006420;
    color: #ffffff;
}

h2, h3 { color: #006420; }
</style>
"""
st.markdown(_BRAND_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_graph():
    return build_graph()


def _init_session():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "own_pending" not in st.session_state:
        st.session_state.own_pending = None  # {"thread_id": ..., "question": ...}


def _save_uploaded_pdf(uploaded_file) -> Path:
    tmp_dir = Path(tempfile.gettempdir()) / "multiagent_poc_uploads"
    tmp_dir.mkdir(exist_ok=True)
    dest = tmp_dir / f"{uuid.uuid4()}_{uploaded_file.name}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _meta_from_result(result: dict) -> dict:
    return {
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "should_escalate": result.get("should_escalate"),
        "rejected": result.get("rejected"),
        "used_attachment": result.get("used_attachment"),
        "sources": result.get("sources") or [],
        "draft_doc_type": result.get("draft_doc_type"),
        "draft_text": result.get("draft_text"),
    }


def _submit_question(question: str, attachment_path: Path | None):
    graph = get_graph()
    thread_id = str(uuid.uuid4())
    inputs = {"question": question}
    if attachment_path is not None:
        inputs["attachment_path"] = str(attachment_path)
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = invoke_graph(graph, inputs, config=config)
    except Exception as e:  # AttachmentRejected etc. can surface here (raised before the try/except node)
        st.session_state.history.append({"question": question, "answer": f"Odrzucono: {e}", "meta": None})
        return

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if payload.get("kind") == hitl_queue.KIND_DOCUMENT_REVIEW:
            hitl_queue.add_pending_document_review(
                thread_id, question, payload.get("document_type"), payload.get("document_text")
            )
        else:
            hitl_queue.add_pending(thread_id, question, payload.get("reason"))
        st.session_state.own_pending = {"thread_id": thread_id, "question": question}
        return

    st.session_state.history.append({"question": question, "answer": result.get("answer"), "meta": _meta_from_result(result)})


def _check_own_pending_resolution():
    pending = st.session_state.own_pending
    result = hitl_queue.take_resolved(pending["thread_id"])
    if result is None:
        st.toast("Jeszcze brak odpowiedzi operatora.")
        return
    meta = {"resolved_by": "człowiek (HITL)", "sources": [], "draft_doc_type": result.get("draft_doc_type"), "draft_text": result.get("draft_text")}
    st.session_state.history.append({"question": pending["question"], "answer": result.get("answer"), "meta": meta})
    st.session_state.own_pending = None


def _resolve_pending_item(item: hitl_queue.PendingEscalation, human_input: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": item.thread_id}}
    result = invoke_graph(graph, Command(resume=human_input), config=config)
    hitl_queue.set_resolved(item.thread_id, result)
    hitl_queue.pop_pending(item.thread_id)


_init_session()

st.markdown(
    """
    <div class="zabka-inspired-banner">
        <h1>🐸 Retail Ops Assistant (PoC)</h1>
        <p>Multi-agent asystent operacyjny dla franczyzobiorców sieci convenience —
        klasyfikacja intencji, RAG nad runbookami, walidacja, HITL, dwaj agenci per kategoria.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<span class="disclaimer-badge">⚠️ Niezależny projekt portfolio — inspirowany '
    "wizualnie stroną Żabka.pl, niezwiązany z i nieautoryzowany przez Żabka Polska sp. z o.o. "
    "Nie zawiera loga ani innych znaków zastrzeżonych.</span>",
    unsafe_allow_html=True,
)

with st.expander("Katalog intencji obsługiwanych przez system"):
    for intent, desc in INTENT_DESCRIPTIONS.items():
        st.markdown(f"- **{intent.value}**: {desc}")

st.divider()
st.subheader("1. Zadaj pytanie (rola: pracownik)")

if st.session_state.own_pending is not None:
    st.info(f"**Twoje pytanie czeka na operatora:** {st.session_state.own_pending['question']}")
    if st.button("Sprawdź, czy jest odpowiedź"):
        _check_own_pending_resolution()
        st.rerun()
else:
    with st.form("question_form", clear_on_submit=True):
        question = st.text_area("Pytanie", placeholder="np. Dostawca przywiózł inny towar niż zamówiony...")
        uploaded_pdf = st.file_uploader("Załącznik (opcjonalnie, PDF)", type=["pdf"])
        submitted = st.form_submit_button("Wyślij")

    if submitted and question.strip():
        attachment_path = _save_uploaded_pdf(uploaded_pdf) if uploaded_pdf is not None else None
        with st.spinner("Przetwarzanie (walidacja → klasyfikacja → RAG/eskalacja)..."):
            _submit_question(question.strip(), attachment_path)
        st.rerun()

st.divider()
st.subheader("2. Panel HITL (rola: operator/kierownik)")
st.caption(
    "Kolejka współdzielona — widoczne są eskalacje i dokumenty do zatwierdzenia od "
    "wszystkich pracowników, nie tylko z tej sesji."
)

pending_items = hitl_queue.list_pending()
if not pending_items:
    st.caption("Brak pozycji oczekujących w kolejce.")
else:
    st.write(f"**{len(pending_items)}** pozycja(-e) w kolejce.")
    for item in pending_items:
        with st.container(border=True):
            if item.kind == hitl_queue.KIND_DOCUMENT_REVIEW:
                st.warning(f"**Dokument do zatwierdzenia** ({item.document_type}) — pytanie: {item.question}")
                st.caption(f"Zgłoszono: {item.created_at.strftime('%H:%M:%S')}")
                with st.form(f"hitl_form_{item.thread_id}"):
                    edited_text = st.text_area("Treść dokumentu (możesz edytować)", value=item.document_text, key=f"doc_{item.thread_id}", height=200)
                    resolve = st.form_submit_button("Zatwierdź dokument")
                if resolve and edited_text.strip():
                    with st.spinner("Wznawianie grafu..."):
                        _resolve_pending_item(item, edited_text.strip())
                    st.rerun()
            else:
                st.warning(f"**Eskalowane pytanie:** {item.question}")
                st.caption(f"Powód eskalacji: {item.reason} — zgłoszone: {item.created_at.strftime('%H:%M:%S')}")
                with st.form(f"hitl_form_{item.thread_id}"):
                    human_answer = st.text_area("Odpowiedź operatora", key=f"answer_{item.thread_id}")
                    resolve = st.form_submit_button("Wyślij odpowiedź do pracownika")
                if resolve and human_answer.strip():
                    with st.spinner("Wznawianie grafu..."):
                        _resolve_pending_item(item, human_answer.strip())
                    st.rerun()

st.divider()
st.subheader("Historia rozmowy (ta sesja)")

if not st.session_state.history:
    st.caption("Brak pytań w tej sesji.")
else:
    for item in reversed(st.session_state.history):
        st.markdown(f"**Q:** {item['question']}")
        st.markdown(f"**A:** {item['answer']}")
        if item["meta"] and item["meta"].get("draft_text"):
            with st.expander(f"📄 Wygenerowany dokument: {item['meta'].get('draft_doc_type')}"):
                st.text(item["meta"]["draft_text"])
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
