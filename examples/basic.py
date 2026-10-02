"""Basic JevRetriever example.

This example demonstrates adaptive evidence retrieval using a small
deterministic retriever. The base retriever can be replaced by any
developer-owned Dense, Hybrid, BM25, MMR, vector-database, or custom
retriever that implements the required interface.
"""

from jevretrieve import JevRetriever, RetrievedDocument


class MyHybridRetriever:
    """Small deterministic retriever used for the example."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        query_lower = query.lower().strip()

        # Jev identified the cause as missing.
        if query_lower.startswith(
            "find the missing cause"
        ):
            documents = [
                RetrievedDocument(
                    document_id="cause-1",
                    text=(
                        "The incident was caused by a configuration "
                        "error introduced during the deployment."
                    ),
                    score=0.95,
                ),
                RetrievedDocument(
                    document_id="cause-2",
                    text=(
                        "The configuration error caused the production "
                        "service to fail shortly after deployment."
                    ),
                    score=0.91,
                ),
            ]

        # Jev identified the responsible entity as missing.
        elif query_lower.startswith(
            "find the missing entity"
        ):
            documents = [
                RetrievedDocument(
                    document_id="owner-1",
                    text=(
                        "The operations team was responsible for "
                        "approving the deployment."
                    ),
                    score=0.94,
                ),
                RetrievedDocument(
                    document_id="owner-2",
                    text=(
                        "The deployment was approved by the "
                        "operations team."
                    ),
                    score=0.90,
                ),
            ]

        # Initial retrieval.
        else:
            documents = [
                RetrievedDocument(
                    document_id="incident-1",
                    text=(
                        "A production incident occurred shortly after "
                        "a deployment."
                    ),
                    score=0.93,
                ),
            ]

        return documents[:top_k]


def main() -> None:
    """Run the example."""

    retriever = JevRetriever(
        base_retriever=MyHybridRetriever(),
        max_retrievals=3,
    )

    result = retriever.retrieve(
        "What caused the incident and who was responsible?"
    )

    print("=== JevRetriever ===")
    print()
    print(f"Original query: {result.query}")
    print(f"Retrieval calls: {result.retrieval_calls}")
    print(f"Jev calls: {result.jev_calls}")
    print(f"Iterations: {result.iterations}")
    print()

    print("Final evidence assessment:")
    print(
        f"  Sufficiency: "
        f"{result.assessment.sufficiency:.2f}"
    )
    print(
        f"  Coverage: "
        f"{result.assessment.coverage:.2f}"
    )
    print(
        f"  Relevance: "
        f"{result.assessment.relevance:.2f}"
    )
    print(
        f"  Redundancy: "
        f"{result.assessment.redundancy:.2f}"
    )
    print(
        f"  Missing information: "
        f"{result.assessment.missing_information}"
    )
    print(
        f"  Next query: "
        f"{result.assessment.next_query}"
    )
    print()

    print("Retrieval decisions:")
    for decision in result.decisions:
        print(
            f"  {decision.retrieval_number}. "
            f"{decision.action.value} — "
            f"{decision.reason}"
        )
        print(
            f"     query: {decision.query}"
        )

    print()
    print("Accumulated documents:")

    for document in result.documents:
        score = (
            f"{document.score:.2f}"
            if document.score is not None
            else "n/a"
        )

        print(
            f"  [{document.document_id}] "
            f"{document.text} "
            f"(score={score})"
        )

    print()
    print("Token usage:")
    print(f"  Input: {result.input_tokens}")
    print(f"  Output: {result.output_tokens}")
    print(f"  Total: {result.total_jev_tokens}")


if __name__ == "__main__":
    main()