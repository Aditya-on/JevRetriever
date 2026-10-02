# JevRetriever

Adaptive evidence retrieval on top of any base retriever, powered by Jev.

JevRetriever adds an evidence-evaluation and retrieval-control loop around an
existing retriever. You provide the retrieval system; Jev evaluates whether
the accumulated evidence is sufficient and determines whether another
retrieval should be performed.

## How it works

```text
User query
    │
    ▼
Base retriever
    │
    ▼
Retrieved evidence
    │
    ▼
Jev evaluates evidence
    │
    ├── sufficient ───────────────► STOP
    │
    └── insufficient
            │
            ▼
       Next retrieval action
            │
            ▼
       Base retriever
            │
            ▼
       Jev evaluates again
            │
            ▼
          repeat
            │
            ▼
     maximum retrieval limit
            │
            ▼
           STOP