"""Intent routing — decide whether a message needs the knowledge base at all.

Every message used to go straight into retrieval. Typing "hi" therefore searched an agronomy
corpus for the word "hi", found five passages that were merely *about bananas*, and handed
them to the model, which dutifully wrote several paragraphs on plantation renewal cycles and
protective equipment. The answer was correct, cited, and completely wrong as a reply.

So a message is routed first:

    greeting      -> answered directly, no retrieval, no API cost
    technical     -> the RAG pipeline, unchanged
    out_of_scope  -> told plainly that this system only knows bananas

**The routing is asymmetric on purpose.** Misrouting a real question into a greeting is a
farmer with a dying crop being told "hello, how can I help?" — the failure this whole system
exists to avoid. Misrouting a greeting into retrieval costs a wasted search that refuses.
Every uncertain case therefore resolves to ``technical``: unknown model output, a malformed
reply, a network failure, an empty string. The router can only ever *skip* work it is sure is
skippable.

Nor is ``out_of_scope`` load-bearing. Retrieval already refuses questions the corpus cannot
answer, measured at 80% on the golden set. This layer exists to make that refusal *fast and
clearly worded* for the obvious cases, not to be the thing standing between a farmer and a
bad answer.

**Most messages never reach the model.** A DeepSeek call before every question would add a
round-trip to the one path that is already the slowest. Two rule-based fast paths take the
common cases for free: a message containing any farming vocabulary is technical without
asking, and a message that is nothing but greeting words is a greeting without asking. Only
genuinely ambiguous text — "what can you do?", "are you there?" — costs a call.
"""

# RUF001/RUF003: the Urdu strings and the comments about them legitimately contain
# Arabic-script punctuation.
# E501: the reply strings are prose shown verbatim to a farmer; wrapping them in source
# would put the line breaks in the wrong places.
# ruff: noqa: RUF001, RUF003, E501

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

DEFAULT_MODEL = "deepseek-v4-flash"


class Intent(StrEnum):
    """What kind of message this is, and therefore which path it takes."""

    GREETING = "greeting"
    """A greeting, thanks, or goodbye. Answered directly."""

    TECHNICAL = "technical"
    """A question about bananas or farming. Goes to retrieval. The default when unsure."""

    OUT_OF_SCOPE = "out_of_scope"
    """Nothing to do with bananas or farming. Declined without searching."""


@dataclass(slots=True)
class Classification:
    """The routing decision plus why it was made, so a misroute can be traced."""

    intent: Intent
    reason: str
    used_model: bool = False

    @property
    def needs_retrieval(self) -> bool:
        return self.intent is Intent.TECHNICAL


# --------------------------------------------------------------------------------------
# Fast path 1 — farming vocabulary means technical, no model call
# --------------------------------------------------------------------------------------

#: Subjects that are farming-adjacent but are NOT this corpus. A question naming one of
#: these skips the fast path entirely and goes to the model, whatever farming words sit
#: beside it.
#:
#: This exists because the vocabulary check alone cannot tell "what fertiliser dose for my
#: wheat crop" from "what fertiliser dose for my bananas" -- both are full of farming terms,
#: and only one has an answer here. Matched on word boundaries, because "price" contains
#: "rice" and "operate" contains "rate".
_OTHER_SUBJECTS: tuple[str, ...] = (
    "wheat", "rice", "paddy", "maize", "cotton", "sugarcane", "mango", "citrus",
    "orange", "potato", "tomato", "onion", "chilli", "pulses", "gram", "millet",
    "cattle", "cow", "cows", "buffalo", "goat", "sheep", "poultry", "chicken",
    "livestock", "fish", "dairy", "milk",
    "price", "prices", "rate", "rates", "market", "mandi", "sell", "selling", "buy",
    "loan", "loans", "bank", "credit", "subsidy", "insurance", "tax", "export",
    "tractor", "machinery", "fuel", "diesel", "labour", "wages",
)

_OTHER_SUBJECT_RE = re.compile(
    r"\b(" + "|".join(_OTHER_SUBJECTS) + r")\b", re.IGNORECASE
)

#: The same list in Urdu, matched as substrings -- word boundaries do not work usefully in
#: Arabic script. Needed because the Urdu domain terms ("کیلے") fast-path a question to
#: technical, so "کیلے کی آج کی قیمت کیا ہے؟" ("what is today's banana price") reached
#: retrieval as a banana question when the corpus holds no prices at all.
_URDU_OTHER_SUBJECTS: tuple[str, ...] = (
    "قیمت", "قیمتیں", "نرخ", "منڈی", "بازار", "بھاؤ",
    "قرض", "بینک", "سبسڈی", "بیمہ", "ٹیکس",
    "گندم", "چاول", "دھان", "مکئی", "کپاس", "گنا", "آم",
    "مویشی", "گائے", "بھینس", "بکری", "مرغی", "دودھ",
    "ٹریکٹر", "ڈیزل", "مزدوری",
)

