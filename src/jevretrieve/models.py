"""Public data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(slots=True)
class RetrievedDocument:
    """A document returned by the user's base retriever."""

    text: str
    document_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalAction(str, Enum):
    STOP = "STOP"
    RETRIEVE_MORE = "RETRIEVE_MORE"
    QUERY_EXPAND = "QUERY_EXPAND"
    DIVERSIFY = "DIVERSIFY"


@dataclass(slots=True)
class EvidenceAssessment:
    """Jev's assessment of the current evidence."""

    sufficiency: float
    coverage: float
    relevance: float
    redundancy: float
    missing_information: str = "NONE"
    next_query: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ControllerDecision:
    """One adaptive retrieval decision."""

    action: RetrievalAction
    reason: str
    query: str
    retrieval_number: int


@dataclass(slots=True)
class RetrievalResult:
    """Final output of JevRetriever."""

    query: str
    documents: list[RetrievedDocument]
    assessment: EvidenceAssessment
    decisions: list[ControllerDecision]
    retrieval_calls: int
    jev_calls: int
    input_tokens: int
    output_tokens: int
    total_cost: float | None
    iterations: int

    @property
    def total_jev_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
