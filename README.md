# JevRetriever

Adaptive evidence retrieval on top of your existing retriever.

JevRetriever does not replace your search system. You give it any base
retriever—dense, BM25, hybrid, MMR, similarity search, vector database
adapter, or your own implementation—and Jev decides whether the accumulated
evidence is sufficient or whether another retrieval is needed.

## Install

```bash
pip install jevretrieve
```

For local development:

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from jevretrieve import JevRetriever, RetrievedDocument


class MyRetriever:
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
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

## How It Works

```text
Your base retriever
        |
        v
     Evidence
        |
        v
    Jev judges
        |
   +----+----------------+
   |                     |
sufficient?         not sufficient
   |                     |
  YES                    |
   |              more evidence useful?
  STOP               +---+---+
                     |       |
                    NO      YES
                     |       |
                    STOP   retrieve again
                              |
                              v
                         Jev judges again
                              |
                             ...
                              |
                    max retrieval limit
                              |
                             STOP
```

JevRetriever follows a simple adaptive evidence loop:

1. Your base retriever retrieves evidence for the user's query.
2. Jev evaluates the accumulated evidence.
3. If the evidence is sufficient, retrieval stops.
4. If the evidence is substantially redundant, retrieval stops.
5. Otherwise, JevRetriever calls the same base retriever again using the
   same original query.
6. The newly retrieved evidence is added to the accumulated evidence.
7. Jev evaluates the complete accumulated evidence again.
8. The process continues until stopping conditions are met or the maximum
   retrieval limit is reached.

Jev always evaluates the original user question against the accumulated
evidence.

The base retriever remains responsible for deciding which documents are
returned. JevRetriever controls the retrieval loop and stopping decision.

## Base Retriever Contract

JevRetriever only requires a retriever with this interface:

```python
class MyRetriever:
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        ...
```

The retriever can use any backend or retrieval strategy.

For example:

- Dense retrieval
- BM25
- Hybrid search
- MMR
- Vector database search
- Keyword search
- Custom retrieval systems
- Application-specific retrievers

JevRetriever does not require a specific retrieval framework.

## Retrieval Budget

`max_retrievals` is a hard upper bound on calls to your base retriever.

The library default is:

```python
max_retrievals=10
```

For example:

```python
retriever = JevRetriever(
    base_retriever=my_retriever,
    max_retrievals=10,
    jev_api_key="YOUR_TYPESAFE_KEY",
)
```

The retriever may stop earlier when:

- the accumulated evidence is sufficient, or
- the evidence is substantially redundant.

The hard retrieval limit prevents the controller from continuing
indefinitely.

## Retrieval Depth

The base retriever is called repeatedly with an increasing `top_k` value.

For example, with:

```python
top_k=5
```

the retrieval loop uses:

```text
retrieval 1 → top_k = 5
retrieval 2 → top_k = 10
retrieval 3 → top_k = 15
...
```

This allows compatible base retrievers to expose additional evidence on
later retrieval passes while keeping the original query unchanged.

The exact behavior of repeated retrieval depends on the base retriever.

## Evidence Accumulation

Documents from every retrieval pass are accumulated and evaluated together.

For example:

```text
Retrieval 1
    ↓
documents A, B, C

Retrieval 2
    ↓
documents A, B, C, D, E

Retrieval 3
    ↓
documents A, B, C, D, E, F, G
```

Jev evaluates the complete accumulated evidence rather than evaluating each
retrieval independently.

## Deduplication

JevRetriever removes duplicate documents using `document_id`.

This means that if the same document is returned by multiple retrieval
passes, it appears only once in the final result.

Example:

```python
RetrievedDocument(
    document_id="doc-123",
    text="Example evidence",
)
```

The `document_id` should identify the document consistently across retrieval
calls.

If a document does not provide a `document_id`, JevRetriever assigns an
internal anonymous identifier for that retrieval result.

## Evidence Assessment

Jev evaluates the accumulated evidence using several dimensions:

- `sufficiency`
- `coverage`
- `relevance`
- `redundancy`
- `missing_information`

Example:

```python
result.assessment.sufficiency
result.assessment.coverage
result.assessment.relevance
result.assessment.redundancy
result.assessment.missing_information
```

The values for the score-based fields are normalized between `0.0` and
`1.0`.

## Stopping Behavior

By default, JevRetriever uses the following thresholds:

```python
sufficiency_threshold=0.85
coverage_threshold=0.85
redundancy_threshold=0.65
```

Evidence is considered sufficient when both:

```text
sufficiency >= 0.85
coverage >= 0.85
```

Retrieval also stops when:

```text
redundancy >= 0.65
```

The thresholds can be customized:

```python
retriever = JevRetriever(
    base_retriever=my_retriever,
    max_retrievals=10,
    sufficiency_threshold=0.90,
    coverage_threshold=0.90,
    redundancy_threshold=0.70,
    jev_api_key="YOUR_TYPESAFE_KEY",
)
```

All threshold values must be between `0.0` and `1.0`.

## Result Object

`JevRetriever.retrieve()` returns a `RetrievalResult`.

Available fields include:

