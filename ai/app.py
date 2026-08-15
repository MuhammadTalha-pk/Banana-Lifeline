"""Banana Lifeline — Streamlit demo.

    .venv/Scripts/python -m streamlit run app.py

A thin shell over ``pipeline.diagnose`` and ``pipeline.ask``. Deliberately thin: the point of
a demo is to show what the AI layer actually does, so anything clever here would be showing
the demo instead.

The one piece of real logic is that the UI branches on ``result.action`` rather than on
whether ``disease`` happens to be set. Three of the five actions withhold a diagnosis on
purpose, and rendering a disease name anyway would undo the safety design.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

# Two mistakes are near-guaranteed here, and both used to produce a confusing traceback
# rather than an explanation:
#
#   1. Running `python app.py` instead of `streamlit run app.py`. Streamlit prints a hint but
#      keeps executing in "bare mode", where st.stop() does NOT halt the script -- so the run
#      continued and died later on an unrelated NameError.
#   2. Using Anaconda or the system Python, where this package is not installed.
#
# Both are checked before anything else, and both exit hard.

if not st.runtime.exists():
    venv = Path(__file__).parent / (
        ".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python"
    )
    print(
        """
This is a Streamlit app -- it cannot be run as a plain script.

"""
        f"""  run this instead:
    {venv} -m streamlit run {Path(__file__).name}
