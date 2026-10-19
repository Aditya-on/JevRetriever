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

## Benchmark Metric Definitions and Calculations

The benchmark reports three complementary metrics. They describe different aspects of the system and should not be treated as interchangeable.

### 1. Answer Accuracy

**What it measures:** The percentage of benchmark questions for which the system's generated answer matches the expected answer under the benchmark's answer-evaluation method.

**Calculation:**

```text
Answer Accuracy (%) =
    (Number of questions answered correctly
     / Total number of evaluated questions) × 100
```

For a 50-question benchmark, if 24 answers are marked correct:

```text
Answer Accuracy = (24 / 50) × 100 = 48%
```

**What it means:** Higher accuracy means the system answered more questions correctly. Comparing `Baseline` with `+ Jev` shows whether Jev-guided retrieval was associated with improved answer accuracy in this experiment.

**How to read the change:** `+8.00 pp` means an increase of 8 percentage points, such as 40% to 48%. It does not mean an 8% relative increase.

### 2. Supporting-Document Recall

**What it measures:** The proportion of ground-truth supporting paragraphs that were retrieved. In this benchmark, the metric uses supporting paragraph titles as the reference; it is not sentence-level supporting-fact recall.

**Per-question calculation:**

```text
Supporting-Document Recall =
    Number of ground-truth supporting paragraph titles retrieved
    / Total number of ground-truth supporting paragraph titles
```

To express it as a percentage, multiply the result by 100.

For example, if a question has 3 ground-truth supporting paragraphs and the retriever finds 2 of them:

```text
Supporting-Document Recall = (2 / 3) × 100 = 66.67%
```

**How to interpret the benchmark average:** The table reports benchmark percentages. The exact aggregation method (for example, averaging per-question recall versus pooling counts across questions) depends on the evaluation code; it cannot be determined from the table alone.

**What it means:** Higher recall means the retriever found a larger proportion of the identified supporting paragraphs. It does not guarantee that the final answer is correct, nor does it measure whether every supporting sentence was retrieved.

### 3. Retrieval Expansion

**What it measures:** How the average number of returned documents changes when Jev-guided adaptive retrieval is enabled. The table also reports the number of base-retriever calls and Jev evaluation calls.

**Calculation of average documents:**

```text
Average Documents =
    Total number of documents counted across evaluated questions
    / Number of evaluated questions
```

The exact document-counting and aggregation details should follow the benchmark evaluation code.

**Calculation of additional average documents:**

```text
Additional Average Documents =
    Average Docs (+ Jev) - Average Docs (Baseline)
```

**Calculation of relative expansion:**

```text
Relative Expansion (%) =
    ((Average Docs (+ Jev) - Average Docs (Baseline))
     / Average Docs (Baseline)) × 100
```

For example, for MMR:

```text
Additional Average Documents = 6.34 - 4.94 = 1.40

Relative Expansion = ((6.34 - 4.94) / 4.94) × 100
                   ≈ 28.34%
```

**What it means:** MMR returned an average of 1.40 more documents with Jev enabled, an increase of approximately 28.34% relative to its baseline average. More retrieved documents indicate retrieval expansion, not necessarily better evidence; Supporting-Document Recall and Answer Accuracy help assess whether that expansion was useful.

**Retrieval calls and Jev calls:** These are call counts reported by the benchmark. A retrieval call is a call to the base retriever; a Jev call is an evaluation request to Jev. Equal totals in the table do not, by themselves, establish the exact per-question sequence or number of iterations.

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