```python
result.query
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

### `query`

The original user query.

### `documents`

All unique documents accumulated during retrieval.

### `assessment`

Jev's final assessment of the accumulated evidence.

### `decisions`

The controller decision made after each retrieval iteration.

Each decision contains:

```python
decision.action
decision.reason
decision.query
decision.retrieval_number
```

The current controller uses:

```text
STOP
RETRIEVE_MORE
```

### `retrieval_calls`

Number of calls made to the base retriever.

### `jev_calls`

Number of Jev evaluations performed.

### `input_tokens`

Total Jev input tokens reported by the API.

### `output_tokens`

Total Jev output tokens reported by the API.

### `total_jev_tokens`

Convenience property:

```python
result.input_tokens + result.output_tokens
```

### `total_cost`

Total Jev cost when available from the API.

### `iterations`

Number of retrieval iterations performed.

## API Key

JevRetriever uses the TypeSafe Jev API.

You can provide the API key directly:

```python
retriever = JevRetriever(
    base_retriever=my_retriever,
    jev_api_key="YOUR_TYPESAFE_KEY",
)
```

Or set the environment variable:

```text
TYPESAFE_API_KEY=YOUR_TYPESAFE_KEY
```

Then:

```python
retriever = JevRetriever(
    base_retriever=my_retriever,
)
```

The environment-variable approach is recommended for applications so that
API keys do not need to be hard-coded into source files.

## Jev Model

The default Jev model is:

```python
jev_model="jev-latest"
```

It can be configured:

```python
retriever = JevRetriever(
    base_retriever=my_retriever,
    jev_model="jev-latest",
    jev_api_key="YOUR_TYPESAFE_KEY",
)
```

## Custom Jev Client

For testing or advanced integrations, a custom `JevClient` can be supplied:

```python
from jevretrieve import JevRetriever


retriever = JevRetriever(
    base_retriever=my_retriever,
    jev_client=my_jev_client,
)
```

This is useful for:

- Unit testing
- Integration testing
- Custom API clients
- Controlled experiments

## Backend-Agnostic Design

JevRetriever does not assume anything about how your application retrieves
documents.

Your existing retrieval system remains responsible for:

- indexing
- embeddings
- vector search
- keyword search
- ranking
- filtering
- metadata
- document storage

JevRetriever adds an adaptive evidence-control layer around that retriever.

```text
                 Your Application
                        |
                        v
                  JevRetriever
                   /          \
                  /            \
                 v              v
        Base Retriever      Jev Evaluation
                 |              |
                 v              v
             Evidence      Stop / Continue
                 \              /
                  \            /
                   v          v
                 Final Evidence
```

## Example Architecture

A typical application can use JevRetriever like this:

```text
User Question
      |
      v
JevRetriever
      |
      +-----------------------+
      |                       |
      v                       v
Base Retriever          Jev Evaluation
      |                       |
      v                       v
Documents              Evidence Judgment
      |                       |
      +-----------+-----------+
                  |
                  v
          Continue / Stop
                  |
                  v
           Final Evidence
                  |
                  v
              LLM Answer
```

The final answer generation remains outside JevRetriever.

JevRetriever is responsible for gathering and evaluating evidence.

## Example With a Custom Retriever

```python
from jevretrieve import JevRetriever, RetrievedDocument


class MyHybridRetriever:
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedDocument]:
        return [
            RetrievedDocument(
                document_id=f"doc-{index}",
                text=f"Retrieved evidence {index}",
                score=1.0 / index,
            )
            for index in range(1, top_k + 1)
        ]


retriever = JevRetriever(
    base_retriever=MyHybridRetriever(),
    max_retrievals=10,
)

result = retriever.retrieve(
    "What caused the production incident?"
)

print("Retrieval calls:", result.retrieval_calls)
print("Jev calls:", result.jev_calls)
print("Documents:", len(result.documents))

for decision in result.decisions:
    print(
        decision.retrieval_number,
        decision.action,
        decision.reason,
    )
```

## Example Output

A result can look conceptually like:

```text
Retrieval calls: 2
Jev calls: 2
Documents: 8

1 RETRIEVE_MORE Evidence is not yet sufficient. Retrieving more evidence.
2 STOP Evidence is sufficient and complete enough.
```

The exact result depends on the base retriever and Jev's evaluation.

## Current MVP Scope

JevRetriever currently focuses on a small, explicit responsibility:

- Generic base retriever interface
- Jev evidence judgment
- Adaptive stopping
- Evidence accumulation
- Document deduplication
- Increasing retrieval depth across iterations
- Retrieval budget / hard upper limit
- Token telemetry
- Optional cost telemetry
- Backend-agnostic design
- No required vector database
- No required embedding model
- No required retrieval framework

The controller intentionally keeps retrieval simple: the original query is
used for repeated retrieval passes rather than automatically rewriting or
diversifying the query.

## Requirements

- Python 3.10+
- `requests`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Development

Clone the repository and install the package in editable mode:

```bash
pip install -e .
```

Run the test suite:

```bash
python -m pytest
```

Build the package:

```bash
python -m build
```

Validate the distributions:

```bash
twine check dist/*
```

## Testing

The test suite uses deterministic fake retrievers and fake Jev clients for
core controller and retrieval-loop behavior.

This keeps the unit tests independent of live API calls.

The tests cover behavior including:

- stopping when evidence is sufficient
- retrieving again when evidence is insufficient
- stopping on substantial redundancy
- respecting the maximum retrieval limit
- preserving the original query
- accumulating evidence
- deduplicating documents
- rejecting invalid configuration
- rejecting empty queries

## Project Structure

```text
jevretrieve/
├── src/
│   └── jevretrieve/
│       ├── __init__.py
│       ├── client.py
│       ├── controller.py
│       ├── evaluator.py
│       ├── models.py
│       └── retriever.py
│
├── tests/
│   ├── test_models.py
│   └── test_retriever.py
│
├── examples/
│   └── basic.py
│
├── README.md
├── requirements.txt
└── pyproject.toml
```

## Design Principle

The central design principle is:

> Your retriever finds evidence. Jev decides when there is enough evidence.

This keeps JevRetriever independent from the underlying search technology
while providing an adaptive retrieval loop around existing retrieval
systems.

## Status

JevRetriever is an early-stage package focused on the core adaptive evidence
retrieval loop.

The API and behavior may evolve as the package develops.

## License

MIT
