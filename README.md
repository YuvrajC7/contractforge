# ContractForge

**Evidence-backed OpenAPI migration for a bounded Python client subset.** Runnable engineering prototype with a local browser demo, FastAPI endpoints, automated tests, and reproducible synthetic evaluation.

## Run locally

Use Python 3.13. From the repository directory:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python benchmark.py
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the interactive JSON demo or /docs for API schemas. The demo's Run button calls POST /demo. No API key is needed for the default path. Services are local demonstration applications without production authentication or rate limiting.

## Design and boundaries

An API field rename can break a consumer while unrelated string literals must remain unchanged. ContractForge compares inline OpenAPI GET /users response properties, accepts explicit x-renamed-from metadata, rewrites parameter subscript accesses using Python ASTs, and returns a readable diff plus before/after consumer checks.

`old/new response schema -> compatibility classification -> bounded AST codemod -> fixture interpreter -> reviewable diff`

The accepted client is one function returning a projection composed of dictionaries, lists, tuples, constants, and parameter subscripts. A custom interpreter evaluates this subset; it never executes submitted Python, imports modules, or uses eval. Calls, attributes, loops, decorators, and unsupported syntax are rejected. Unsupported removals and type changes cause abstention.

The benchmark uses 24 supported rename fixtures with five examples each and 16 unsupported changes. These are generated variants with held-out identifiers, not independently sourced repositories. This is a deterministic codemod, not an LLM agent, general OpenAPI compatibility checker, or arbitrary-code sandbox. External references, nested schema migrations, multi-file clients, and dependency builds are outside the implemented scope. Review every generated patch.

## Evaluation

The checked-in [benchmark report](reports/benchmark.json) contains measured results, source hashes, environment metadata, and scope notes. Run `python benchmark.py` to regenerate it; timing varies by machine. The test suite contains **14 passing cases** in the recorded local run. CI reruns tests and benchmarks on Ubuntu.

All generated transactions, documents, labels, and API fixtures are synthetic. Generators are in core.py and experiment definitions in benchmark.py. The generator plus fixed seeds is the reproducible data source; no private user, employer, or customer data is included. Finite passing checks do not prove universal correctness.

## Source map

| File | Responsibility |
| --- | --- |
| core.py | Domain logic and seeded fixtures |
| app.py | Validated API requests and demo routes |
| ui.py | Lightweight browser interface |
| tests/ | Regression and domain checks |
| benchmark.py | Reproducible evaluation workload |
| reports/benchmark.json | Measured local evidence |

## Development

Created with AI coding assistance. Claims describe the code and bounded evaluations in this repository. MIT licensed; see LICENSE.