""",
        file=sys.stderr,
    )
    raise SystemExit(1)

try:
    from banana_lifeline.config import get_paths
except ModuleNotFoundError as exc:
    if exc.name != "banana_lifeline":
        raise
    venv = Path(__file__).parent / (
        ".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python"
    )
    st.error(
        f"`banana_lifeline` is not installed for this interpreter."
        f"Running: `{sys.executable}` (Python {sys.version.split()[0]})"
        f"Start Streamlit from the project venv instead:"
        f"```{venv} -m streamlit run {Path(__file__).name}```"
    )
    st.stop()
    # st.stop() is a no-op outside a script run, so never fall through to code
    # that depends on the import having succeeded.
    raise SystemExit(1) from None


st.set_page_config(page_title="Banana Lifeline", page_icon="🍌", layout="centered")

FOLLOW_UP_KEYS = (
    "older_leaves_yellow_first",
    "leaves_collapse_around_stem",
    "brown_lines_inside_stem",
    "stem_base_splitting",
)

#: How each decision is presented. Three of the five deliberately show no disease name.
#: ``None`` means no banner at all -- a greeting with a status banner over it looks like a
#: system notice rather than a reply.
ACTION_STYLE: dict[str, tuple[str | None, str]] = {
    "answer": ("success", "Diagnosis"),
    "answer_with_caveat": ("warning", "Likely — but not certain"),
    "ask_follow_up": ("info", "Needs a few checks on the plant"),
    "retake_photo": ("warning", "Please retake the photo"),
    "refer_to_expert": ("error", "Ask an extension officer"),
    "greeting": (None, ""),
    "out_of_scope": (None, ""),
}


@st.cache_resource(show_spinner="Loading models — 30-60 seconds the first time...")
def warm_up() -> bool:
    """Load the models once per server, not once per interaction.

    This used to warm up by asking a real question, which spent a DeepSeek call on every
    restart to do what loading the models does directly.
    """
    from banana_lifeline.pipeline import warm_up as load_models

    load_models()
    return True


def render_sources(citations: list[dict[str, str]]) -> None:
    if not citations:
        return
    with st.expander(f"Sources ({len(citations)})"):
        for citation in citations:
            title = f"**[{citation['n']}] {citation['source']}** — {citation['title']}"
            if citation.get("url"):
                st.markdown(f"{title}  \n{citation['url']}")
            else:
                st.markdown(title)


def render_result(result: object, *, show_header: bool = True) -> None:
    """Render one pipeline result, branching on action rather than on disease."""
    kind, heading = ACTION_STYLE.get(result.action, ("info", result.action))

    if show_header and kind:
        banner = getattr(st, kind)
        label = heading
        if result.disease and result.action in {"answer", "answer_with_caveat", "ask_follow_up"}:
            label = f"{heading}: **{result.disease}** ({result.confidence:.0%} confident)"
        banner(label)

    if result.message:
        st.write(result.message)

    if result.answer:
        st.markdown(result.answer)
        render_sources(result.citations)

    if result.translated_query:
        st.caption(f"Searched as: _{result.translated_query}_")

    if result.safety_violations:
        with st.expander("Safety checks applied"):
            for violation in result.safety_violations:
                st.caption(f"• {violation}")


# --------------------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------------------

with st.sidebar:
    st.title("🍌 Banana Lifeline")
    st.caption("Disease help for banana farmers")

    language = st.radio(
        "Answer language",
        options=["en", "ur"],
        format_func=lambda code: {"en": "English", "ur": "اردو Urdu"}[code],
        horizontal=True,
    )

    st.divider()
    st.markdown("**What it can do**")
    st.caption(
        "Identify Panama disease and Sigatoka from a leaf photo, and answer questions about "
        "planting, soil, irrigation and harvesting."
    )

    st.markdown("**What it will not do**")
    st.caption(
        "Name a disease it is unsure of, invent a spray dose, or claim Panama disease can be "
        "cured. It says so instead."
    )

    st.divider()
    if st.button("Clear conversation"):
        for key in ("messages", "disease", "pending_follow_up"):
            st.session_state.pop(key, None)
        st.rerun()

    paths = get_paths()
    st.caption(f"Knowledge base: {paths.corpus / 'chunks.jsonl'}")


warm_up()

st.session_state.setdefault("messages", [])
st.session_state.setdefault("disease", None)
st.session_state.setdefault("pending_follow_up", None)

# --------------------------------------------------------------------------------------
# Photo
# --------------------------------------------------------------------------------------

st.subheader("1. Photograph a leaf (optional)")
uploaded = st.file_uploader(
    "A clear, close photo of one banana leaf in daylight",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
)

# The uploader is the only evidence a photo exists. `st.session_state.disease` outlives it:
# nothing but the Clear button ever put it back to None, so removing the photo -- or landing
# in a session that still held an old diagnosis -- left later answers claiming a photo that
# was not there. A greeting would end with "Your photo looked healthy" to someone who had
# never uploaded one. State that describes an upload has to be owned by the uploader.
if uploaded is None and st.session_state.get("disease") is not None:
    st.session_state.disease = None
    st.session_state.pending_follow_up = None

if uploaded is not None and st.button("Diagnose this photo", type="primary"):
    from banana_lifeline.pipeline import diagnose

    scratch = Path(tempfile.gettempdir()) / f"upload_{uploaded.name}"
    scratch.write_bytes(uploaded.getbuffer())

    with st.spinner("Looking at the photo..."):
        result = diagnose(scratch, language=language)

    st.session_state.disease = result.disease
    st.session_state.pending_follow_up = (
        result.follow_up_questions if result.action == "ask_follow_up" else None
    )
    st.session_state.messages.append({"role": "assistant", "result": result})

if uploaded is not None:
    st.image(uploaded, caption="Your photo", width=320)

# --------------------------------------------------------------------------------------
# Panama follow-up
# --------------------------------------------------------------------------------------

if st.session_state.pending_follow_up:
    st.subheader("2. Check the plant")
    st.info(
        "A leaf photo cannot confirm Panama disease on its own — its clearest signs are on "
        "the whole plant. Please check these:"
    )

    with st.form("follow_up"):
        answers = {
            key: st.radio(question, ["No", "Yes"], horizontal=True, key=f"fu_{key}") == "Yes"
            for key, question in zip(
                FOLLOW_UP_KEYS, st.session_state.pending_follow_up, strict=False
            )
        }
        if st.form_submit_button("Submit answers", type="primary"):
            from banana_lifeline.generation.answer import answer_follow_up

            message, score = answer_follow_up(answers)
            st.session_state.pending_follow_up = None
            st.session_state.messages.append({"role": "assistant", "follow_up": (message, score)})
            st.rerun()

# --------------------------------------------------------------------------------------
# Conversation
# --------------------------------------------------------------------------------------

st.subheader("Ask a question")
if st.session_state.disease:
    st.caption(f"Answers are focused on **{st.session_state.disease}** from your photo.")

for entry in st.session_state.messages:
    if entry["role"] == "user":
        with st.chat_message("user"):
            st.write(entry["text"])
        continue

    with st.chat_message("assistant", avatar="🍌"):
        if "follow_up" in entry:
            message, score = entry["follow_up"]
            (st.warning if score >= 0.60 else st.info)(f"Match with Panama disease: {score:.0%}")
            st.write(message)
        else:
            render_result(entry["result"])

question = st.chat_input("Type in English or Urdu…")
if question:
    from banana_lifeline.pipeline import ask

    st.session_state.messages.append({"role": "user", "text": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant", avatar="🍌"), st.spinner("Reading the sources..."):
        result = ask(question, disease=st.session_state.disease, language=language)
        render_result(result, show_header=False)

    st.session_state.messages.append({"role": "assistant", "result": result})
