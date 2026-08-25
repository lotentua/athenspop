# Contributing to athenspop

Thanks for helping improve `athenspop`. Contributions are welcome across code, tests, documentation, examples, and the released data documentation.

The package is organized as a series of small analytical stages. A focused change should normally have one clear home: validation, model construction, scheduling, sequence representation, distance calculation, clustering, or visualization. Fix a shared rule at the earliest stage that owns it instead of repeating the rule downstream.

## Set up a development environment

The project uses [uv](https://docs.astral.sh/uv/) and supports Python 3.12 or later.

```console
git clone https://github.com/lotentua/athenspop.git
cd athenspop
uv sync --locked --all-groups
```

Run the full local check before opening a pull request:

```console
uv run ruff format --check .
uv run ruff check .
uv run ty check src tests examples docs/conf.py
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=95
uv run python examples/compose_schedule.py
uv run python examples/analyze_athens.py
uv run sphinx-build -nW --keep-going -b html docs docs/_build/html
uv build
```

Set `MPLBACKEND=Agg` before running examples on a headless machine.

## Make the behavior clear

A useful change explains the observable result before its implementation details. Add the smallest deterministic test that would fail without the change. Prefer a public return value, exception, diagnostic, or figure property over assertions about private helper structure.

Tests use [pytest](https://docs.pytest.org/), and coverage is measured with [coverage.py](https://coverage.readthedocs.io/). The 95% branch threshold is a release guard, not a reason to test unimportant lines. Spend test effort on data boundaries, scheduling constraints, error paths, and analytical contracts.

## Follow the Python conventions

Python code follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html). [Ruff](https://docs.astral.sh/ruff/) formats and lints source, tests, examples, and `docs/conf.py`; [ty](https://docs.astral.sh/ty/) checks them statically.

Use module imports and qualify project symbols:

```python
import athenspop.scheduling.engine

result = athenspop.scheduling.engine.schedule_once(dataset)
```

Document public behavior, assumptions, arguments, results, and material exceptions. A docstring should help someone use or maintain the symbol; it does not need to restate that a class is a class or a function is a function.

## Write documentation for a reader's task

The Sphinx documentation follows four broad roles:

- the tutorial teaches a complete first workflow;
- workflow pages help an experienced reader accomplish a goal;
- concept pages explain why the methods behave as they do; and
- reference pages state exact contracts and API behavior.

This separation follows the [Diátaxis documentation framework](https://diataxis.fr/start-here/) and the navigation used by projects such as [NumPy](https://numpy.org/doc/stable/), [pandas](https://pandas.pydata.org/docs/), and [GeoPandas](https://geopandas.org/en/stable/docs.html).

Link mentions of public Python objects to their generated API documentation with MyST/Sphinx roles:

```markdown
{py:func}`athenspop.scheduling.engine.schedule_once`
```

Use an equation, figure, diagram, or table only when it makes a relationship easier to understand than prose. Every display should have a clear purpose, caption, and accessible alternative text where the format supports it.

Build documentation with [Sphinx](https://www.sphinx-doc.org/) and [MyST Parser](https://myst-parser.readthedocs.io/):

```console
uv run sphinx-build -nW --keep-going -b html docs docs/_build/html
```

The `-n` option reports unresolved cross-references, and `-W` treats warnings as errors.

## Prepare a reviewable change

Before submitting:

- keep the change focused and explain the user-visible result;
- update API documentation and examples when public behavior changes;
- describe any change to data, timing, or methodological interpretation;
- run the full local check; and
- leave generated environments, caches, and documentation builds out of the commit.

Software contributions are released under the repository's [MIT License](LICENSE). The processed Athens tables retain their separate [CC BY 4.0 International license](data/athens/LICENSE).
