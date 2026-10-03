"""Main public JevRetriever implementation."""

from __future__ import annotations

from typing import Protocol

from .client import JevClient
from .controller import RetrievalController
from .evaluator import EvidenceEvaluator
from .models import (
    ControllerDecision,
    RetrievedDocument,
    RetrievalAction,
    RetrievalResult,
)


class BaseRetriever(Protocol):
    """Minimal contract for an existing developer retriever."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        ...


class JevRetriever:
    """Adaptive evidence retrieval around any base retriever.

    The base retriever finds evidence.
    Jev evaluates the accumulated evidence and decides whether
    another retrieval is needed.

    Retrieval continues with the same query until:
    - the evidence is sufficient,
    - the evidence becomes substantially redundant, or
    - the maximum retrieval limit is reached.
    """

    def __init__(
        self,
        base_retriever: BaseRetriever,
        max_retrievals: int = 10,
        *,
        top_k: int = 5,
        jev_api_key: str | None = None,
        jev_model: str = "jev-latest",
        sufficiency_threshold: float = 0.85,
        coverage_threshold: float = 0.85,
        redundancy_threshold: float = 0.65,
        jev_client: JevClient | None = None,
    ) -> None:
        if max_retrievals < 1:
            raise ValueError(
                "max_retrievals must be at least 1."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        self.base_retriever = base_retriever
        self.max_retrievals = max_retrievals
        self.top_k = top_k

        client = jev_client or JevClient(
            api_key=jev_api_key,
            model=jev_model,
        )

        self.evaluator = EvidenceEvaluator(client)

        self.controller = RetrievalController(
            sufficiency_threshold=sufficiency_threshold,
            coverage_threshold=coverage_threshold,
            redundancy_threshold=redundancy_threshold,
        )

    def retrieve(self, query: str) -> RetrievalResult:
        """Retrieve evidence adaptively using Jev."""

        if not query or not query.strip():
            raise ValueError(
                "query must not be empty."
            )

        all_documents: list[RetrievedDocument] = []
        seen_ids: set[str] = set()

        decisions: list[ControllerDecision] = []

        input_tokens = 0
        output_tokens = 0

        jev_calls = 0
        retrieval_calls = 0

        assessment = None

        for retrieval_number in range(
            1,
            self.max_retrievals + 1,
        ):
            retrieval_calls += 1

            # Increase retrieval depth on each pass so the
            # base retriever can expose additional evidence.
            batch_size = self.top_k * retrieval_number

            new_documents = self.base_retriever.retrieve(
                query,
                top_k=batch_size,
            )

            for index, document in enumerate(new_documents):
                document_id = document.document_id

                if document_id is None:
                    document_id = (
                        f"__anonymous__"
                        f"{retrieval_calls}_"
                        f"{index}"
                    )

                if document_id not in seen_ids:
                    seen_ids.add(document_id)
                    all_documents.append(document)

            # Jev always evaluates the original user question
            # against all accumulated evidence.
            (
                assessment,
                in_tokens,
                out_tokens,
                _raw,
            ) = self.evaluator.evaluate(
                query,
                all_documents,
            )

            jev_calls += 1

            input_tokens += in_tokens
            output_tokens += out_tokens

            action, reason = self.controller.decide(
                assessment,
                retrieval_number=retrieval_number,
                max_retrievals=self.max_retrievals,
            )

            decisions.append(
                ControllerDecision(
                    action=action,
                    reason=reason,
                    query=query,
                    retrieval_number=retrieval_number,
                )
            )

            if action is RetrievalAction.STOP:
                break

        assert assessment is not None

        return RetrievalResult(
            query=query,
            documents=all_documents,
            assessment=assessment,
            decisions=decisions,
            retrieval_calls=retrieval_calls,
            jev_calls=jev_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=None,
            iterations=retrieval_calls,
        )