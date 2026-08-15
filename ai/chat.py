"""Talk to Banana Lifeline from the terminal.

    .venv/Scripts/python chat.py

Type a question in English or Urdu and press Enter. Commands:

    /photo <path>   diagnose a photo, then keep asking about it
    /ur  /en        switch the answer language
    /sources        show the sources behind the last answer
    /help  /quit

This is a thin wrapper over ``pipeline.ask`` and ``pipeline.diagnose`` -- the same two
functions a backend would call. Nothing here is special-cased for the terminal, so what you
see is what the app would get.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Same guard as try_it.py: running this with Anaconda or the system Python is the most common
# mistake, and a bare ModuleNotFoundError does not explain it.
try:
    from banana_lifeline.config import get_paths
except ModuleNotFoundError as exc:  # pragma: no cover - startup guard
    if exc.name != "banana_lifeline":
        raise
    here = Path(__file__).parent
    venv = here / (".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python")
    print(
        "banana_lifeline is not installed for this interpreter.\n\n"
        f"  you ran  : {sys.executable}   (Python {sys.version.split()[0]})\n"
        f"  you want : {venv}\n\n"
        f"Try:  {venv} {Path(__file__).name}",
        file=sys.stderr,
    )
    raise SystemExit(1) from None

if hasattr(sys.stdout, "reconfigure"):
    # Windows consoles default to cp1252, which cannot print Urdu.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANNER = """
+----------------------------------------------------------------+
|  Banana Lifeline                                               |
|  Ask about banana diseases, planting, soil, or irrigation.     |
|  English or Urdu.  Type /help for commands, /quit to exit.     |
+----------------------------------------------------------------+
"""

HELP = """
  /photo <path>   diagnose a photo (then ask follow-up questions about it)
  /ur             answer in Urdu
  /en             answer in English
  /sources        show sources for the last answer
  /help           this list
  /quit           exit
"""

FOLLOW_UP_KEYS = (
    "older_leaves_yellow_first",
    "leaves_collapse_around_stem",
    "brown_lines_inside_stem",
    "stem_base_splitting",
)


def wrap(text: str, width: int = 76, indent: str = "  ") -> str:
    import textwrap

    return "\n".join(
        textwrap.fill(line, width=width, initial_indent=indent, subsequent_indent=indent)
        if line.strip()
        else ""
        for line in text.split("\n")
    )


def show_sources(citations: list[dict[str, str]]) -> None:
    if not citations:
        print("  (no sources — the answer was a refusal)")
        return
    for citation in citations:
        print(f"  [{citation['n']}] {citation['source']} — {citation['title']}")
        if citation.get("url"):
            print(f"      {citation['url']}")


def run_follow_up(questions: list[str]) -> None:
    """Walk the farmer through the Panama confirmation questions."""
    from banana_lifeline.generation.answer import answer_follow_up

    print("\n  A leaf photo cannot confirm Panama disease. A few questions:\n")
    responses: dict[str, bool] = {}

    for key, question in zip(FOLLOW_UP_KEYS, questions, strict=False):
        while True:
            reply = input(f"  {question}\n  (y/n) > ").strip().lower()
            if reply in {"y", "yes", "n", "no"}:
                responses[key] = reply.startswith("y")
                break
            print("  Please answer y or n.")
        print()

    message, score = answer_follow_up(responses)
    print(f"  Confidence from these signs: {score:.0%}\n")
    print(wrap(message))


def main() -> int:
    print(BANNER)
    print("  Loading models (30-60 seconds the first time)...", flush=True)

    from banana_lifeline.pipeline import ask, diagnose, warm_up

    # Load the models now rather than on the user's first question.
    warm_up()
    paths = get_paths()
    print(f"  Ready. Knowledge base: {paths.corpus / 'chunks.jsonl'}\n")

    language = "en"
    disease: str | None = None
    last_citations: list[dict[str, str]] = []

    while True:
        try:
            raw = input(f"\n[{language}] you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye.")
            return 0

        if not raw:
            continue

        lowered = raw.lower()
        if lowered in {"/quit", "/exit", "/q"}:
            print("  Bye.")
            return 0
        if lowered == "/help":
            print(HELP)
            continue
        if lowered == "/sources":
            show_sources(last_citations)
            continue
        if lowered in {"/ur", "/urdu"}:
            language = "ur"
            print("  Answering in Urdu.")
            continue
        if lowered in {"/en", "/english"}:
            language = "en"
            print("  Answering in English.")
            continue

        if lowered.startswith("/photo"):
            path_text = raw[len("/photo") :].strip().strip('"')
            if not path_text:
                print("  Usage: /photo C:\\path\\to\\leaf.jpg")
                continue
            image = Path(path_text)
            if not image.is_file():
                print(f"  No such file: {image}")
                continue

            print("  Looking at the photo...", flush=True)
            result = diagnose(image, language=language)

            print(f"\n  [{result.action}]  confidence {result.confidence:.0%}")
            if result.message:
                print(wrap(result.message))

            if result.action == "ask_follow_up":
                run_follow_up(result.follow_up_questions)
                disease = "panama"
            elif result.disease:
                disease = result.disease
                if result.answer:
                    print("\n" + wrap(result.answer))
                    last_citations = result.citations
                    print(f"\n  ({len(result.citations)} sources — type /sources)")
            continue

        # Anything else is a question.
        print("  Thinking...", flush=True)
        result = ask(raw, disease=disease, language=language)

        if result.action in {"refer_to_expert", "greeting", "out_of_scope"}:
            print("\n" + wrap(result.answer or result.message))
            last_citations = []
            continue

        print("\n" + wrap(result.answer))
        last_citations = result.citations
        if result.citations:
            print(f"\n  ({len(result.citations)} sources — type /sources)")
        if result.translated_query:
            print(f"  (searched as: {result.translated_query})")


if __name__ == "__main__":
    raise SystemExit(main())
