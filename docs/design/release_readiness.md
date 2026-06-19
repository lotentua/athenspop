# Migration Validation Note

This internal note records validation evidence for the generic-source migration on 2026-06-19.
It is not public release messaging and it is not a claim that the package is absolutely bug free.

## Validation Evidence

| Check | Command | Current result |
| --- | --- | --- |
| Unit tests | `uv run pytest -q tests` | `65 passed`. |
| Athens example tests | `uv run pytest -q examples\athens\tests` | `36 passed`. |
| Ruff lint | `uv run ruff check .` | Passed. |
| Ruff format check | `uv run ruff format --check .` | Passed. |
| Static type check | `uv run ty check` | Passed. |
| Sphinx docs build | `uv run sphinx-build -W -b html docs docs\_build\html` | Passed with public docs and API pages warning-clean. |
| Package build | `uv build` | Built `dist\athenspop-0.1.0.tar.gz` and `dist\athenspop-0.1.0-py3-none-any.whl`. |
| Installed-wheel quickstart smoke | Temporary virtual environment plus `uv pip install --python .codex_tmp_release_venv\Scripts\python.exe dist\athenspop-0.1.0-py3-none-any.whl` | Passed with Python 3.12.11, `athenspop==0.1.0`, NumPy 2.4.6, pandas 3.0.3, and SciPy 1.17.1; the documented quickstart dataframe validated, loaded, scheduled, and preserved `departure_second = 0`. |
| Athens smoke command | `uv run python -m examples.athens.smoke` | Passed. |
| Athens artifact command | `uv run python -m examples.athens.reproduce` | Passed and wrote generated artifacts to `examples/athens/output/full`. |
| Public leakage checks | Targeted `rg` checks over `README.md`, `src`, `tests`, and public docs | Passed with no public paper, v1, old time-origin, or old example-module references. |

## Current Release Interpretation

The generic library surface is `athenspop.validation`, `athenspop.model`, `athenspop.io`, `athenspop.scheduling`, `athenspop.generation`, `athenspop.sequence`, `athenspop.clustering`, and `athenspop.visualization`, with top-level public imports intentionally re-exported from `athenspop`.

The Athens workflow is an example, not the package identity.
It is maintained under `examples/athens` and documented through `examples/athens/docs/athens_reproduction.md`, `examples/athens/docs/athens_walkthrough.md`, `examples/athens/docs/athens_method_contract.md`, and `examples/athens/docs/athens_output_manifest.md`.

The generated Athens artifacts are ignored by Git and should be regenerated with `uv run python -m examples.athens.reproduce` when needed.
Public docs deliberately keep the package surface generic rather than presenting any one example as the package identity.

## Residual Risks And Deferred Work

- Exact pixel-level matching to historical figure files is outside this migration gate; the important current evidence is the generic object-returning figure primitive plus the Athens example output command.
- MATSim and PAM import/export adapters remain deferred; the generic package design keeps future interoperability possible but does not promise adapters now.
- Sequenzo remains a future acceleration candidate only after custom-matrix parity and performance are proven.
- The largest runtime hotspot is still the 512 by 512 optimal-matching dissimilarity matrix, so profile-guided optimization remains deferred until the generic API boundary is stable.
- Repeat the validation commands from a clean checkout before publishing a tag.
