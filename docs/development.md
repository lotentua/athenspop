# Development

Contributions should preserve the package's explicit stage boundaries: dataframe validation, trusted model objects, scheduling, episode and sequence construction, dissimilarity, clustering, and optional visualization. A change belongs at the earliest shared boundary that can enforce its contract without duplicating checks downstream.

## Set up the repository

The repository uses `uv` to resolve its development environment:

```console
uv sync --locked --all-groups
```

Run the complete local verification set before submitting a change:

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

## Python style and typing

Python code follows the Google Python Style Guide where its rules apply. Ruff enforces formatting, imports, docstrings, naming, annotations, complexity, and selected defect patterns. `ty` checks source, tests, examples, and the Sphinx configuration.

Use module imports and qualify domain symbols. Every module, class, function, method, callback, type alias, and constant needs a useful prose docstring or documentation comment. Public docstrings use Google sections such as `Args`, `Returns`, `Raises`, `Attributes`, and `Notes` only when the corresponding information exists.

Keep runtime validation at untrusted public boundaries. Private functions should rely on the normalized model contract instead of repeating dataframe checks.

## Tests

Tests assert observable behavior and public contracts. Prefer small dataframes and direct model outcomes over tests coupled to private helper structure. Cover both the successful result and the material failure at each public trust boundary.

Regression tests should name the behavior that would fail without the correction. Tests must remain deterministic: supply random seeds, compare stable tabular values, and close Matplotlib figures. The configured coverage threshold is a release guard, not a substitute for checking the important branches.

## Documentation and examples

Documentation is standalone product guidance. Keep methodological assumptions next to the operation they govern and distinguish measured results from exploratory choices. Ordinary Markdown prose is not hard-wrapped. Code examples use the same module-import and typing conventions as source code.

Executable files under `examples/` contain reusable functions and a small script entry point. Workflow pages explain those functions as notebook-like cells, show material output, and state the limits of interpretation. Plotting functions return figures and defer dimensions, typography, lines, and default colors to the active Matplotlib stylesheet.

## Change discipline

Add a dependency or abstraction only when a demonstrated requirement cannot be met by the standard library, the platform, or an installed dependency. Remove dead paths and define each public behavior once in the module that owns it. Update the tests, API documentation, workflow narrative, and data contract when a public behavior changes.
