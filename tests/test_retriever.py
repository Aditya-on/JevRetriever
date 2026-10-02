from __future__ import annotations

from collections.abc import Iterator

import pytest

from jevretrieve import (
    EvidenceAssessment,
    JevRetriever,
    RetrievedDocument,
)


class FakeJevClient:
    """Deterministic Jev client for unit tests."""

    def __init__(
        self,
        assessments: list[EvidenceAssessment],
    ) -> None:
        self.assessments: Iterator[
            EvidenceAssessment
        ] = iter(assessments)

        self.states: list[dict] = []

    def judge(
        self,
        *,
        state: dict,
        questions: dict,
    ) -> dict:
        self.states.append(state)

        assessment = next(self.assessments)

        return {
            "answers": {
                "sufficiency": {
                    "number": assessment.sufficiency,
                },
                "coverage": {
                    "number": assessment.coverage,
                },
                "relevance": {
                    "number": assessment.relevance,
                },
                "redundancy": {
                    "number": assessment.redundancy,
                },
                "missing_information": {
                    "choice": assessment.missing_information,
                },
                "next_query": {
                    "text": assessment.next_query,
                },
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
            },
        }


class FakeBaseRetriever:
    """Deterministic base retriever for unit tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        self.calls.append((query, top_k))

        return [
            RetrievedDocument(
                document_id=f"{query}-{index}",
                text=f"Evidence for: {query}",
                score=1.0,
            )
            for index in range(top_k)
        ]


def make_retriever(
    assessments: list[EvidenceAssessment],
    *,
    max_retrievals: int = 3,
) -> tuple[JevRetriever, FakeBaseRetriever, FakeJevClient]:
    base = FakeBaseRetriever()
    client = FakeJevClient(assessments)

    retriever = JevRetriever(
        base,
        max_retrievals=max_retrievals,
        jev_client=client,
    )

    return retriever, base, client


def test_sufficient_evidence_stops():
    retriever, base, client = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            )
        ]
    )

    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 1
    assert result.jev_calls == 1

    assert len(result.decisions) == 1
    assert result.decisions[0].action.value == "STOP"

    assert len(base.calls) == 1
    assert len(client.states) == 1


def test_hard_limit_is_respected():
    retriever, base, client = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.1,
                coverage=0.1,
                relevance=0.5,
                redundancy=0.1,
                missing_information="NONE",
            ),
            EvidenceAssessment(
                sufficiency=0.1,
                coverage=0.1,
                relevance=0.5,
                redundancy=0.1,
                missing_information="NONE",
            ),
            EvidenceAssessment(
                sufficiency=0.1,
                coverage=0.1,
                relevance=0.5,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ],
        max_retrievals=3,
    )

    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 3
    assert result.jev_calls == 3

    assert len(base.calls) == 3
    assert len(client.states) == 3

    assert result.decisions[-1].action.value == "STOP"
    assert (
        result.decisions[-1].reason
        == "Maximum retrieval limit reached."
    )


def test_jev_can_change_query():
    retriever, base, _ = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.4,
                coverage=0.4,
                relevance=0.7,
                redundancy=0.1,
                missing_information="NONE",
                next_query="find the missing evidence",
            ),
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ]
    )

    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 2
    assert result.jev_calls == 2

    assert base.calls[0][0] == "original question"
    assert base.calls[1][0] == "find the missing evidence"

    assert result.decisions[0].action.value == "QUERY_EXPAND"
    assert result.decisions[1].action.value == "STOP"


def test_missing_information_prevents_early_stop():
    retriever, base, _ = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="CAUSE",
                next_query="find the missing cause",
            ),
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ]
    )

    result = retriever.retrieve("what caused the incident?")

    assert result.retrieval_calls == 2
    assert result.jev_calls == 2

    assert base.calls[0][0] == "what caused the incident?"
    assert base.calls[1][0] == "find the missing cause"

    assert result.decisions[0].action.value == "QUERY_EXPAND"
    assert result.decisions[1].action.value == "STOP"


def test_original_query_is_preserved_for_jev():
    retriever, _, client = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.4,
                coverage=0.4,
                relevance=0.7,
                redundancy=0.1,
                missing_information="CAUSE",
                next_query="find the missing cause",
            ),
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ]
    )

    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 2
    assert result.jev_calls == 2

    assert client.states[0]["query"] == "original question"
    assert client.states[1]["query"] == "original question"

    assert result.query == "original question"


def test_documents_are_deduplicated():
    class DuplicateRetriever:
        def retrieve(
            self,
            query: str,
            top_k: int = 5,
        ) -> list[RetrievedDocument]:
            return [
                RetrievedDocument(
                    document_id="same-doc",
                    text="same evidence",
                    score=1.0,
                ),
                RetrievedDocument(
                    document_id="unique-doc",
                    text="unique evidence",
                    score=0.9,
                ),
            ]

    client = FakeJevClient(
        [
            EvidenceAssessment(
                sufficiency=0.2,
                coverage=0.2,
                relevance=0.5,
                redundancy=0.1,
                missing_information="NONE",
            ),
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ]
    )

    retriever = JevRetriever(
        DuplicateRetriever(),
        max_retrievals=2,
        jev_client=client,
    )

    result = retriever.retrieve("original question")

    document_ids = [
        document.document_id
        for document in result.documents
    ]

    assert result.retrieval_calls == 2
    assert result.jev_calls == 2

    assert document_ids == [
        "same-doc",
        "unique-doc",
    ]


def test_empty_query_is_rejected():
    base = FakeBaseRetriever()
    client = FakeJevClient([])

    retriever = JevRetriever(
        base,
        jev_client=client,
    )

    with pytest.raises(ValueError, match="query must not be empty"):
        retriever.retrieve("")


def test_invalid_max_retrievals_is_rejected():
    base = FakeBaseRetriever()
    client = FakeJevClient([])

    with pytest.raises(ValueError, match="max_retrievals"):
        JevRetriever(
            base,
            max_retrievals=0,
            jev_client=client,
        )


def test_invalid_top_k_is_rejected():
    base = FakeBaseRetriever()
    client = FakeJevClient([])

    with pytest.raises(ValueError, match="top_k"):
        JevRetriever(
            base,
            top_k=0,
            jev_client=client,
        )


def test_diversify_triggers_another_retrieval():
    retriever, base, _ = make_retriever(
        [
            EvidenceAssessment(
                sufficiency=0.4,
                coverage=0.4,
                relevance=0.7,
                redundancy=0.9,
                missing_information="NONE",
                next_query="find different evidence",
            ),
            EvidenceAssessment(
                sufficiency=0.95,
                coverage=0.95,
                relevance=0.95,
                redundancy=0.1,
                missing_information="NONE",
            ),
        ]
    )

    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 2
    assert result.jev_calls == 2

    assert result.decisions[0].action.value == "DIVERSIFY"
    assert base.calls[0][0] == "original question"
    assert base.calls[1][0] == "find different evidence"

    assert result.decisions[1].action.value == "STOP"