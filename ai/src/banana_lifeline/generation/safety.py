"""Safety rules, enforced in code.

A language model asked politely to be careful is not a safety mechanism. Every rule here is
checked against generated text after the fact, because prompts fail silently and a farmer
acting on a fabricated fungicide dose does not get a second chance at the season.

Each rule exists because of a specific, plausible failure:

**Panama has no chemical cure.** Every model has read thousands of "banana disease → apply
fungicide" documents. Asked how to treat Panama, the fluent completion is a spray schedule,
and it is wrong: Fusarium wilt is a soil-borne vascular pathogen that no foliar treatment
reaches. A farmer who sprays loses the money *and* the crop, having skipped containment
while the disease spread.

**Dosages must be quoted, never computed.** "2 litres per hectare" is the kind of detail
models interpolate confidently and incorrectly. Any figure not present verbatim in a
retrieved passage is stripped.

**Region caveats.** Pesticide registration is jurisdiction-specific and none of the corpus
is Pakistani. Advice from an Indian or American source may name a product that is
unregistered, or banned, locally.

**TR4 escalates.** Tropical Race 4 is a quarantine pathogen. Handling it as a private
problem is how it reaches the next farm.
"""

# E501: several regexes and the refusal strings read worse when wrapped.
# RUF001: the Urdu refusal text legitimately contains an Arabic full stop.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    BLOCK = "block"  # the answer must not be shown as written
    AMEND = "amend"  # the answer is usable once text is added or removed
    NOTE = "note"  # informational


@dataclass(slots=True)
class Violation:
    rule: str
    severity: Severity
    detail: str
    suggested_text: str = ""


@dataclass(slots=True)
class SafetyResult:
    """Outcome of checking one generated answer."""

    violations: list[Violation] = field(default_factory=list)
    amended_text: str = ""

    @property
    def blocked(self) -> bool:
        return any(v.severity is Severity.BLOCK for v in self.violations)

    @property
    def is_clean(self) -> bool:
        return not self.violations


# Words that describe applying a chemical to cure something.
_TREATMENT_VERBS = re.compile(
    r"\b(spray|apply|applicat|drench|treat with|fungicid|dose|dosage|"
    r"propiconazole|tridemorph|mancozeb|chlorothalonil|carbendazim|azoxystrobin|"
    r"tebuconazole|bordeaux)\w*",
    re.IGNORECASE,
)

# Language claiming a cure.
_CURE_CLAIMS = re.compile(
    r"\b(cure[sd]?|curing|eradicat\w+|eliminat\w+|get rid of|will heal|recover fully)\b",
    re.IGNORECASE,
)

# Quantities that look like an application rate.
_DOSAGE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|g|kg|ml|l|litre|liter|gram|gm|oz)\b"
    r"(?:\s*(?:/|per)\s*(?:ha|hectare|acre|l|litre|liter|plant|tree|m2))?",
    re.IGNORECASE,
)

_PPE_MENTIONS = re.compile(
    r"\b(protective|glove|mask|goggle|respirator|cover(ed|ing)? (your )?skin|ppe)\b",
    re.IGNORECASE,
)

_PREHARVEST = re.compile(
    r"\b(pre-?harvest interval|phi|days? before harvest|withholding)\b", re.IGNORECASE
)

_TR4 = re.compile(r"\b(tr4|tropical race 4|race 4)\b", re.IGNORECASE)

PANAMA_CONTAINMENT_TEXT = (
    "There is no chemical cure for Panama disease. Fungicides do not reach the fungus, "
    "which lives in the soil and inside the plant. What works is stopping its spread: "
    "do not move soil, suckers, or tools from the affected area; clean tools with "
    "disinfectant between plants; improve drainage; and do not replant a susceptible "
    "variety in that soil."
)

TR4_ESCALATION_TEXT = (
    "Tropical Race 4 (TR4) is a notifiable quarantine disease. If you suspect it, report it "
    "to your local agricultural extension office or plant protection department. Do not move "
    "plants, suckers, soil, or equipment off the farm."
)

REGION_CAVEAT_TEXT = (
    "This guidance comes from sources outside Pakistan. Product registration differs by "
    "country, so confirm with your local agriculture department that any chemical named here "
    "is approved for use on bananas in Pakistan before buying or applying it."
)


