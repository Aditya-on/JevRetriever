# JevRetriever

**Adaptive evidence retrieval for Python, powered by Jev.**

JevRetriever is a reusable retrieval framework that wraps an existing base retriever and uses **TypeSafe Jev** to decide whether the accumulated evidence is sufficient or whether another retrieval pass is useful.

## What JevRetriever Does

```text
User query
    ↓
Base retriever
    ↓
Jev evaluates accumulated evidence
    ↓
Sufficient? ── YES ──→ STOP
    │
    NO
    ↓
Retrieve again with the same query
    ↓
Jev evaluates again
    ↓
...
    ↓
Maximum retrieval limit
    ↓
STOP
```

Jev evaluates:

- **Sufficiency**
- **Coverage**
- **Relevance**
- **Redundancy**
- **Missing information**

The base retriever remains responsible for finding documents. Jev acts as the evidence evaluator and retrieval controller.

## Installation

```bash
pip install jevretrieve
```

Or install the specific release:

```bash
pip install jevretrieve==0.1.3
```

## Quick Start

```python
from jevretrieve import JevRetriever, RetrievedDocument


class MyRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        return [
            RetrievedDocument(
                text="Your retrieved document text...",
                document_id="doc-1",
                score=0.91,
            )
        ]


retriever = JevRetriever(
    base_retriever=MyRetriever(),
    jev_api_key="YOUR_TYPESAFE_API_KEY",
)

result = retriever.retrieve(
    "What caused the incident and when was the change introduced?"
)

for document in result.documents:
    print(document.document_id)
    print(document.text)

print(result.assessment.sufficiency)
print(result.assessment.coverage)
print(result.retrieval_calls)
print(result.jev_calls)
```

## API Key

Pass the key directly:

```python
JevRetriever(
    base_retriever=my_retriever,
    jev_api_key="YOUR_TYPESAFE_API_KEY",
)
```

Or use the environment variable:

```bash
export TYPESAFE_API_KEY=YOUR_TYPESAFE_API_KEY
```

On Windows:

```powershell
$env:TYPESAFE_API_KEY="YOUR_TYPESAFE_API_KEY"
```

## Base Retriever Interface

JevRetriever works with an existing retriever implementing:

```python
def retrieve(
    self,
    query: str,
    top_k: int = 5,
) -> list[RetrievedDocument]:
    ...
```

A document can be represented as:

```python
RetrievedDocument(
    text="Document content",
    document_id="unique-document-id",
    score=0.87,
    metadata={"source": "example"},
)
```

The framework is independent of the underlying retrieval implementation. The base retriever can use dense embeddings, BM25, MMR, similarity search, a vector database, or another retrieval strategy.

## Configuration

```python
JevRetriever(
    base_retriever=my_retriever,
    max_retrievals=10,
    top_k=5,
    jev_api_key="YOUR_TYPESAFE_API_KEY",
    jev_model="jev-latest",
    sufficiency_threshold=0.85,
    coverage_threshold=0.85,
    redundancy_threshold=0.65,
)
```

### `max_retrievals`

Maximum number of retrieval iterations allowed.

Default:

```python
max_retrievals=10
```

This is a hard safety limit.

For the benchmark experiments:

```python
max_retrievals=3
```

This allowed up to three retrieval iterations. In the observed benchmark runs, Jev never required a third iteration; when additional retrieval was triggered, the controller stopped after the second iteration.

### `top_k`

The initial retrieval size. Later passes request progressively larger batches:

```text
pass 1 → top_k × 1
pass 2 → top_k × 2
pass 3 → top_k × 3
```

### Thresholds

Default values:

```text
sufficiency_threshold = 0.85
coverage_threshold    = 0.85
redundancy_threshold  = 0.65
```

## Retrieval Result

`retrieve()` returns a `RetrievalResult` containing:

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

The final assessment contains:

```python
result.assessment.sufficiency
result.assessment.coverage
result.assessment.relevance
result.assessment.redundancy
result.assessment.missing_information
```

Controller decisions use:

```python
RetrievalAction.STOP
RetrievalAction.RETRIEVE_MORE
```

## Controller Behavior

The controller follows this order:

1. Maximum retrieval limit reached → `STOP`
2. Evidence is substantially redundant → `STOP`
3. Evidence is sufficiently complete and no important information is missing → `STOP`
4. Important information is missing → `RETRIEVE_MORE`
5. Otherwise → `RETRIEVE_MORE`

