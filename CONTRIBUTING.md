# Contributing to athenspop

Contributions should preserve the package's module boundaries, typed public contracts, and behavior-based tests. Use module imports, Google-style docstrings, and complete prose for user-facing and developer-facing text. Keep plotting functions independent of figure size, font size, color palettes, and publication styles unless a visual contract requires a specific setting.

## Development environment

Install the locked development environment with Python 3.12 or later:

```console
uv sync --locked --all-groups
```

Run the complete local verification suite before submitting a change:

```console
uv run ruff format --check src tests examples docs/conf.py
uv run ruff check src tests examples docs/conf.py
uv run ty check src tests examples docs/conf.py
uv run coverage run -m pytest
uv run coverage report
uv run python examples/compose_schedule.py
uv run python examples/analyze_athens.py
uv run sphinx-build -W --keep-going -b html docs docs/_build/html
uv build
```

Set `MPLBACKEND=Agg` before running the examples in a headless environment.

Tests should state observable behavior or a public contract. Add the smallest deterministic case that fails for the defect or boundary under review. Avoid assertions about private implementation structure when a public operation can establish the same condition.

## Changes and review

Keep each change focused and explain any user-visible behavior, data-contract change, or methodological implication. Documentation changes must preserve the distinction between demonstrated behavior, analytical choices, and limitations. Define each public behavior once in the module that owns it.

By contributing, you agree that software contributions are released under the repository's [MIT License](LICENSE). The processed Athens tables retain their separate [CC BY 4.0 International license](data/athens/LICENSE).
