"""Jev evidence evaluator."""

from __future__ import annotations

from typing import Any

from .client import JevClient
from .models import EvidenceAssessment, RetrievedDocument


class EvidenceEvaluator:
    """Evaluate retrieved evidence using Jev."""

    def __init__(self, client: JevClient) -> None:
        self.client = client

    def evaluate(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> tuple[EvidenceAssessment, int, int, dict[str, Any]]:
        """Ask Jev to evaluate the current evidence."""

        evidence = [
            {
                "id": doc.document_id or str(index),
                "text": doc.text,
                "score": doc.score,
            }
            for index, doc in enumerate(documents, start=1)
        ]

        state = {
            "query": query,
            "retrieved_evidence": evidence,
            "instruction": (
                "Judge whether the retrieved evidence is sufficient to "
                "answer the query. Evaluate relevance, coverage, "
                "sufficiency, redundancy, and identify the most important "
                "missing information."
            ),
        }

        questions = {
            "sufficiency": {
                "type": "score",
                "criteria": [
                    "0.0 = The evidence is completely insufficient.",
                    "0.25 = The evidence provides very little support.",
                    "0.5 = The evidence provides partial support.",
                    "0.75 = The evidence provides substantial support.",
                    "1.0 = The evidence is fully sufficient.",
                ],
            },
            "coverage": {
                "type": "score",
                "criteria": [
                    "0.0 = None of the required facts are covered.",
                    "0.25 = Very few required facts are covered.",
                    "0.5 = Some required facts are covered.",
                    "0.75 = Most required facts are covered.",
                    "1.0 = All important required facts are covered.",
                ],
            },
            "relevance": {
                "type": "score",
                "criteria": [
                    "0.0 = The evidence is unrelated to the query.",
                    "0.25 = The evidence is mostly irrelevant.",
                    "0.5 = The evidence is partially relevant.",
                    "0.75 = The evidence is highly relevant.",
                    "1.0 = The evidence is directly relevant.",
                ],
            },
            "redundancy": {
                "type": "score",
                "criteria": [
                    "0.0 = The evidence contains no meaningful redundancy.",
                    "0.25 = The evidence has little redundancy.",
                    "0.5 = The evidence has moderate redundancy.",
                    "0.75 = The evidence is substantially redundant.",
                    "1.0 = The evidence is almost entirely redundant.",
                ],
            },
            "missing_information": {
                "type": "choice",
                "criteria": {
                    "NONE": "No important information is missing.",
                    "ENTITY": (
                        "A needed person, organization, object, "
                        "or entity is missing."
                    ),
                    "RELATIONSHIP": (
                        "A needed relationship between entities is missing."
                    ),
                    "DATE": "A needed date or time is missing.",
                    "LOCATION": "A needed location is missing.",
                    "CAUSE": "A needed cause or explanation is missing.",
                    "COMPARISON": (
                        "Information needed for a comparison is missing."
                    ),
                    "ADDITIONAL_FACT": (
                        "Another important factual detail is missing."
                    ),
                },
                "instructions": (
                    "Identify the most important missing information "
                    "category. Choose NONE if no important information "
                    "is missing."
                ),
            },
        }

        # 🔴✓ API CALL — TypeSafe Jev
        raw = self.client.judge(
            state=state,
            questions=questions,
        )

        # Test doubles can return an EvidenceAssessment directly.
        if isinstance(raw, EvidenceAssessment):
            return raw, 0, 0, {}

        answers = raw.get("answers", raw)

        missing_information = _choice(
            answers,
            "missing_information",
        )

        assessment = EvidenceAssessment(
            sufficiency=_score(
                answers,
                "sufficiency",
            ),
            coverage=_score(
                answers,
                "coverage",
            ),
            relevance=_score(
                answers,
                "relevance",
            ),
            redundancy=_score(
                answers,
                "redundancy",
            ),
            missing_information=missing_information,
            raw=raw,
        )

        usage = raw.get("usage", {})

        input_tokens = int(
            usage.get(
                "input_tokens",
                usage.get("prompt_tokens", 0),
            )
            or 0
        )

        output_tokens = int(
            usage.get(
                "output_tokens",
                usage.get("completion_tokens", 0),
            )
            or 0
        )

        return (
            assessment,
            input_tokens,
            output_tokens,
            raw,
        )


def _answer(
    answers: dict[str, Any],
    name: str,
) -> Any:
    """Extract an answer value from a Jev answer object."""

    value = answers.get(name)

    if isinstance(value, dict):
        for key in (
            "score",
            "number",
            "text",
            "choice",
            "value",
            "answer",
        ):
            if key in value:
                return value[key]

    return value


def _score(
    answers: dict[str, Any],
    name: str,
) -> float:
    """Return a normalized 0-1 score."""

    value = answers.get(name)

    if isinstance(value, dict):
        if "score" in value:
            try:
                return max(
                    0.0,
                    min(
                        1.0,
                        float(value["score"]),
                    ),
                )
            except (TypeError, ValueError):
                return 0.0

        if "number" in value:
            try:
                return max(
                    0.0,
                    min(
                        1.0,
                        float(value["number"]),
                    ),
                )
            except (TypeError, ValueError):
                return 0.0

    try:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )
    except (TypeError, ValueError):
        return 0.0


def _choice(
    answers: dict[str, Any],
    name: str,
) -> str:
    """Extract and normalize a Jev choice answer."""

    value = _answer(
        answers,
        name,
    )

    return str(
        value or "NONE"
    ).upper()