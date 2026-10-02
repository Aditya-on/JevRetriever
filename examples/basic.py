from jevretrieve import JevRetriever, RetrievedDocument


class MyHybridRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        # Replace this with your real Dense / Hybrid / BM25 / MMR retriever.
        return [
            RetrievedDocument(
                document_id="example-1",
                text="Example evidence returned by your retriever.",
                score=0.95,
            )
        ]


retriever = JevRetriever(
    base_retriever=MyHybridRetriever(),
    max_retrievals=10,
    jev_api_key="YOUR_TYPESAFE_KEY",
)

result = retriever.retrieve(
    "What caused the incident and who was responsible?"
)

print("Retrieval calls:", result.retrieval_calls)
print("Jev calls:", result.jev_calls)
print("Sufficiency:", result.assessment.sufficiency)

for document in result.documents:
    print(document.document_id, document.text)
