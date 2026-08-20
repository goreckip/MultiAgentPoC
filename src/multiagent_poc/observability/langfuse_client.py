"""Langfuse Cloud observability wiring (architecture layer 7).

Two mechanisms, used together:
- `observe()` decorator (re-exported) on key functions creates nested spans
  automatically via contextvars — as long as the call chain is synchronous
  and starts under one `@observe`-decorated entry point (see
  graph/pipeline_graph.py::invoke_graph), everything called underneath nests
  into a single trace per question.
- `get_callback_handler()` is passed explicitly into LangChain LLM calls
  (ChatOllama.invoke(..., config={"callbacks": [...]})), which is what
  actually captures token counts/latency for the generation calls. The
  `observe()` decorator alone does not extract LLM-specific metrics from a
  plain function return value.

Credentials come from LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST
in .env (see config.py) — the langfuse SDK reads these from the environment
directly via its default client singleton.
"""

from langfuse import observe  # noqa: F401 — re-exported for use elsewhere
from langfuse.langchain import CallbackHandler

_handler: CallbackHandler | None = None


def get_callback_handler() -> CallbackHandler:
    global _handler
    if _handler is None:
        _handler = CallbackHandler()
    return _handler
