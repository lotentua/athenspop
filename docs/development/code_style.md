# Code Style

The project targets Python 3.12 or later and does not preserve shims for older Python versions, deleted modules, or old data formats.

Use `uv` for environment and command execution. Ruff is both the linter and formatter. ty checks the typed surface. pytest checks behavior. Sphinx builds the documentation.

Public modules, classes, dataclasses, functions, and methods use Google-style docstrings rendered by Sphinx Napoleon. Public dataclasses document every field in an `Attributes:` section. Public callables document arguments, return values, raised exceptions, units, randomness, array shapes, and caveats when those details affect correct use.

Private helpers get short docstrings when they encode non-obvious policy, such as validation staging, feasible-window refinement, callable travel-time checks, episode partitioning, optimal-matching batching, or clustering layout conversion. Trivial helpers should usually be inlined instead of documented.

Do not hard-wrap prose in documentation, docstrings, comments, or user-facing strings. Let tools or renderers wrap text visually.
