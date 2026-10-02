"""Jev retrieval controller."""

from __future__ import annotations

from .models import EvidenceAssessment, RetrievalAction


class RetrievalController:
    """Decide whether retrieval should stop or continue."""

    def __init__(
        self,
        *,
        sufficiency_threshold: float = 0.85,
        coverage_threshold: float = 0.85,
    ) -> None:
        if not 0.0 <= sufficiency_threshold <= 1.0:
            raise ValueError(
                "sufficiency_threshold must be between 0 and 1."
            )

        if not 0.0 <= coverage_threshold <= 1.0:
            raise ValueError(
                "coverage_threshold must be between 0 and 1."
            )

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
        """Return the next retrieval action."""

        # The hard ceiling always wins.
        if retrieval_number >= max_retrievals:
            return (
                RetrievalAction.STOP,
                "Maximum retrieval limit reached.",
                current_query,
            )

        # If Jev identified missing information, continue with a
        # targeted query.
        if (
            assessment.missing_information
            and assessment.missing_information != "NONE"
        ):
            next_query = (
                assessment.next_query
                or current_query
            )

            return (
                RetrievalAction.QUERY_EXPAND,
                (
                    "Important information is still missing: "
                    f"{assessment.missing_information}."
                ),
                next_query,
            )

        # If the evidence is highly redundant, explicitly classify
        # the next retrieval as DIVERSIFY.
        #
        # DIVERSIFY does not claim that the underlying retriever
        # performs a specific diversification algorithm. It means
        # that Jev has determined another retrieval should seek
        # different evidence, using the supplied follow-up query
        # when available.
        if assessment.redundancy >= 0.65:
            next_query = (
                assessment.next_query
                or current_query
            )

            return (
                RetrievalAction.DIVERSIFY,
                "Current evidence is substantially redundant.",
                next_query,
            )

        # If Jev explicitly supplied a different follow-up query,
        # classify the next retrieval as query expansion.
        if (
            assessment.next_query
            and assessment.next_query != current_query
        ):
            return (
                RetrievalAction.QUERY_EXPAND,
                "Jev supplied a more specific follow-up query.",
                assessment.next_query,
            )

        # Stop only when the evidence is sufficiently complete.
        if (
            assessment.sufficiency
            >= self.sufficiency_threshold
            and assessment.coverage
            >= self.coverage_threshold
        ):
            return (
                RetrievalAction.STOP,
                "Evidence is sufficient and complete enough.",
                current_query,
            )

        # Otherwise retrieve more evidence using the current query.
        return (
            RetrievalAction.RETRIEVE_MORE,
            "Current evidence is not yet sufficient.",
            current_query,
        )