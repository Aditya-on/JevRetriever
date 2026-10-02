"""Public data models for JevRetriever."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass
class RetrievedDocument:
    """A document returned by the developer's base retriever."""

    text: str
    document_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievalAction(str, Enum):
    """Action selected by the Jev retrieval controller."""

    STOP = "STOP"
    RETRIEVE_MORE = "RETRIEVE_MORE"
    QUERY_EXPAND = "QUERY_EXPAND"
    DIVERSIFY = "DIVERSIFY"


@dataclass
class EvidenceAssessment:
    """Jev's assessment of the currently accumulated evidence."""

    sufficiency: float
    coverage: float
    relevance: float
    redundancy: float
    missing_information: str = "NONE"
    next_query: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class ControllerDecision:
    """A single retrieval-control decision."""

    action: RetrievalAction
    reason: str
    query: str
    retrieval_number: int


@dataclass
class RetrievalResult:
    """Final result returned by :class:`JevRetriever`.

    Attributes:
        query: The original user query.
        documents: All unique documents accumulated during retrieval.
        assessment: Jev's final assessment of the accumulated evidence.
        decisions: The controller decision made after each retrieval.
        retrieval_calls: Number of calls made to the base retriever.
        jev_calls: Number of calls made to Jev.
        input_tokens: Total Jev input tokens reported by the API.
        output_tokens: Total Jev output tokens reported by the API.
        total_cost: Total Jev cost, when available.
        iterations: Number of retrieval iterations performed.
    """

    query: str
    documents: list[RetrievedDocument]
    assessment: EvidenceAssessment
    decisions: list[ControllerDecision]

    retrieval_calls: int
    jev_calls: int

    input_tokens: int = 0
    output_tokens: int = 0

    total_cost: float | None = None

    iterations: int = 0

    @property
    def total_jev_tokens(self) -> int:
        """Return total Jev tokens consumed."""

        return self.input_tokens + self.output_tokens