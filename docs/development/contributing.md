# Contributing

Keep changes small, documented, and tested against the same public contract: dataframe validation at the boundary, trusted model objects internally, optional scheduling/generation, sequence analysis, and clustering.

Before editing source, read the relevant concept or user-guide page, update code and tests together, and keep examples dataset-specific rather than letting them leak into the generic library.

Run the repository gate before submitting changes:

```powershell
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format --check .
uv run --python 3.12 ty check
uv run --python 3.12 pytest -q
uv run --python 3.12 sphinx-build -W -b html docs docs/_build/html
```

Run the full reanalysis when changing its methods, inputs, provenance, or artifact contract:

```powershell
uv run --python 3.12 python -m examples.athens.reproduce
```