#: Substrings that settle it. Deliberately generous: a false "technical" costs one search
#: that refuses, while a false "greeting" costs a farmer their answer.
#:
#: Stems rather than whole words, so "irrigat" covers irrigate/irrigation/irrigated and
#: "fertil" covers fertiliser/fertilizer/fertility without listing each.
_DOMAIN_TERMS: tuple[str, ...] = (
    # the crop
    "banana", "plantain", "musa", "kela", "kelay", "orchard", "plantation",
    # the diseases
    "sigatoka", "panama", "fusarium", "tr4", "wilt", "fungus", "fungal", "blight",
    "nematode", "weevil", "aphid", "borer", "virus", "mosaic", "rot",
    # the plant
    "leaf", "leaves", "plant", "crop", "sucker", "pseudostem", "stem", "trunk",
    "root", "fruit", "bunch", "flower", "seedling", "cultivar", "variety",
    # what farmers do
    "soil", "water", "irrigat", "fertil", "manure", "compost", "mulch", "drainage",
    "spray", "pesticide", "fungicide", "herbicide", "chemical", "dose", "dosage",
    "prune", "harvest", "ripen", "sow", "grow", "farm", "field", "acre", "hectare",
    "spacing", "weed", "nutrient", "potassium", "nitrogen", "phosphor",
    # what is wrong
    "disease", "symptom", "spot", "streak", "yellow", "brown", "black", "dying",
    "sick", "infect", "treat", "cure", "prevent", "pest", "damage",
)

#: Urdu domain vocabulary, taken from the translation glossary so the two cannot drift.
#: An Urdu question must reach retrieval as surely as an English one.
_URDU_DOMAIN_TERMS: tuple[str, ...] = (
    "کیلا", "کیلے", "پتہ", "پتے", "پتوں", "بیماری", "دھبے", "دھبہ", "لکیریں",
    "مرجھاؤ", "تنا", "جڑ", "پھپھوندی", "دوا", "سپرے", "مٹی", "پانی", "کھاد",
    "فصل", "پودا", "پودے", "علاج", "پاناما", "سگاٹوکا", "کاشت", "کٹائی",
)


# --------------------------------------------------------------------------------------
# Fast path 2 — nothing but greeting words means greeting, no model call
# --------------------------------------------------------------------------------------

#: Single tokens that carry no question. A message made *entirely* of these is a greeting.
#: Checked only after the domain scan, so "hi my banana leaves are yellow" is technical.
_GREETING_TOKENS: frozenset[str] = frozenset(
    {
        # English
        "hi", "hii", "hiii", "hey", "heyy", "hello", "helo", "hallo", "yo",
        "good", "morning", "afternoon", "evening", "night", "day",
        "thanks", "thank", "thanx", "thx", "ty", "cheers", "welcome",
        "bye", "goodbye", "cya", "later", "ok", "okay", "okey", "k", "sure",
        "there", "you", "u", "how", "are", "is", "it", "going", "doing",
        "please", "sir", "madam", "bhai",
        # Roman Urdu
        "salam", "salaam", "slam", "assalam", "asalam", "assalamualaikum",
        "asalamualaikum", "assalamualikum", "walaikum", "alaikum", "alaykum",
        "aoa", "adab", "shukriya", "shukria", "shukriah", "khuda", "hafiz",
        "kya", "haal", "hai", "kaise", "ho", "theek", "acha", "achha", "jee", "ji",
        # Urdu script
        "السلام", "علیکم", "سلام", "ہیلو", "آداب", "شکریہ", "خدا", "حافظ",
        "کیسے", "ہیں", "آپ", "ٹھیک", "اچھا", "جی", "ہاں",
    }
)

#: Questions about the assistant itself. Neither farming nor small talk, and a third
#: category for them would earn nothing: the greeting already answers "what can you do".
#:
#: These are here because the model got them badly wrong. Asked to route "can you help me"
#: it answered out_of_scope, so a farmer opening with that was told "I only know about
#: bananas -- I cannot help with that." Exact phrases only, never token matching, so
#: "can you help me with my leaves" is untouched (and caught by the domain scan first).
_ABOUT_PHRASES: frozenset[str] = frozenset(
    {
        "who are you", "what are you", "who r u", "what r u",
        "what can you do", "what do you do", "what can u do",
        "what is this", "what's this", "whats this", "what is this app",
        "how do you work", "how does this work", "how do i use this",
        "can you help", "can you help me", "can u help", "can u help me",
        "how can you help", "how can you help me", "can you help me please",
        "what is your name", "whats your name", "what's your name",
        "help", "what do you know",
        "آپ کون ہیں", "آپ کیا کر سکتے ہیں", "یہ کیا ہے", "مدد",
    }
)