## 50-Question Benchmark

JevRetriever was evaluated on a 50-question subset of the **HotpotQA distractor** benchmark using:

- MMR
- Dense retrieval
- BM25
- Similarity search

Each retriever was evaluated with and without Jev using the same benchmark questions and answer-generation setup.

### Answer Accuracy

| Retriever | Baseline | + Jev | Change |
|---|---:|---:|---:|
| MMR | 40.00% | 48.00% | +8.00 pp |
| Dense | 36.00% | 44.00% | +8.00 pp |
| BM25 | 42.00% | 44.00% | +2.00 pp |
| Similarity | 34.00% | 44.00% | +10.00 pp |

### Supporting-Document Recall

| Retriever | Baseline | + Jev | Change |
|---|---:|---:|---:|
| MMR | 81.47% | 94.67% | +13.20 pp |
| Dense | 80.17% | 86.83% | +6.66 pp |
| BM25 | 76.67% | 83.33% | +6.66 pp |
| Similarity | 80.17% | 86.83% | +6.66 pp |

### Retrieval Expansion

| Retriever | Avg. docs — Baseline | Avg. docs — + Jev | Retrieval calls | Jev calls |
|---|---:|---:|---:|---:|
| MMR | 4.94 | 6.34 | 64 | 64 |
| Dense | 4.94 | 5.64 | 57 | 57 |
| BM25 | 4.94 | 5.54 | 56 | 56 |
| Similarity | 4.94 | 5.64 | 57 | 57 |

The benchmark showed increased supporting-document recall for all four retriever types when Jev-controlled adaptive retrieval was enabled.

Better evidence coverage does not automatically produce the same increase in final answer accuracy; answer generation and reasoning remain separate components of the RAG pipeline.

## Benchmark Notes

The benchmark used the HotpotQA **distractor** setting, where each question is evaluated against a fixed candidate context containing supporting and distractor Wikipedia paragraphs.

Therefore, these experiments primarily evaluate **adaptive selection from a fixed candidate pool** rather than open-ended retrieval across the entire Wikipedia corpus.

The supporting-recall metric used in these experiments is **paragraph-title recall**, not sentence-level supporting-fact recall.

## Why Use JevRetriever?

A conventional RAG pipeline often uses:

```text
query → retrieve top 5 → answer
```

JevRetriever allows retrieval to respond to evidence quality:

```text
query
  ↓
retrieve
  ↓
evaluate evidence
  ↓
enough? → answer
  ↓
not enough
  ↓
retrieve more
  ↓
evaluate again
  ↓
answer
```

This can be useful when:

- some questions are answerable with a small amount of evidence;
- other questions require multiple supporting documents;
- retrieved evidence can be redundant;
- missing information should trigger additional retrieval;
- developers want a hard upper bound on retrieval effort.

## Package Architecture

```text
jevretrieve/
├── __init__.py
├── client.py
├── controller.py
├── evaluator.py
├── models.py
└── retriever.py
```

### Main Components

**`BaseRetriever`** — Minimal interface expected from an existing retriever.

**`JevClient`** — Handles communication with the TypeSafe Jev System One API.

**`EvidenceEvaluator`** — Sends the query and accumulated evidence to Jev and converts the response into an `EvidenceAssessment`.

**`RetrievalController`** — Uses the Jev assessment to choose `STOP` or `RETRIEVE_MORE`.

**`JevRetriever`** — Coordinates the complete adaptive retrieval loop.

**Models** — `RetrievedDocument`, `EvidenceAssessment`, `ControllerDecision`, `RetrievalAction`, and `RetrievalResult`.

## Development

```bash
git clone https://github.com/Aditya-on/JevRetriever.git
cd JevRetriever
pip install -e .
pytest
```

## Version

Current release:

```text
0.1.3
```

## Project Status

JevRetriever is an early public release focused on the core adaptive evidence-retrieval abstraction.

Current capabilities include:

- retriever-agnostic interface;
- Jev-based evidence evaluation;
- adaptive retrieval control;
- evidence accumulation and document deduplication;
- configurable retrieval limits and thresholds;
- token-usage tracking;
- unit tests;
- PyPI distribution;
- benchmark evaluation across multiple retrieval strategies.

## License

MIT License.
