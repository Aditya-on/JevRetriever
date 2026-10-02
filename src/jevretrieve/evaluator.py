"""Jev evidence evaluator."""

from __future__ import annotations

from typing import Any

from .client import JevClient
from .models import EvidenceAssessment, RetrievedDocument


class EvidenceEvaluator:
    def __init__(self, client: JevClient) -> None:
        self.client = client

    def evaluate(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> tuple[EvidenceAssessment, int, int, dict[str, Any]]:
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
                "missing information. If more retrieval would help, propose "
                "a concise next search query."
            ),
        }

        questions = {
            "sufficiency": {
                "type": "number",
                "criteria": (
                    "Score how sufficient the evidence is for answering "
                    "the query from 0 to 1."
                ),
            },
            "coverage": {
                "type": "number",
                "criteria": (
                    "Score how completely the evidence covers the facts "
                    "needed to answer the query from 0 to 1."
                ),
            },
            "relevance": {
                "type": "number",
                "criteria": (
                    "Score how relevant the retrieved evidence is to the "
                    "query from 0 to 1."
                ),
            },
            "redundancy": {
                "type": "number",
                "criteria": (
                    "Score how redundant the retrieved evidence is from "
                    "0 to 1, where 1 is highly redundant."
                ),
            },
            "missing_information": {
                "type": "choice",
                "criteria": {
                    "NONE": "No important information is missing.",
                    "ENTITY": "A needed person, organization, object, or entity is missing.",
                    "RELATIONSHIP": "A needed relationship between entities is missing.",
                    "DATE": "A needed date or time is missing.",
                    "LOCATION": "A needed location is missing.",
                    "CAUSE": "A needed cause or explanation is missing.",
                    "COMPARISON": "Information needed for a comparison is missing.",
                    "ADDITIONAL_FACT": "Another important factual detail is missing.",
                },
                "instructions": "Identify the most important missing information category.",
            },
            "next_query": {
                "type": "text",
                "criteria": (
                    "If more evidence is needed, provide the best concise "
                    "search query for the next retrieval. If no more "
                    "retrieval is needed, return an empty string."
                ),
            },
        }

        # 🔴✓ API CALL — TypeSafe Jev
        raw = self.client.judge(state=state, questions=questions)

        answers = raw.get("answers", raw)
        assessment = EvidenceAssessment(
            sufficiency=_number(answers, "sufficiency"),
            coverage=_number(answers, "coverage"),
            relevance=_number(answers, "relevance"),
            redundancy=_number(answers, "redundancy"),
            missing_information=_choice(answers, "missing_information"),
            next_query=_text(answers, "next_query"),
            raw=raw,
        )

        usage = raw.get("usage", {})
        input_tokens = int(
            usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0
        )
        output_tokens = int(
            usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0
        )
        return assessment, input_tokens, output_tokens, raw


def _answer(answers: dict[str, Any], name: str) -> Any:
    value = answers.get(name)
    if isinstance(value, dict):
        for key in ("number", "text", "choice", "value", "answer"):
            if key in value:
                return value[key]
    return value


def _number(answers: dict[str, Any], name: str) -> float:
    value = _answer(answers, name)
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _choice(answers: dict[str, Any], name: str) -> str:
    value = _answer(answers, name)
    return str(value or "NONE").upper()


def _text(answers: dict[str, Any], name: str) -> str | None:
    value = _answer(answers, name)
    if value is None:
        return None
    value = str(value).strip()
    return value or None
