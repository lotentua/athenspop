# V1 Release Readiness Note

This note records the current release-validation evidence for the long-form canonical rewrite on 2026-06-19. It is not a claim that the package is absolutely bug free; it is the evidence-backed readiness state for the first complete maintainable release target in `docs/plans/long_canonical_rewrite_plan.md`.

## Validation Evidence

| Check | Command | Current result |
| --- | --- | --- |
| Unit and example tests | `uv run rtk pytest -q tests examples\paper` | `95 passed`. |
| Ruff lint | `uv run ruff check .` | Passed. |
| Ruff format check | `uv run ruff format --check .` | Passed after Ruff formatted `tests/test_paper_reproduction_artifacts.py`. |
| Static type check | `uv run ty check` | Passed. |
| Sphinx docs build | `uv run sphinx-build -W -b html docs docs\_build\html` | Passed with 17 documentation sources including the new paper walkthrough. |
| Package build | `uv build` | Built `dist\athenspop-0.1.0.tar.gz` and `dist\athenspop-0.1.0-py3-none-any.whl`. |
| Installed-wheel quickstart smoke | Temporary virtual environment plus `uv pip install --python .codex_tmp_release_venv\Scripts\python.exe dist\athenspop-0.1.0-py3-none-any.whl` | Passed with Python 3.12.11, `athenspop==0.1.0`, NumPy 2.4.6, pandas 3.0.3, and SciPy 1.17.1; the documented quickstart dataframe validated, loaded, scheduled, and preserved `departure_second = 0`. |
| Full paper artifact command | `uv run python -m examples.paper.reproduce` | Passed and wrote validated artifacts to `examples/paper/output/full` in 41.776 seconds in the normal measured run. |
| Paper walkthrough snippet probe | Focused runtime probe following `docs/user_guide/paper_walkthrough.md` through source verification, input conversion, validation, scheduling, return-home imputation, episode/state checks, toy transition costs, and demographics | Passed. |

## Current Release Interpretation

The canonical library surface is `athenspop.validation`, `athenspop.model`, `athenspop.io`, `athenspop.scheduling`, `athenspop.generation`, `athenspop.sequence`, and `athenspop.clustering`, with top-level public imports intentionally re-exported from `athenspop`.

The paper workflow is an example, not the package identity. It is maintained under `examples/paper` and documented through `docs/user_guide/paper_reproduction.md`, `docs/user_guide/paper_walkthrough.md`, `docs/design/paper_method_contract.md`, and `docs/design/paper_output_manifest.md`.

The generated full paper artifacts are ignored by Git and should be regenerated with `uv run python -m examples.paper.reproduce` when needed. Public docs deliberately point to reproducible output paths rather than checking generated SVGs into the docs build.

## Residual Risks And Deferred Work

- Exact PGF or pixel-level reproduction of the paper's original figure files is deferred; v1 acceptance is based on documented data, hierarchy, cluster sizes, temporal state distributions, and portable SVG outputs.
- MATSim and PAM import/export adapters are deferred; the generic package design keeps future interoperability possible but does not promise adapters in v1.
- Sequenzo is not used in v1. Local optimal matching preserves the paper-specific self-transition-excluding transition-cost semantics; Sequenzo remains a future acceleration candidate only after custom-matrix parity and performance are proven.
- The largest runtime hotspot is still the 512 by 512 optimal-matching dissimilarity matrix. Current runtime is comfortably below the 10-minute v1 threshold on this machine, so no compiled extension, multiprocessing layer, or new dependency is justified for v1.
- The release validation was performed in the current dirty implementation branch plus an installed-wheel temporary environment, not from a separately cloned clean checkout. Before publishing a tag, repeat the validation commands after staging or committing the intended source tree.
