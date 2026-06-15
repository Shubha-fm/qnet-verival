# Artifact Description

This artifact supports the QNet-VeriVal framework paper. It provides a runnable implementation of the proposed framework and a metropolitan multi-hop QKD case study.

## Main artifact functions

1. Load a distributed QKD model.
2. Explore the finite-state protocol workflow.
3. Verify safety and liveness properties.
4. Inject realistic protocol faults.
5. Apply mutation analysis.
6. Diagnose violations using counterexample traces.

## Reproducibility

Run:

```bash
pip install -r requirements.txt
python -m backend.app
```

Then open `http://127.0.0.1:8000`.
