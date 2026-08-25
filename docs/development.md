# Development guide

This page explains how the repository fits together and where a change belongs. The shorter [contribution guide](https://github.com/lotentua/athenspop/blob/v2/CONTRIBUTING.md) contains the setup commands and pull-request checklist.

## Find the stage that owns the behavior

`athenspop` moves data through explicit boundaries:

| Stage | Module | Responsibility |
| --- | --- | --- |
| Input conversion | [Input conversion API](api/io.md) | Convert source clock values into package time |
| Validation | [Validation API](api/validation.md) | Interpret untrusted dataframes and collect issues |
| Model | [Model API](api/model.md) | Hold trusted immutable diaries and metadata |
| Scheduling | [Scheduling API](api/scheduling.md) | Realize one feasible schedule |
| Generation | [Generation API](api/generation.md) | Repeat scheduling with derived seeds |
| Sequence | [Sequence API](api/sequence.md) | Build episodes, discretize states, and calculate distances |
| Clustering | [Clustering API](api/clustering.md) | Build, cut, and summarize hierarchies |
| Visualization | [Visualization API](api/visualization.md) | Render a temporal cluster view |

A shared validation rule belongs at the dataframe boundary. A scheduling constraint belongs in the scheduler. Plotting code should consume established model and clustering contracts rather than reinterpret them.

## Install the locked environment

[uv](https://docs.astral.sh/uv/) resolves the development, documentation, and optional visualization dependencies:

```console
uv sync --locked --all-groups
```

Use the locked environment when reproducing a failure or validating a release. Update `uv.lock` only when the dependency declaration changes intentionally.

## Check code and types

[Ruff](https://docs.astral.sh/ruff/) applies formatting and the configured lint rules. [ty](https://docs.astral.sh/ty/) checks source, tests, examples, and the Sphinx configuration.

```console
uv run ruff format --check .
uv run ruff check .
uv run ty check src tests examples docs/conf.py
```

The project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html). Use qualified module imports for project code, document public contracts with Google-style docstrings, and keep runtime checks at untrusted boundaries.

## Test contracts rather than helper structure

Tests use [pytest](https://docs.pytest.org/) in importlib mode. They should exercise behavior a user or adjacent module can observe:

- normalized data or a structured validation issue;
- a scheduled trip or a clear infeasibility diagnostic;
- an exact state sequence or dissimilarity;
- a stable hierarchy property; or
- visible figure geometry and labels.

Use small inputs and fixed random seeds. Close Matplotlib figures. A regression test should make the corrected failure easy to recognize from its name and assertions.

```console
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=95
```

## Keep examples executable and explanations readable

Files under `examples/` are ordinary Python modules with reusable functions and small script entry points. Their workflow pages use `literalinclude` so the displayed code cannot drift from the executable source.

Documentation is built with [Sphinx](https://www.sphinx-doc.org/), [MyST Parser](https://myst-parser.readthedocs.io/), and the [PyData Sphinx Theme](https://pydata-sphinx-theme.readthedocs.io/).

```console
uv run python examples/compose_schedule.py
uv run python examples/analyze_athens.py
uv run sphinx-build -nW --keep-going -b html docs docs/_build/html
```

Use a tutorial for learning, a workflow for a goal, a concept page for explanation, and reference for exact behavior. The [Diátaxis map](https://diataxis.fr/map/) explains the distinction. Link every public symbol mentioned in Sphinx prose to its generated API target.

Figures should inherit the caller's dimensions, typography, and palette unless a quantitative visual contract requires otherwise. Inspect a raster rendering whenever a figure changes; an SVG that compiles is not necessarily legible.

## Build the release artifacts

Run both examples and the warning-free documentation build before creating archives:

```console
uv build --clear
```

The wheel must contain the same `athenspop` package files as `src/athenspop`. The source archive also includes tests, examples, documentation, and the separately licensed Athens data. Install the wheel in an isolated environment for a final import smoke test.
