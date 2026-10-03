
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
        redundancy_threshold: float = 0.65,
    ) -> None:
        if not 0.0 <= sufficiency_threshold <= 1.0:
            raise ValueError(
                "sufficiency_threshold must be between 0 and 1."
            )
        if not 0.0 <= coverage_threshold <= 1.0:
            raise ValueError(
                "coverage_threshold must be between 0 and 1."
            )
        if not 0.0 <= redundancy_threshold <= 1.0:
            raise ValueError(
                "redundancy_threshold must be between 0 and 1."
            )

        self.sufficiency_threshold = sufficiency_threshold
        self.coverage_threshold = coverage_threshold
        self.redundancy_threshold = redundancy_threshold

    def decide(
        self,
        assessment: EvidenceAssessment,
        *,
        retrieval_number: int,
        max_retrievals: int,
    ) -> tuple[RetrievalAction, str]:
        """Return the next retrieval action and reason."""

        if retrieval_number >= max_retrievals:
            return (
                RetrievalAction.STOP,
                "Maximum retrieval limit reached.",
            )

        if assessment.redundancy >= self.redundancy_threshold:
            return (
                RetrievalAction.STOP,
                (
                    "Evidence is substantially redundant. "
                    "No further retrieval is needed."
                ),
            )

        if (
            assessment.sufficiency
            >= self.sufficiency_threshold
            and assessment.coverage
            >= self.coverage_threshold
            and assessment.missing_information == "NONE"
        ):
            return (
                RetrievalAction.STOP,
                "Evidence is sufficient and complete enough.",
            )

        if assessment.missing_information != "NONE":
            return (
                RetrievalAction.RETRIEVE_MORE,
                (
                    "Important information is still missing "
                    f"({assessment.missing_information}). "
                    "Retrieving more evidence."
                ),
            )

        return (
            RetrievalAction.RETRIEVE_MORE,
            "Evidence is not yet sufficient. Retrieving more evidence.",
        )
