"""Adaptive stopping and action selection."""

from __future__ import annotations

from .models import EvidenceAssessment, RetrievalAction


class RetrievalController:
    """Simple deterministic policy driven by Jev's evidence assessment."""

    def __init__(
        self,
        *,
        sufficiency_threshold: float = 0.85,
        coverage_threshold: float = 0.85,
    ) -> None:
        self.sufficiency_threshold = sufficiency_threshold
        self.coverage_threshold = coverage_threshold

    def decide(
        self,
        assessment: EvidenceAssessment,
        *,
        current_query: str,
        retrieval_number: int,
        max_retrievals: int,
    ) -> tuple[RetrievalAction, str, str]:
        if (
            assessment.sufficiency >= self.sufficiency_threshold
            and assessment.coverage >= self.coverage_threshold
        ):
            return (
                RetrievalAction.STOP,
                "Evidence is sufficiently complete.",
                current_query,
            )

        if retrieval_number >= max_retrievals:
            return (
                RetrievalAction.STOP,
                "Maximum retrieval limit reached.",
                current_query,
            )

        next_query = assessment.next_query or current_query

        if assessment.next_query and next_query.strip() != current_query.strip():
            action = RetrievalAction.QUERY_EXPAND
            reason = "Evidence is insufficient; Jev supplied a better next query."
        elif assessment.redundancy >= 0.65:
            action = RetrievalAction.DIVERSIFY
            reason = "Evidence is insufficient and highly redundant; diversify the search."
        else:
            action = RetrievalAction.RETRIEVE_MORE
            reason = "Evidence is insufficient; retrieve more evidence."

        return action, reason, next_query
