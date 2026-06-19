# Testing

The generic library gate is `uv run pytest -q tests`.

Bare `uv run pytest -q` should collect the generic library suite under `tests` only.
Dataset-specific example tests are explicit so the reusable package boundary stays clear.

Final quality checks use non-mutating commands:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -q tests
uv run sphinx-build -W -b html docs docs/_build/html
```

The minimum supported Python gate runs the same checks under Python 3.12.
Run dataset-specific example tests from the example folder when validating the whole repository.