def check_panama_no_cure(text: str, disease: str | None) -> list[Violation]:
    """Block any chemical cure offered for Panama disease."""
    if disease != "panama":
        return []

    violations: list[Violation] = []

    treatment = _TREATMENT_VERBS.search(text)
    cure = _CURE_CLAIMS.search(text)

    # "eradication" appears legitimately in containment guidance (destroying affected
    # plants), so a cure claim only counts when paired with chemical treatment language.
    if treatment and cure:
        violations.append(
            Violation(
                rule="panama_no_cure",
                severity=Severity.BLOCK,
                detail=f"chemical cure implied for Panama: {treatment.group(0)!r} + "
                f"{cure.group(0)!r}",
                suggested_text=PANAMA_CONTAINMENT_TEXT,
            )
        )
    elif treatment and not re.search(
        r"no (chemical |effective )?(cure|treatment|control)", text, re.IGNORECASE
    ):
        violations.append(
            Violation(
                rule="panama_no_cure",
                severity=Severity.AMEND,
                detail=f"treatment language for Panama without a 'no cure' statement: "
                f"{treatment.group(0)!r}",
                suggested_text=PANAMA_CONTAINMENT_TEXT,
            )
        )

    return violations


def check_dosages_are_grounded(text: str, sources: list[str]) -> list[Violation]:
    """Every quantity must appear verbatim in a retrieved passage.

    The model may quote a dose; it may not calculate or recall one.
    """
    haystack = " ".join(sources).lower()
    violations: list[Violation] = []

    for match in _DOSAGE.finditer(text):
        quantity = match.group(0).strip()
        normalised = re.sub(r"\s+", " ", quantity.lower())
        if normalised not in haystack and normalised.replace(" ", "") not in haystack.replace(
            " ", ""
        ):
            violations.append(
                Violation(
                    rule="ungrounded_dosage",
                    severity=Severity.BLOCK,
                    detail=f"dosage {quantity!r} does not appear in any retrieved source",
                )
            )

    return violations


def check_chemical_safety(text: str) -> list[Violation]:
    """Chemical advice must carry PPE and pre-harvest interval warnings."""
    if not _TREATMENT_VERBS.search(text):
        return []

    violations: list[Violation] = []
    if not _PPE_MENTIONS.search(text):
        violations.append(
            Violation(
                rule="missing_ppe",
                severity=Severity.AMEND,
                detail="chemical application described without protective equipment advice",
                suggested_text="Wear gloves, a mask, and clothing that covers your skin when "
                "mixing or spraying. Do not spray into the wind.",
            )
        )
    if not _PREHARVEST.search(text):
        violations.append(
            Violation(
                rule="missing_preharvest_interval",
                severity=Severity.AMEND,
                detail="chemical application described without a pre-harvest interval",
                suggested_text="Check the product label for how many days must pass between "
                "the last spray and harvest.",
            )
        )

    return violations


def check_tr4_escalation(text: str) -> list[Violation]:
    if not _TR4.search(text):
        return []
    if re.search(
        r"\b(report|notifiable|quarantine|authorit|extension office)\w*", text, re.IGNORECASE
    ):
        return []

    return [
        Violation(
            rule="tr4_not_escalated",
            severity=Severity.AMEND,
            detail="TR4 discussed without official reporting guidance",
            suggested_text=TR4_ESCALATION_TEXT,
        )
    ]


def check_region_applicability(text: str, regions: list[str]) -> list[Violation]:
    """Flag chemical advice sourced entirely from outside Pakistan."""
    if not _TREATMENT_VERBS.search(text):
        return []
    if any(region.lower() in {"pakistan", "pk"} for region in regions):
        return []

    return [
        Violation(
            rule="foreign_region_advice",
            severity=Severity.AMEND,
            detail=f"chemical advice drawn from non-Pakistani sources: {sorted(set(regions))}",
            suggested_text=REGION_CAVEAT_TEXT,
        )
    ]


def enforce(
    text: str,
    *,
    disease: str | None,
    source_texts: list[str],
    source_regions: list[str],
) -> SafetyResult:
    """Run every rule and produce the text that is actually safe to show."""
    violations: list[Violation] = []
    violations += check_panama_no_cure(text, disease)
    violations += check_dosages_are_grounded(text, source_texts)
    violations += check_chemical_safety(text)
    violations += check_tr4_escalation(text)
    violations += check_region_applicability(text, source_regions)

    result = SafetyResult(violations=violations)

    if result.blocked:
        # A blocked answer is replaced, not patched: the reasoning that produced it was
        # wrong, so editing its wording would leave the error in place.
        blocking = next(v for v in violations if v.severity is Severity.BLOCK)
        result.amended_text = blocking.suggested_text or (
            "I cannot give reliable guidance on this. Please consult a local agricultural "
            "extension officer."
        )
        return result

    additions = [v.suggested_text for v in violations if v.suggested_text]
    result.amended_text = "\n\n".join([text, *additions]) if additions else text
    return result
