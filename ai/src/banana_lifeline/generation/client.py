"""Shared DeepSeek client with retries.

Calls to the API fail intermittently — a dropped connection, a rate limit, an empty
completion. Observed here in practice: the same request that failed twice succeeded on the
third attempt, unchanged.

That matters because of what "failure" meant downstream. Translation degraded silently to a
glossary substitution, producing a half-Urdu query that still retrieved passages and still
generated an answer; generation returned an empty string and became a refusal indis-
tinguishable from "the corpus has nothing". A farmer would see a worse answer with no
indication anything had gone wrong.

Retrying is the correct response to a transient fault. Degrading is what happens after the
retries are exhausted, and by then it is a real condition worth reporting.
"""

from __future__ import annotations

import time
from typing import Any

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 3.0)

#: Token budget per answer, and it has to be generous.
#:
#: DeepSeek's flash model reasons before it writes, and those reasoning tokens count against
#: max_tokens while never appearing in ``message.content``. Measured on a real five-source
#: prompt: English answers consume ~1,200 completion tokens, Urdu ~3,900 -- Urdu reasoning is
#: simply more token-hungry.
#:
#: At the original 900 the failure was silent and asymmetric: English answers came back
#: truncated mid-sentence (finish_reason "length"), and Urdu came back as an EMPTY string
#: with 900 tokens consumed, because the budget ran out during reasoning. An empty completion
#: then looked exactly like a refusal, so the app told Urdu-speaking farmers it had no
#: information while quietly having plenty.
DEFAULT_MAX_TOKENS = 6000


def get_client(timeout: float = 60.0) -> Any:
    from openai import OpenAI

    from banana_lifeline.secrets import load_credentials

    credentials = load_credentials()
    return OpenAI(
        api_key=credentials.require_deepseek(),
        base_url=credentials.deepseek_base_url,
        timeout=timeout,
    )


def complete(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float = 0.2,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = 60.0,
) -> str:
    """Call DeepSeek, retrying transient failures.

    An empty completion is treated as a failure worth retrying, not as an answer: the model
    returning nothing is a fault, and passing it through as "" turns into a silent refusal.

    Raises after the final attempt so the caller decides how to degrade, rather than being
    handed an empty string that looks like a legitimate result.
    """
    client = get_client(timeout)
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            content = (choice.message.content or "").strip()

            # Truncation is not partial success. A half-written translation retrieves the
            # wrong passages, and a half-written answer stops mid-instruction -- both are
            # worse than a clean failure the caller can report.
            if content and choice.finish_reason != "length":
                return content
            if content:
                last_error = RuntimeError(f"completion truncated at max_tokens={max_tokens}")
                raise last_error

            # Empty with finish_reason "length" means reasoning consumed the whole budget.
            # Retrying identically would burn the same tokens for the same nothing, so the
            # error names the cause instead of pretending the model had no answer.
            if choice.finish_reason == "length":
                raise RuntimeError(
                    f"token budget exhausted during reasoning (max_tokens={max_tokens}); "
                    "raise DEFAULT_MAX_TOKENS"
                )
            last_error = RuntimeError("model returned an empty completion")
        except Exception as exc:
            last_error = exc

        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])

    raise RuntimeError(
        f"DeepSeek failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error
