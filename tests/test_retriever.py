from jevretrieve import JevRetriever, RetrievedDocument
from jevretrieve.models import EvidenceAssessment


class FakeBaseRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, query, top_k=5):
        self.calls.append((query, top_k))
        return [
            RetrievedDocument(
                document_id=f"{query}-{i}",
                text=f"Evidence {i} for {query}",
                score=1.0,
            )
            for i in range(top_k)
        ]


class FakeEvaluator:
    pass


class FakeJevClient:
    def __init__(self, assessments):
        self.assessments = iter(assessments)

    def judge(self, *, state, questions):
        a = next(self.assessments)
        return {
            "answers": {
                "sufficiency": {"number": a.sufficiency},
                "coverage": {"number": a.coverage},
                "relevance": {"number": a.relevance},
                "redundancy": {"number": a.redundancy},
                "missing_information": {"choice": a.missing_information},
                "next_query": {"text": a.next_query or ""},
            },
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }


def test_stops_when_evidence_is_sufficient():
    client = FakeJevClient([
        EvidenceAssessment(
            sufficiency=0.95,
            coverage=0.94,
            relevance=0.9,
            redundancy=0.2,
        )
    ])
    base = FakeBaseRetriever()

    retriever = JevRetriever(
        base,
        max_retrievals=10,
        jev_client=client,
    )
    result = retriever.retrieve("test")

    assert result.retrieval_calls == 1
    assert result.jev_calls == 1
    assert result.decisions[-1].action.value == "STOP"


def test_never_exceeds_hard_limit():
    client = FakeJevClient([
        EvidenceAssessment(
            sufficiency=0.1,
            coverage=0.1,
            relevance=0.5,
            redundancy=0.1,
            next_query="more evidence",
        )
        for _ in range(3)
    ])
    base = FakeBaseRetriever()

    retriever = JevRetriever(
        base,
        max_retrievals=3,
        jev_client=client,
    )
    result = retriever.retrieve("test")

    assert result.retrieval_calls == 3
    assert len(base.calls) == 3


def test_jev_can_change_query():
    client = FakeJevClient([
        EvidenceAssessment(
            sufficiency=0.2,
            coverage=0.2,
            relevance=0.5,
            redundancy=0.1,
            next_query="specific missing fact",
        ),
        EvidenceAssessment(
            sufficiency=0.95,
            coverage=0.95,
            relevance=0.95,
            redundancy=0.1,
        ),
    ])
    base = FakeBaseRetriever()

    retriever = JevRetriever(
        base,
        max_retrievals=5,
        jev_client=client,
    )
    result = retriever.retrieve("original question")

    assert result.retrieval_calls == 2
    assert base.calls[1][0] == "specific missing fact"
    assert result.decisions[0].action.value == "QUERY_EXPAND"
