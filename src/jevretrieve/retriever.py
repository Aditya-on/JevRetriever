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
    """Minimal contract for a developer's existing retriever."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        ...


class JevRetriever:
    """Adaptive evidence retrieval around any base retriever.

    The developer supplies a base retriever and a hard maximum number
    of retrieval calls.

    The original user query remains the question Jev evaluates.
    Jev may produce a follow-up query, which is used only for the
    next retrieval call.
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
        )

    def retrieve(self, query: str) -> RetrievalResult:
        """Retrieve evidence adaptively using Jev."""

        if not query or not query.strip():
            raise ValueError(
                "query must not be empty."
            )

        # Keep the user's original question fixed.
        original_query = query

        # This query may change after each Jev decision and is used
        # only when calling the developer's base retriever.
        current_query = query

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
            # ---------------------------------------------------------
            # Retrieve using the current retrieval query.
            # ---------------------------------------------------------
            retrieval_calls += 1

            batch_size = self.top_k * retrieval_number

            new_documents = self.base_retriever.retrieve(
                current_query,
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

            # ---------------------------------------------------------
            # IMPORTANT:
            #
            # Jev always evaluates the ORIGINAL user question against
            # the accumulated evidence.
            #
            # current_query is NOT passed here.
            # ---------------------------------------------------------

            # 🔴✓ API CALL — TypeSafe Jev
            (
                assessment,
                in_tokens,
                out_tokens,
                _raw,
            ) = self.evaluator.evaluate(
                original_query,
                all_documents,
            )

            jev_calls += 1

            input_tokens += in_tokens
            output_tokens += out_tokens

            # ---------------------------------------------------------
            # Let the controller decide whether to stop or retrieve
            # again.
            #
            # current_query is used here because the next retrieval
            # may need a more specific query suggested by Jev.
            # ---------------------------------------------------------

            action, reason, next_query = self.controller.decide(
                assessment,
                current_query=current_query,
                retrieval_number=retrieval_number,
                max_retrievals=self.max_retrievals,
            )

            decisions.append(
                ControllerDecision(
                    action=action,
                    reason=reason,
                    query=current_query,
                    retrieval_number=retrieval_number,
                )
            )

            if action is RetrievalAction.STOP:
                break

            # Use Jev's follow-up query only for the next retrieval.
            current_query = next_query

        assert assessment is not None

        return RetrievalResult(
            query=original_query,
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