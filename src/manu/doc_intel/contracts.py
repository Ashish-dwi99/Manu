"""What a document turned out to be, and where each fact came from.

Every value here carries the span it was read from. That is the whole point: an advocate
signing a filing has to be able to click "next hearing 12 August 2026" and land on the
line in the order that says it. A case file of uncited facts is a summary, and a summary
is not work product.

See docs/document-intelligence.md for the design and for what was studied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Bumped whenever an extractor changes what it would produce from the same bytes. A file is
# re-read when its content hash OR this version differs from what was stored, which is what
# lets "re-index the folder" stay cheap while still picking up improvements.
EXTRACTOR_VERSION = 1

DOCUMENT_PROFILE_SCHEMA = "manu.legal_agent.document_profile.v1"


# Document kinds an Indian case folder actually contains. Ordered roughly by the life of a
# matter, because that ordering is also how the case file presents them.
#
# `unclassified` is a first-class value, not a failure. A folder holds letters, fee
# receipts and scanned envelopes, and calling one of those a "written statement" is worse
# than admitting we do not know.
DOCUMENT_KINDS: tuple[str, ...] = (
    "unclassified",
    # Pre-litigation
    "legal_notice",
    "reply_to_legal_notice",
    # Institution
    "plaint",
    "written_statement",
    "memo_of_appeal",
    "writ_petition",
    "bail_application",
    "application_ia",
    "counter_affidavit",
    "rejoinder",
    # Court output
    "order",
    "judgment",
    "decree",
    "cause_list",
    # Record
    "deposition",
    "affidavit",
    "vakalatnama",
    "fir",
    "charge_sheet",
    "bank_memo",
    "exhibit_list",
    "annexure",
    "correspondence",
)

# The regions a filing is built from. Most attributes live in a known one, and searching
# the right region beats searching the file: a date in the cause title is the filing year,
# the same date in the prayer is a deadline being asked for.
DOCUMENT_REGIONS: tuple[str, ...] = ("cause_title", "body", "prayer", "verification")


@dataclass(frozen=True, slots=True)
class Citation:
    """Where a value was read from, precisely enough to open it."""

    relative_path: str
    start: int
    end: int
    page: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "start": self.start,
            "end": self.end,
            "page": self.page,
        }


@dataclass(frozen=True, slots=True)
class Attribute:
    """One extracted fact.

    `confidence` is not decoration. The case file picks between documents that disagree, and
    a deterministic identifier read off a published grammar deserves to outrank a model's
    reading of prose. `method` records which it was so the choice can be explained.
    """

    name: str
    value: str
    citation: Citation
    # "grammar" — a published format matched exactly. "rule" — a title line or phrase.
    # "model" — read by the model. Never blend these; the case file resolves conflicts by
    # method and an unlabelled value cannot be resolved.
    method: str
    confidence: float
    # Free-form, per attribute: a date carries its role, a party carries its description.
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "citation": self.citation.as_dict(),
            "method": self.method,
            "confidence": round(float(self.confidence), 3),
            "detail": dict(self.detail),
        }


@dataclass(frozen=True, slots=True)
class Classification:
    """What kind of document this is, and what decided it.

    `evidence` exists so the answer is arguable. An advocate who disagrees with
    "counter_affidavit" can see it was the phrase that decided, and a wrong rule can be
    corrected instead of a model being retrained.
    """

    kind: str
    method: str
    confidence: float
    evidence: str = ""
    citation: Citation | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "method": self.method,
            "confidence": round(float(self.confidence), 3),
            "evidence": self.evidence,
            "citation": self.citation.as_dict() if self.citation else None,
        }


UNCLASSIFIED = Classification(kind="unclassified", method="none", confidence=0.0)


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    """Everything read out of one file.

    `failure` is a field rather than an exception because one unreadable scan in a folder of
    two hundred must not stop the rest. The document keeps its own failure and the case file
    can say so.
    """

    relative_path: str
    content_sha256: str
    extractor_version: int
    classification: Classification
    attributes: tuple[Attribute, ...] = ()
    page_count: int = 0
    failure: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DOCUMENT_PROFILE_SCHEMA,
            "relative_path": self.relative_path,
            "content_sha256": self.content_sha256,
            "extractor_version": self.extractor_version,
            "classification": self.classification.as_dict(),
            "attributes": [item.as_dict() for item in self.attributes],
            "page_count": self.page_count,
            "failure": self.failure,
        }

    def attribute(self, name: str) -> Attribute | None:
        """The best reading of one attribute in this document.

        Best means highest confidence, and on a tie the deterministic one, because a
        grammar match is checkable and a model's reading is not.
        """
        candidates = [item for item in self.attributes if item.name == name]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.confidence, item.method == "grammar"))
