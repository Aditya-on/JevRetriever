# JevRetriever

Adaptive evidence retrieval on top of your existing retriever.

JevRetriever does not replace your search system. You give it any base
retriever—dense, BM25, hybrid, MMR, similarity search, vector database
adapter, or your own implementation—and JevRetriever decides whether more
evidence is needed.

## Install

```bash
pip install jevretrieve
```

For local development:

```bash
pip install -r requirements.txt
```

## Quick start

```python
from jevretrieve import JevRetriever, RetrievedDocument


class MyRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        # Use your own Dense / Hybrid / BM25 / MMR / custom search here.
        return [
            RetrievedDocument(
                document_id="doc-1",
                text="Your retrieved document text",
                score=0.91,
            )
        ]


retriever = JevRetriever(
    base_retriever=MyRetriever(),
    max_retrievals=10,
    jev_api_key="YOUR_TYPESAFE_KEY",
)

result = retriever.retrieve(
    "What caused the incident and who was responsible?"
)

for document in result.documents:
    print(document.text)
```

## How it works

```text
Your base retriever
        |
        v
   Initial evidence
        |
        v
    Jev judges
        |
   +----+----+
   |         |
 enough?   not enough
   |         |
 STOP     next action
             |
       +-----+------+
       |            |
   retrieve more  change query
       |            |
       +-----+------+
             |
          Jev again
             |
            ...
             |
       hard retrieval limit
             |
            STOP
```

The base retriever is completely application-specific.

JevRetriever only requires:

```python
class MyRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        ...
```

`max_retrievals` is a hard upper bound on calls to your base retriever. Jev
may stop after 1, 2, 5, or another number of calls, but it will never exceed
the configured limit.

## Result object

```python
result.documents
result.assessment
result.decisions
result.retrieval_calls
result.jev_calls
result.input_tokens
result.output_tokens
result.total_jev_tokens
result.total_cost
result.iterations
```

`evidence_recall` is a benchmark metric that requires gold evidence labels.
It is not inferred automatically for arbitrary production data.

## API key

Pass the key directly:

```python
JevRetriever(
    base_retriever=my_retriever,
    max_retrievals=10,
    jev_api_key="YOUR_TYPESAFE_KEY",
)
```

or set:

```text
TYPESAFE_API_KEY=YOUR_TYPESAFE_KEY
```

JevRetriever does not store your key on disk.

## Current MVP scope

- Generic base retriever interface
- Jev evidence judgment
- Adaptive stopping
- Query expansion driven by Jev
- Retrieval budget / hard upper limit
- Token and cost telemetry
- No required vector database
- No required embedding model
- No required framework such as LangChain

The package intentionally does not force a particular retrieval backend.

## Development

```bash
python -m pip install -r requirements.txt
python -m pytest
python -m pip install -e .
```

## License

MIT
