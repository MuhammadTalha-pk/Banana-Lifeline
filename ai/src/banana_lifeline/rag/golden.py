"""The golden evaluation set.

Written against the corpus that actually exists, in the language farmers actually use. Three
design choices matter:

**Farmer phrasing, not textbook phrasing.** A grower writes "leaves going yellow and the
plant is dying", not "progressive chlorosis and vascular wilt". If the golden set is written
in the corpus's own vocabulary, retrieval scores well and then fails on real users.

**Urdu questions are included from the start.** Multilingual retrieval either works or it
does not, and discovering it does not after building everything on top of it is expensive.

**Unanswerable questions are included on purpose.** They test refusal. Without them the
metrics reward a system that always returns its best guess — which in agriculture becomes a
spray recommendation that someone acts on.

The disease questions still need an agronomist's sign-off before these count as ground truth;
they encode my reading of the corpus, not domain authority.
"""

from __future__ import annotations

from banana_lifeline.rag.eval import GoldenQuestion

GOLDEN_SET: list[GoldenQuestion] = [
    # ---------------------------------------------------------------- panama: symptoms ---
    GoldenQuestion(
        question="My banana plant's lower leaves are turning yellow and drooping around the stem",
        language="en",
        disease="panama",
        topic="symptoms",
        expect_terms=["yellow", "wilt", "older leaves", "lower leaves"],
        expect_sources=["fao_fusarium_wilt_manual", "hawaii_banana_ipm", "tnau_panama_wilt"],
    ),
    GoldenQuestion(
        question="I cut the stem and there are brown lines inside. What does that mean?",
        language="en",
        disease="panama",
        topic="symptoms",
        expect_terms=["vascular", "discolo", "brown", "pseudostem", "rhizome"],
        note="The definitive Panama sign, and the one the guided follow-up asks about.",
    ),
    GoldenQuestion(
        question="کیلے کے پودے کے نچلے پتے پیلے ہو رہے ہیں",
        language="ur",
        disease="panama",
        topic="symptoms",
        expect_terms=["yellow", "wilt", "leaves"],
        note="Urdu: the lower leaves of the banana plant are turning yellow.",
    ),
    # ---------------------------------------------------------------- panama: treatment --
    GoldenQuestion(
        question="What spray can cure Panama disease?",
        language="en",
        disease="panama",
        topic="treatment",
        expect_terms=[
            "no cure",
            "no effective",
            "not effective",
            "cannot be controlled",
            "eradicat",
            "no chemical",
        ],
        note="Must retrieve the 'there is no chemical cure' material, not a fungicide list.",
    ),
    GoldenQuestion(
        question="How do I stop Panama disease spreading to my other banana plants?",
        language="en",
        disease="panama",
        topic="prevention",
        expect_terms=["sanitation", "disinfect", "quarantine", "clean", "spread", "tools"],
    ),
    GoldenQuestion(
        question="پاناما بیماری کا علاج کیا ہے؟",
        language="ur",
        disease="panama",
        topic="treatment",
        expect_terms=["no cure", "no chemical", "eradicat", "control", "resistant"],
        note="Urdu: what is the treatment for Panama disease?",
    ),
    GoldenQuestion(
        question="What is TR4 and why is everyone worried about it?",
        language="en",
        disease="panama",
        topic="cause",
        expect_terms=["tropical race 4", "TR4", "cubense", "spread"],
    ),
    GoldenQuestion(
        question="Can I plant bananas again in a field where Panama disease killed the plants?",
        language="en",
        disease="panama",
        topic="prevention",
        expect_terms=["soil", "persist", "years", "replant", "resistant"],
    ),
    # -------------------------------------------------------------- sigatoka: symptoms ---
    GoldenQuestion(
        question="There are dark streaks and spots spreading on my banana leaves",
        language="en",
        disease="sigatoka",
        topic="symptoms",
        expect_terms=["streak", "spot", "lesion", "sigatoka"],
        expect_sources=["aps_black_sigatoka", "hawaii_banana_ipm", "tnau_yellow_sigatoka"],
    ),
    GoldenQuestion(
        question="What is the difference between black sigatoka and yellow sigatoka?",
        language="en",
        disease="sigatoka",
        topic="cause",
        expect_terms=["fijiensis", "musicola", "black", "yellow"],
    ),
    GoldenQuestion(
        question="کیلے کے پتوں پر کالے دھبے اور لکیریں ہیں",
        language="ur",
        disease="sigatoka",
        topic="symptoms",
        expect_terms=["streak", "spot", "lesion"],
        note="Urdu: there are black spots and streaks on the banana leaves.",
    ),
    # -------------------------------------------------------------- sigatoka: treatment --
    GoldenQuestion(
        question="Which fungicide should I use for black sigatoka?",
        language="en",
        disease="sigatoka",
        topic="treatment",
        expect_terms=["fungicide", "spray", "application", "oil", "protectant", "systemic"],
    ),
    GoldenQuestion(
        question="How often do I need to spray for sigatoka?",
        language="en",
        disease="sigatoka",
        topic="treatment",
        expect_terms=["interval", "days", "spray", "application", "cycle", "weekly"],
    ),
    GoldenQuestion(
        question="Does removing infected leaves help control sigatoka?",
        language="en",
        disease="sigatoka",
        topic="prevention",
        expect_terms=["remov", "sanitation", "deleaf", "prun", "infected leaves"],
    ),
    # ------------------------------------------------------------------- cultivation ----
    GoldenQuestion(
        question="How much space should I leave between banana plants?",
        language="en",
        disease=None,
        topic="cultivation",
        expect_terms=["spacing", "metres", "meters", "apart", "density", "plant"],
        expect_sources=["fao_banana_cultivation"],
    ),
    GoldenQuestion(
        question="What kind of soil is best for growing bananas?",
        language="en",
        disease=None,
        topic="cultivation",
        expect_terms=["soil", "drainage", "loam", "fertile", "pH"],
    ),
    GoldenQuestion(
        question="How often should banana plants be watered?",
        language="en",
        disease=None,
        topic="cultivation",
        expect_terms=["irrigat", "water", "rainfall", "moisture"],
    ),
    GoldenQuestion(
        question="کیلے کی فصل کے لیے کون سی مٹی بہترین ہے؟",
        language="ur",
        disease=None,
        topic="cultivation",
        expect_terms=["soil", "drainage", "fertile"],
        note="Urdu: which soil is best for a banana crop?",
    ),
    GoldenQuestion(
        question="When should I remove suckers from my banana plant?",
        language="en",
        disease=None,
        topic="cultivation",
        expect_terms=["sucker", "desucker", "remov", "follower"],
    ),
    # ------------------------------------------------------------------- precautions ----
    GoldenQuestion(
        question="What safety gear do I need when spraying fungicide?",
        language="en",
        disease=None,
        topic="precautions",
        expect_terms=["protective", "equipment", "clothing", "glove", "mask", "safety"],
        note="Underpins the hard-coded PPE rule in generation.",
    ),
    # ---------------------------------------------------- unanswerable: refusal tests ----
    GoldenQuestion(
        question="What is the current market price of bananas in Lahore?",
        language="en",
        disease=None,
        topic=None,
        unanswerable=True,
        note="Market prices are nowhere in an agronomy corpus. Must refuse, not improvise.",
    ),
    GoldenQuestion(
        question="Which bank gives the best agricultural loan in Punjab?",
        language="en",
        disease=None,
        topic=None,
        unanswerable=True,
        note="Finance question. A fluent wrong answer here damages trust in everything else.",
    ),
    GoldenQuestion(
        question="How do I treat foot and mouth disease in my cattle?",
        language="en",
        disease=None,
        topic=None,
        unanswerable=True,
        note="Right domain, wrong species. Tests that 'disease' vocabulary alone is not "
        "enough to trigger an answer.",
    ),
    GoldenQuestion(
        question="کیلے کی آج کی قیمت کیا ہے؟",
        language="ur",
        disease=None,
        topic=None,
        unanswerable=True,
        note="Urdu: what is today's banana price? Refusal must work in both languages.",
    ),
    GoldenQuestion(
        question="What fertiliser dose should I apply to my wheat crop?",
        language="en",
        disease=None,
        topic=None,
        unanswerable=True,
        note="Different crop. The corpus has fertiliser guidance for bananas, so this tests "
        "that topical similarity does not override subject mismatch.",
    ),
]