#: Whole phrases that are greetings even though a token check would pass them anyway.
#: Kept explicit because they are what people actually type first.
_GREETING_PHRASES: frozenset[str] = frozenset(
    {
        "hi", "hello", "hey", "yo", "salam", "aoa", "adab",
        "good morning", "good afternoon", "good evening",
        "how are you", "how are you doing", "whats up", "what's up", "sup",
        "thank you", "thanks", "thank you so much", "ok thanks", "okay thanks",
        "bye", "goodbye", "good bye", "see you",
        "assalam o alaikum", "assalamu alaikum", "asalam o alaikum",
        "السلام علیکم", "سلام", "شکریہ", "خدا حافظ", "آپ کیسے ہیں",
    }
)

#: Punctuation to drop before matching, Latin and Arabic-script alike. A message ending in
#: "؟" or "۔" is the same message without it.
#:
#: Python's ``\w`` is Unicode-aware and already keeps Urdu letters, so this must NOT also
#: whitelist the Arabic block: that block contains "؟" and "۔" themselves, and whitelisting
#: it left Urdu greetings with their punctuation attached and failing every exact match.
_PUNCTUATION = re.compile(r"[^\w\s']+", re.UNICODE)


def normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Matching happens on this form."""
    stripped = _PUNCTUATION.sub(" ", text.lower())
    return re.sub(r"\s+", " ", stripped).strip()


def names_other_subject(text: str) -> bool:
    """Whether the message names a crop, animal, or topic this corpus does not cover."""
    return bool(_OTHER_SUBJECT_RE.search(text)) or any(
        term in text for term in _URDU_OTHER_SUBJECTS
    )


def looks_technical(text: str) -> bool:
    """Whether the message is confidently about banana growing, on rules alone.

    Returns False when another subject is named, even alongside farming vocabulary. The
    model decides those: "what fertiliser for my wheat" and "what fertiliser for my bananas"
    are indistinguishable to a keyword scan and have opposite correct answers.
    """
    if names_other_subject(text):
        return False
    lowered = text.lower()
    return any(term in lowered for term in _DOMAIN_TERMS) or any(
        term in text for term in _URDU_DOMAIN_TERMS
    )


def looks_like_greeting(text: str) -> bool:
    """Whether the message is made of nothing but greeting words.

    The all-tokens rule is what makes this safe. "hi" and "hello there" pass; "hi, is this
    normal on my leaves" does not, because "normal" and "leaves" are not greeting tokens --
    and it would already have been caught by the domain scan regardless.
    """
    cleaned = normalise(text)
    if not cleaned:
        return False
    if cleaned in _GREETING_PHRASES or cleaned in _ABOUT_PHRASES:
        return True

    tokens = cleaned.split()
    # An unbounded token check would classify a long rambling message as a greeting on the
    # strength of its filler words. Real greetings are short.
    if len(tokens) > 6:
        return False
    return all(token in _GREETING_TOKENS for token in tokens)


# --------------------------------------------------------------------------------------
# Slow path — ask the model
# --------------------------------------------------------------------------------------

_SYSTEM_PROMPT = """You route messages in an assistant for banana farmers in Pakistan.

Reply with ONE word and nothing else:

greeting - a greeting, thanks, goodbye, small talk, OR a question about you and what you can \
do, such as "who are you", "what can you do", "can you help me"
technical - growing bananas or their diseases: symptoms, soil, planting, irrigation, \
fertiliser, pests, harvesting. Vague ones like "any tips?" and follow-ups like "how much?" \
count, because the farmer is standing in a banana field.
out_of_scope - anything else, INCLUDING other farming topics this assistant does not cover: \
other crops (wheat, rice, cotton, mango), livestock, market prices, loans, subsidies, \
machinery. Also sport, politics, celebrities, coding, and general trivia.

Two things to get right:
- A question about a DIFFERENT crop or about animals is out_of_scope even though it is \
farming. This assistant only knows bananas.
- Never answer out_of_scope for a question about you or about what this assistant does. \
Someone asking "can you help me" is asking to be helped.

If a question could plausibly be about bananas, answer technical.
Reply with the single word only."""


@lru_cache(maxsize=512)
def _classify_via_deepseek(text: str, model: str) -> str:
    from banana_lifeline.generation.client import complete

    return complete(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        model=model,
        temperature=0,  # routing must be reproducible
        # A one-word answer, but this model reasons before it writes and those tokens come
        # out of the same budget. 2000 is the figure translation needed for the same reason.
        max_tokens=2000,
        timeout=30,
    )


def _parse(reply: str) -> Intent | None:
    """Read an intent out of the model's reply, or None if it did not name exactly one."""
    lowered = reply.strip().lower()
    matched = [intent for intent in Intent if intent.value in lowered]
    return matched[0] if len(matched) == 1 else None


