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
in .env (see config.py). The client is constructed explicitly here rather than
left to the SDK's implicit singleton, because it needs a mask (below).
"""

import re

from langfuse import Langfuse, get_client, observe  # noqa: F401 — observe is re-exported

from langfuse.langchain import CallbackHandler

# Kept in sync with validation/input_validation.py by test_langfuse_mask.py —
# an 11-digit run is the shape of a Polish PESEL.
_PESEL_RE = re.compile(r"\b\d{11}\b")
MASKED = "[zamaskowane]"


def mask_sensitive(data):
    """Last line of defence before anything leaves the machine.

    The input layer already rejects a question containing a PESEL, but rejection
    happens *inside* `handle_question`, which is itself `@observe`-decorated:
    the decorator records the function's arguments when the call starts, so the
    offending question is captured as span input before validation ever runs and
    would be shipped to Langfuse Cloud attached to the failed span.

    Masking at the client closes that gap for every span, input and output
    alike, without the rest of the code having to remember to sanitise.
    """
    if isinstance(data, str):
        return _PESEL_RE.sub(MASKED, data)
    if isinstance(data, dict):
        return {k: mask_sensitive(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return type(data)(mask_sensitive(v) for v in data)
    return data


_client: Langfuse | None = None
_handler: CallbackHandler | None = None


def get_langfuse() -> Langfuse:
    """Configures the SDK singleton with the mask. Constructing `Langfuse(...)`
    registers it as the default client, so `@observe` and the LangChain callback
    handler both pick the mask up without being passed anything.
    """
    global _client
    if _client is None:
        _client = Langfuse(mask=mask_sensitive)
    return _client


def get_callback_handler() -> CallbackHandler:
    global _handler
    if _handler is None:
        get_langfuse()  # ensure the masked client exists before the handler binds
        _handler = CallbackHandler()
    return _handler


# Configure at import time: `@observe` decorators elsewhere resolve the default
# client lazily, but the first traced call can happen before anything asks for a
# callback handler, so the mask has to be registered as early as possible.
get_langfuse()
