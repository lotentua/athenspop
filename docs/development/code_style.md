# Code Style

The project targets Python 3.12 or later and does not preserve shims for older Python versions, deleted modules, or old data formats.

Use `uv` for environment and command execution.
Ruff is both the linter and formatter. Its configuration follows the referenced `aef-embeddings` contract: Ruff defaults with `E`, `W`, `F`, `I`, and `UP` selected.
ty runs with its defaults and checks source, tests, and maintained examples together.
pytest checks behavior.
Sphinx builds the documentation.

Use the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) where it applies. Use [PEP 8](https://peps.python.org/pep-0008/) for uncovered Python conventions and [Refactoring.Guru](https://refactoring.guru/refactoring) only as supplementary refactoring guidance. Existing project contracts and evidence take precedence over generic pattern advice.

Public modules, classes, dataclasses, functions, and methods use Google-style docstrings rendered by Sphinx Napoleon.
Public dataclasses document every field in an `Attributes:` section.
Public callables document arguments, return values, raised exceptions, units, randomness, array shapes, and caveats when those details affect correct use.
Structured docstring entries use the alternate Google-style layout where the item name appears on one line and the description starts on the next indented line.

Private helpers get short docstrings when they encode non-obvious policy, such as validation staging, feasible-window refinement, callable travel-time checks, episode partitioning, optimal-matching batching, or clustering layout conversion.
Trivial helpers should usually be inlined instead of documented.

Ruff's default formatter width is authoritative for Python. Reflow docstrings, comments, and user-facing strings cleanly when `E501` identifies a real overlong Python line; do not add blanket suppressions.
