"""The authoritative source registry.

Every document that can ground an answer is declared here, with its provenance. This is
deliberately a hand-curated list rather than a crawl: a farmer acting on a fungicide dose
needs that dose to come from FAO or a university extension service, not from whatever a
search engine surfaced.

Two fields carry more weight than they look like they do:

``region``
    Pesticide registration is jurisdiction-specific. A product recommended by a Tamil Nadu
    extension page may be unregistered, or banned, in Pakistan. None of the current sources
    are Pakistani, so retrieval can prefer local guidance where it exists and generation can
    add a "verify local registration" caveat where it does not.

``authority``
    Where two sources disagree, the tier decides which wins. An FAO technical manual
    outranks a summary page.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class FetchMode(StrEnum):
    """How a source has to be retrieved.

    Not cosmetic: only one of the eight is a direct PDF link. The rest hide behind landing
    pages or table-of-contents pages, and treating them all as direct downloads is how you
    end up indexing navigation chrome instead of agronomy.
    """

    DIRECT = "direct"
    """URL is the document itself."""

    LANDING = "landing"
    """HTML page that links to the real document; follow one hop to a PDF."""

    PAGE = "page"
    """A single HTML page that is itself the content."""

    INDEX = "index"
    """A table-of-contents page whose linked sub-pages are the content."""


class Authority(StrEnum):
    """Trust tier, highest first. Used to break ties between contradicting sources."""

    INTERNATIONAL = "international"  # FAO, IPPC — treaty bodies and UN agencies
    SCIENTIFIC = "scientific"  # APS and other peer-reviewed professional societies
    UNIVERSITY = "university"  # university extension services
    NATIONAL = "national"  # national/provincial agriculture departments


class DocumentType(StrEnum):
    TECHNICAL_MANUAL = "technical_manual"
    GUIDELINES = "guidelines"
    EXTENSION_GUIDE = "extension_guide"
    EDUCATIONAL = "educational"
    FARMING_GUIDE = "farming_guide"
    EXPERT_SYSTEM = "expert_system"


class Source(BaseModel):
    """One document, with everything needed to fetch it and to cite it afterwards."""

    slug: str = Field(description="Stable id; becomes the filename and the citation key.")
    title: str
    url: HttpUrl
    fetch_mode: FetchMode

    # --- the metadata schema that travels onto every chunk -------------------------------
    source: str = Field(description="Publisher shown to the user, e.g. 'FAO'.")
    authority: Authority
    region: str = Field(description="Jurisdiction the advice was written for.")
    document_type: DocumentType
    language: str = "en"
    year: int | None = Field(None, description="Publication year; None when undated.")
    diseases: tuple[str, ...] = Field(
        description="Diseases this document covers. Chunks get one each; documents may span."
    )

    # --- fetch behaviour ------------------------------------------------------------------
    link_pattern: str | None = Field(
        None,
        description="For LANDING/INDEX modes: regex selecting the links worth following.",
    )
    max_subpages: int = Field(
        40, description="Ceiling on INDEX crawls, so a bad pattern cannot walk an entire site."
    )
    licence: str = Field(description="Redistribution terms, recorded per document.")
    notes: str = ""

    @property
    def is_pakistani(self) -> bool:
        return self.region.lower() in {"pakistan", "pk"}


# Diseases use the same vocabulary as the classifier so a CNN prediction can filter
# retrieval directly, with no mapping layer in between.
PANAMA = "panama"
SIGATOKA = "sigatoka"
GENERAL = "general"


REGISTRY: tuple[Source, ...] = (
    Source(
        slug="fao_fusarium_wilt_manual",
        title="Technical Manual: Fusarium Wilt of Banana (Panama Disease)",
        url="https://www.fao.org/fileadmin/templates/banana/documents/Docs_Resources_2015/TR4/13ManualFusarium.pdf",
        fetch_mode=FetchMode.DIRECT,
        source="FAO",
        authority=Authority.INTERNATIONAL,
        region="global",
        document_type=DocumentType.TECHNICAL_MANUAL,
        year=2015,
        diseases=(PANAMA,),
        licence="FAO — free for non-commercial educational use with attribution.",
        notes="Verified 1.77 MB direct PDF. The deepest Panama source in the pack.",
    ),
    Source(
        slug="ippc_tr4_guidelines",
        title="Prevention, Preparedness and Response Guidelines for Fusarium TR4",
        url="https://www.ippc.int/en/publications/92050/",
        fetch_mode=FetchMode.LANDING,
        link_pattern=r"\.pdf",
        source="FAO/IPPC",
        authority=Authority.INTERNATIONAL,
        region="global",
        document_type=DocumentType.GUIDELINES,
        year=2023,
        diseases=(PANAMA,),
        licence="IPPC/FAO — public phytosanitary guidance, redistributable with attribution.",
        notes="TR4 is quarantine-grade; this source backs the mandatory escalation rule. "
        "KNOWN LIMITATION: the publication page renders its file list via JavaScript, "
        "so only the landing page is retrievable automatically. TR4 coverage therefore "
        "rests on the FAO Fusarium manual; download the PDF by hand to strengthen it.",
    ),
    Source(
        slug="hawaii_banana_ipm",
        title="Banana Pest and Disease Management in the Tropical Pacific",
        url="https://cms.ctahr.hawaii.edu/wangkh/Research-and-Extension/Banana-IPM/Banana-IPM-Guidebook",
        # The guidebook is HTML chapters, not a PDF -- CHPT2-Panama and CHPT2-BLS (Black Leaf
        # Streak, i.e. Black Sigatoka) are directly on-topic for two of our three classes.
        fetch_mode=FetchMode.INDEX,
        link_pattern=r"Guidebook/CHPT",
        source="University of Hawaii CTAHR",
        authority=Authority.UNIVERSITY,
        region="pacific",
        document_type=DocumentType.EXTENSION_GUIDE,
        diseases=(PANAMA, SIGATOKA, GENERAL),
        licence="University extension material — educational use with attribution.",
        notes="Practical IPM framing; complements the more formal FAO documents.",
    ),
    Source(
        slug="aps_black_sigatoka",
        title="Black Sigatoka of Bananas and Plantains",
        url="https://www.apsnet.org/edcenter/pdlessons/Pages/BlackSigatoka.aspx",
        fetch_mode=FetchMode.PAGE,
        source="American Phytopathological Society",
        authority=Authority.SCIENTIFIC,
        region="global",
        document_type=DocumentType.EDUCATIONAL,
        diseases=(SIGATOKA,),
        licence="APS Education Center — educational use with attribution.",
        notes="Returns 403 without a browser user-agent; 200 with one.",
    ),
    Source(
        slug="tnau_panama_wilt",
        title="Banana Panama Wilt",
        url="https://agritech.tnau.ac.in/crop_protection/banana_diseases/crop_prot_crop%20diseases_fruits_banana_7.html",
        fetch_mode=FetchMode.PAGE,
        source="Tamil Nadu Agricultural University",
        authority=Authority.UNIVERSITY,
        region="india",
        document_type=DocumentType.EXTENSION_GUIDE,
        diseases=(PANAMA,),
        licence="TNAU Agritech Portal — public extension material.",
        notes="South Asian context, closest agronomically to Pakistan of the current set. "
        "Indian pesticide registrations still differ from Pakistani ones. "
        "Apex domain only: TNAU's certificate does not cover www.",
    ),
    Source(
        slug="tnau_yellow_sigatoka",
        title="Banana Yellow Sigatoka (Leaf Spot)",
        url="https://agritech.tnau.ac.in/crop_protection/banana_diseases/crop_prot_crop%20diseases_fruits_banana_8.html",
        fetch_mode=FetchMode.PAGE,
        source="Tamil Nadu Agricultural University",
        authority=Authority.UNIVERSITY,
        region="india",
        document_type=DocumentType.EXTENSION_GUIDE,
        diseases=(SIGATOKA,),
        licence="TNAU Agritech Portal — public extension material.",
        notes="Yellow Sigatoka specifically; the dataset does not distinguish it from Black.",
    ),
    Source(
        slug="fao_banana_cultivation",
        title="Bananas (FAO Better Farming Series)",
        url="https://www.fao.org/4/t0308e/t0308e00.htm",
        fetch_mode=FetchMode.INDEX,
        link_pattern=r"t0308e\d+\.htm",
        max_subpages=30,
        source="FAO",
        authority=Authority.INTERNATIONAL,
        region="global",
        document_type=DocumentType.FARMING_GUIDE,
        diseases=(GENERAL,),
        licence="FAO — free for non-commercial educational use with attribution.",
        notes="Table of contents; chapters live in sibling t0308eNN.htm pages. Backs the "
        "general farming questions the chatbot must answer without an image.",
    ),
    Source(
        slug="tnau_expert_system",
        title="Banana Expert System: Crop Protection",
        url="https://agritech.tnau.ac.in/expert_system/banana/cropprotection.html",
        fetch_mode=FetchMode.PAGE,
        source="Tamil Nadu Agricultural University",
        authority=Authority.UNIVERSITY,
        region="india",
        document_type=DocumentType.EXPERT_SYSTEM,
        diseases=(PANAMA, SIGATOKA, GENERAL),
        licence="TNAU Agritech Portal — public extension material.",
        notes="Broad crop-protection coverage including pests beyond the three CNN classes.",
    ),
)


def by_slug(slug: str) -> Source:
    for source in REGISTRY:
        if source.slug == slug:
            return source
    raise KeyError(f"Unknown source slug: {slug!r}. Known: {[s.slug for s in REGISTRY]}")


def for_disease(disease: str) -> tuple[Source, ...]:
    """Sources covering a disease, most authoritative first."""
    order = {
        Authority.INTERNATIONAL: 0,
        Authority.SCIENTIFIC: 1,
        Authority.UNIVERSITY: 2,
        Authority.NATIONAL: 3,
    }
    matches = [s for s in REGISTRY if disease in s.diseases]
    return tuple(sorted(matches, key=lambda s: order[s.authority]))


def coverage_summary() -> dict[str, Any]:
    """What the corpus covers, for the audit trail and for spotting gaps."""
    return {
        "documents": len(REGISTRY),
        "per_disease": {
            disease: len(for_disease(disease)) for disease in (PANAMA, SIGATOKA, GENERAL)
        },
        "regions": sorted({s.region for s in REGISTRY}),
        "pakistani_sources": sum(1 for s in REGISTRY if s.is_pakistani),
        "authorities": sorted({s.authority.value for s in REGISTRY}),
    }