def classify(
    text: str,
    *,
    model: str = DEFAULT_MODEL,
    use_model: bool = True,
) -> Classification:
    """Route one message.

    Resolves to ``TECHNICAL`` for anything it cannot settle, including every failure mode of
    the model call. Retrieval refuses safely; a wrongly-skipped question does not.
    """
    if not text.strip():
        return Classification(Intent.GREETING, "empty message")

    if looks_technical(text):
        return Classification(Intent.TECHNICAL, "farming vocabulary present")

    if looks_like_greeting(text):
        return Classification(Intent.GREETING, "greeting words only")

    if not use_model:
        return Classification(Intent.TECHNICAL, "no rule matched; model routing disabled")

    try:
        reply = _classify_via_deepseek(text, model)
    except Exception as exc:
        return Classification(Intent.TECHNICAL, f"routing unavailable: {type(exc).__name__}")

    intent = _parse(reply)
    if intent is None:
        return Classification(Intent.TECHNICAL, f"unreadable routing reply: {reply[:40]!r}")

    return Classification(intent, "model routed", used_model=True)


# --------------------------------------------------------------------------------------
# What a non-technical message gets told
# --------------------------------------------------------------------------------------

GREETING_TEXT = {
    "en": "Hello. I help banana farmers.\n\nYou can:\n\n- **Send a photo of a leaf** and I will check it for Panama disease or Sigatoka.\n- **Ask a question** about planting, spacing, soil, irrigation, fertiliser, or harvesting.\n\nWhat is happening with your plants?",
    "ur": "السلام علیکم۔ میں کیلے کے کاشتکاروں کی مدد کرتا ہوں۔\n\nآپ یہ کر سکتے ہیں:\n\n- **پتے کی تصویر بھیجیں** — میں پاناما یا سگاٹوکا کی جانچ کروں گا۔\n- **سوال پوچھیں** — پودے لگانا، فاصلہ، مٹی، آبپاشی، کھاد یا کٹائی کے بارے میں۔\n\nآپ کے پودوں کے ساتھ کیا مسئلہ ہے؟",
}

OUT_OF_SCOPE_TEXT = {
    "en": "I only know about bananas — the diseases that affect them and how they are grown. I cannot help with that.\n\nAsk me about leaf symptoms, planting, soil, irrigation, fertiliser, or harvesting — or send a photo of a leaf.",
    "ur": "میں صرف کیلے کے بارے میں جانتا ہوں — اس کی بیماریاں اور اس کی کاشت۔ اس معاملے میں میں مدد نہیں کر سکتا۔\n\nمجھ سے پتوں کی علامات، پودے لگانے، مٹی، آبپاشی، کھاد یا کٹائی کے بارے میں پوچھیں — یا پتے کی تصویر بھیجیں۔",
}

#: Disease names as a farmer reading Urdu should see them.
_DISEASE_UR = {"healthy": "صحت مند", "sigatoka": "سگاٹوکا", "panama": "پاناما"}

_PHOTO_CONTEXT = {
    "en": {
        "healthy": "\n\nYour photo looked healthy. Ask me anything about keeping it that way.",
        "other": "\n\nYour photo was identified as **{disease}** — ask me anything about it.",
    },
    "ur": {
        "healthy": "\n\nآپ کی تصویر صحت مند دکھائی دی۔ اسے ایسا ہی رکھنے کے بارے میں کچھ بھی پوچھیں۔",
        "other": "\n\nآپ کی تصویر میں **{disease}** کی نشاندہی ہوئی — اس کے بارے میں کچھ بھی پوچھیں۔",
    },
}


def greeting_text(language: str = "en", disease: str | None = None) -> str:
    """The greeting, carrying forward a diagnosis if the farmer has already sent a photo.

    Dropping that context would make the assistant look like it had forgotten the photo it
    was just shown.
    """
    code = language if language in GREETING_TEXT else "en"
    text = GREETING_TEXT[code]

    if not disease:
        return text

    templates = _PHOTO_CONTEXT[code]
    if disease == "healthy":
        return text + templates["healthy"]

    shown = _DISEASE_UR.get(disease, disease) if code == "ur" else disease
    return text + templates["other"].format(disease=shown)


def out_of_scope_text(language: str = "en") -> str:
    return OUT_OF_SCOPE_TEXT.get(language, OUT_OF_SCOPE_TEXT["en"])
