"""Shared pytest hooks/fixtures for the MemSearch test suite.

The live OpenAI integration tests (``test_core.py``, ``test_embeddings_openai.py``)
call the real API. When the configured key is out of quota or rate-limited, that
is an environment condition, not a code defect. We handle it two ways, both
narrowly scoped to OpenAI quota / rate-limit so genuine bugs still fail:

1. A pre-probe fixture skips those modules up-front when a tiny embed call hits a
   quota/rate-limit error. This covers tests that swallow the embedding error
   internally and then assert on an empty result (e.g. ``index()`` returning 0
   chunks → ``assert n > 0``).
2. A report hook reclassifies any direct quota/rate-limit failure as a skip.
"""

import asyncio
import os

import pytest

_QUOTA_MARKERS = ("insufficient_quota", "ratelimiterror", "rate limit")
_OPENAI_MODULES = ("test_core", "test_embeddings_openai")

# Session-cached probe result: None = not yet probed; "" = ok; str = skip reason.
_probe_skip_reason: list[str | None] = [None]


def _is_quota_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in text for marker in _QUOTA_MARKERS)


@pytest.fixture(autouse=True)
def _skip_openai_modules_on_quota(request):
    module = request.module.__name__.rsplit(".", 1)[-1]
    if module not in _OPENAI_MODULES or not os.environ.get("OPENAI_API_KEY"):
        return
    if _probe_skip_reason[0] is None:
        _probe_skip_reason[0] = ""
        try:
            from memsearch.embeddings.openai import OpenAIEmbedding

            asyncio.run(OpenAIEmbedding().embed(["ping"]))
        except Exception as exc:
            if _is_quota_error(exc):
                _probe_skip_reason[0] = f"OpenAI integration unavailable (quota/rate-limit): {type(exc).__name__}"
    if _probe_skip_reason[0]:
        pytest.skip(_probe_skip_reason[0])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed and call.excinfo is not None:
        exc = call.excinfo.value
        if _is_quota_error(exc):
            rep.outcome = "skipped"
            rep.longrepr = f"OpenAI integration unavailable (quota/rate-limit): {type(exc).__name__}"
