"""Legal research attached to a case: find a judgment, read it, rely on a paragraph.

The discipline is Mike's (studied, not copied): verify the citation, find the judgment,
read what is needed, and cite only what was read. The sources are Indian, and each one
declares its standing, because an Indian Kanoon result is a lead until it is read from an
official or licensed copy.
"""

from manu.research.sources import (
    IndianKanoonSource,
    Judgment,
    JudgmentHit,
    LibrarySource,
    ResearchLadder,
    SourceUnavailable,
    default_research_ladder,
    split_paragraphs,
)
from manu.research.verify import check_citations

__all__ = [
    "IndianKanoonSource",
    "Judgment",
    "JudgmentHit",
    "LibrarySource",
    "ResearchLadder",
    "SourceUnavailable",
    "check_citations",
    "default_research_ladder",
    "split_paragraphs",
]
