# QNet-VeriVal

QNet-VeriVal is a research prototype framework/software for verification and validation of critical distributed systems. The included case study focuses on a metropolitan multi-hop Quantum Key Distribution (QKD) network with end users, trusted relays, authentication service, and key-management server.

The framework demonstrates:

- protocol modeling for distributed quantum-classical workflows
- finite-state verification of safety and liveness properties
- fault injection for realistic coordination faults
- mutation analysis for property-strength validation
- counterexample-based diagnosis
- web-based interface and JSON API

## Why this software exists

The paper proposes QNet-VeriVal as a reusable framework, not only a single QKD model. QKD is used as the critical case study because it combines security-sensitive communication, distributed coordination, relay forwarding, authentication, key management, and strict protocol ordering.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m backend.app
```

Open:

```text
http://127.0.0.1:8000
```

## Run in GitHub Codespaces

1. Open the GitHub repository.
2. Click `Code`.
3. Select `Codespaces`.
4. Click `Create codespace on main`.
5. In the terminal run:

```bash
pip install -r requirements.txt
python -m backend.app
```

Open forwarded port `8000`.

## Run with Docker

```bash
docker build -t qnet-verival .
docker run -p 8000:8000 qnet-verival
```

Open:

```text
http://127.0.0.1:8000
```

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Web interface |
| `/api/health` | GET | Health check |
| `/api/model` | GET | Load sample QKD model |
| `/api/verify` | POST | Run formal verification |
| `/api/validate` | POST | Run full validation |
| `/api/fault` | POST | Run a selected fault injection |
| `/api/mutation` | POST | Run a selected mutation |
| `/api/catalog` | GET | List available faults and mutations |

## Project structure

```text
qnet-verival/
├── backend/
│   ├── app.py
│   └── qnet_verival/
│       ├── engine.py
│       ├── models.py
│       └── sample.py
├── frontend/
│   └── index.html
├── examples/
│   └── metropolitan_qkd.json
├── docs/
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

## Suggested citation text

QNet-VeriVal is a verification and validation framework for critical distributed quantum communication protocols. It integrates formal model construction, temporal property verification, fault injection, mutation analysis, and counterexample-based diagnosis within a unified software workflow.
