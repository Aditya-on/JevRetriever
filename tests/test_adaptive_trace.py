from jevretrieve import (
    EvidenceAssessment,
    JevRetriever,
    RetrievedDocument,
)


class FakeJevClient:
    def __init__(self):
        self.calls = 0

    def judge(self, *, state, questions):
        self.calls += 1

        if self.calls == 1:
            return {
                "answers": {
                    "sufficiency": {"number": 0.4},
                    "coverage": {"number": 0.4},
                    "relevance": {"number": 0.8},
                    "redundancy": {"number": 0.9},
                    "missing_information": {
                        "choice": "NONE"
                    },
                    "next_query": {
                        "text": None
                    },
                },
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
            }

        return {
            "answers": {
                "sufficiency": {"number": 1.0},
                "coverage": {"number": 1.0},
                "relevance": {"number": 1.0},
                "redundancy": {"number": 0.2},
                "missing_information": {
                    "choice": "NONE"
                },
                "next_query": {
                    "text": None
                },
            },
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
            },
        }


class TraceRetriever:
    def __init__(self):
        self.queries = []

    def retrieve(self, query, top_k=5):
        self.queries.append(query)

        if len(self.queries) == 1:
            return [
                RetrievedDocument(
                    document_id="incident",
                    text=(
                        "A production incident occurred "
                        "after deployment."
                    ),
                    score=0.9,
                )
            ]

        return [
            RetrievedDocument(
                document_id="cause",
                text=(
                    "The incident was caused by an "
                    "incorrect configuration change."
                ),
                score=0.9,
            )
        ]


base = TraceRetriever()

retriever = JevRetriever(
    base_retriever=base,
    max_retrievals=2,
    jev_client=FakeJevClient(),
)

result = retriever.retrieve(
    "What caused the incident?"
)

print("=== Local Adaptive Trace ===")

print("\nRetrieval calls:")
print(result.retrieval_calls)

print("\nJev calls:")
print(result.jev_calls)

print("\nQueries:")
for query in base.queries:
    print("-", query)

print("\nDecisions:")
for decision in result.decisions:
    print(
        f"{decision.retrieval_number}: "
        f"{decision.action.value} — "
        f"{decision.reason}"
    )

print("\nDocuments:")
for document in result.documents:
    print(
        f"- {document.document_id}: "
        f"{document.text}"
    )