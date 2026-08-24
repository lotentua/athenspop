# Testing

The repository gate is `uv run pytest -q`. Pytest collects both the generic suite under `tests` and maintained example tests under `examples/athens/tests` using importlib mode.

For a focused generic-library run, use `uv run pytest -q tests`. For the Athens example, use `uv run pytest -q examples/athens/tests`.

Final quality checks use non-mutating commands:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -q
uv run sphinx-build -W -b html docs docs/_build/html
```

The full Athens reanalysis is a separate release gate because its 512-by-512 optimal-matching stage is intentionally not repeated by every unit-test run:

```powershell
uv run python -m examples.athens.reproduce
```

The minimum supported Python gate runs the same checks under Python 3.12.
