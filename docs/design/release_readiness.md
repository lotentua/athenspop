# Release Readiness Record

This record reports the release-candidate evidence collected on 24 August 2026. The software and documentation gates pass. The public Git repository and pushed integration branch already expose the manuscript, survey and routing resources. Their redistribution authority remains unresolved.

## Verification Evidence

| Check | Command | Result |
| --- | --- | --- |
| Complete test graph | `uv run pytest -q` | 207 passed in 39.25 seconds |
| Ruff lint | `uv run ruff check .` | Passed |
| Ruff format | `uv run ruff format --check .` | Passed for 96 files |
| Static types | `uv run ty check` | Passed |
| Sphinx | `uv run sphinx-build -W -b html docs docs/_build/html` | Passed with warnings treated as errors |
| Distributions | `uv build` | Built the 0.1.0 source and wheel distributions |
| Installed wheel | Isolated `uv run --no-project --with <wheel>` quickstart | Passed; the core import did not install Matplotlib |
| Migrated reanalysis | `uv run python -m examples.athens.reproduce` | Passed below 2 minutes, within the 10-minute release threshold |
| Artifact contract | `validate_athens_artifacts(...)` on the fresh reanalysis | 167 checks passed |

The source distribution contains the generic package, license, README, project metadata, and lockfile. It excludes the manuscript, Athens inputs, generated outputs, examples, tests, and documentation.

## Scientific Claim Boundary

The frozen paper-result reference identifies downstream arrays retained from historical commit `75d1cd5ae186ece22c3f0f7eabb58c2a4659df0f`. Reclustering its retained dissimilarity matrix yields the ten cluster sizes and two-decimal normalized heights shown in the paper. The retained state sequences contain 13 labels although the manuscript describes 15 unreduced states. The repository therefore calls this surface a paper-result reference, not an end-to-end reproduction.

The migrated reanalysis regenerates artifacts from hashed survey and routing inputs with the refactored pipeline. It preserves all 15 unreduced activity and travel states and records method, random-number, dependency, lockfile, input, and exclusion provenance. The routing fallback affects 209 trips in 97 diaries, including 27 imputed returns. Of 124 activity-duration-imputed returns, 43 begin after the observation horizon and 4 cross it; the sequence crop therefore removes or truncates them. Its numerical clustering differs from the frozen reference and is labeled accordingly.

## Open Release Condition

The public repository contains the raw survey, derived routing resources, and manuscript files. The MIT software license does not establish authority to redistribute those materials. The owner must document their provenance and redistribution authority or remove them from public Git history and provide an acquisition and hash-verification procedure.

Committing and pushing this release-candidate branch does not resolve the existing exposure. The built Python distributions use a narrower software-only surface.
