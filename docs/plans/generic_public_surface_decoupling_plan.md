# Generic Public Surface Decoupling And Python 3.12 Modernization Plan

This is an internal execution plan for decoupling `athenspop` from paper-specific and first-release-specific framing while preserving the example workflow as a reproducible example under `examples/athens`.

## Review Findings

- High: [README.md](../../README.md), [docs/index.md](../index.md), `docs/user_guide/*`, `docs/design/*`, and `docs/plans/long_canonical_rewrite_plan.md` still present the package through first-release and paper-reproduction language, so a reader can reasonably infer that the package identity is the paper workflow instead of a generic long-form travel-diary library; the smallest correction is to make the public package home, quickstart, concepts, API guide, and design notes generic, then move or exclude all paper and first-release language from public documentation except under `examples/athens`.
- High: Athens-specific tests are currently mixed into the generic test suite as `tests/test_athens_*.py`, while additional paper-specific test modules already live under `examples/athens`; this makes the generic package test boundary look method- and dataset-specific, so the smallest correction is to move all paper-specific tests into `examples/athens/tests` and keep top-level `tests/` only for generic library contracts.
- High: [examples/athens_reproduction_smoke.py](../../examples/athens_reproduction_smoke.py) is a paper-specific executable module at the repository root of `examples`, so paper machinery leaks outside the example namespace; the smallest correction is to move it to `examples/athens/smoke.py` or `examples/athens/reproduction_smoke.py` and update imports/tests accordingly.
- High: Public classes and functions in `src/athenspop` have useful names but thin docstrings, and many public dataclasses do not document every attribute with Google-style `Attributes:` sections; this violates the intended public API standard and makes the library hard for non-expert maintainers to learn from the generated API reference.
- Medium: Private helpers in validation, scheduling, sequence, and clustering encode real algorithmic policy but are mostly undocumented; this is not a call for noisy comments on trivial lines, but nontrivial private helpers need short contract docstrings because future maintainers will otherwise have to reverse-engineer validation cascades, feasible-window refinement, optimal-matching batching, and clustering layout assumptions.
- Medium: [pyproject.toml](../../pyproject.toml) declares `requires-python = ">=3.12"` but has no Ruff configuration, while source modules still use older `TypeAlias` declarations instead of the Python 3.12 `type` statement; the smallest correction is to configure Ruff in `pyproject.toml`, set `target-version = "py312"`, use `select = ["ALL"]` with documented narrow ignores, and replace compatibility-era typing idioms where Python 3.12 has a clearer native form.
- Medium: The current Sphinx docs use Napoleon and PyData Sphinx Theme, which is a sound simple stack for this repository, but the public information architecture still mixes user guide, paper contract, release evidence, profiling notes, and implementation planning in one public toctree; the smallest correction is to keep Sphinx and restructure the docs rather than switching tools.
- Medium: Current public prose still uses `canonical` as a partly historical rewrite term; keep `canonical` only when it means the normalized internal data contract, and use simpler public terms such as "validated tables", "survey dataset", "diary", "schedule", "sequence", and "cluster" where possible.
- Low: The user wrote `athenspoop` once, but the actual package is `athenspop`; this plan assumes the package name remains `athenspop` unless a separate rename task is explicitly requested.

## External Documentation Evidence

- PAM presents itself first as a generic population activity sequence modelling library, then separates installation, reading data, activity plans, examples, and API reference; use that structure as inspiration for public positioning and navigation, not as a dependency or API template: https://arup-group.github.io/pam/latest/.
- Pydantic concept docs separate conceptual explanations, field/model semantics, API links, and examples; copy that documentation pattern for validation, table schemas, schedules, and model objects, but do not add Pydantic as a runtime dependency unless a future boundary-validation need clearly justifies it: https://pydantic.dev/docs/validation/latest/concepts/models/ and https://pydantic.dev/docs/validation/latest/concepts/fields/.
- ActivitySim documents core components, table/data-management assumptions, probabilistic and logit scheduling models, and how the system works separately from API details; use its mathematical and dataflow separation as inspiration while keeping `athenspop` much smaller and friendlier for students: https://activitysim.github.io/activitysim/v1.0.4/core.html, https://activitysim.github.io/activitysim/v1.0.4/models.html, and https://activitysim.github.io/activitysim/v1.0.4/howitworks.html.
- Python 3.12 typing documentation defines the `type` statement for type aliases and explicitly notes that annotations are not runtime enforcement; the code should use modern type aliases and keep runtime validation only at real external-data boundaries: https://docs.python.org/3.12/library/typing.html.
- Ruff documents one tool covering linting, import sorting, pydocstyle, pyupgrade, formatting-adjacent rules, and many Flake8 plugins; use Ruff as the single lint/format authority in `pyproject.toml`: https://docs.astral.sh/ruff/linter/ and https://docs.astral.sh/ruff/settings/.
- Google Python style requires docstrings for public modules, functions, methods, and classes, and PEP 257 gives the baseline Python docstring convention; use Google sections through Sphinx Napoleon while preserving this project's no-hard-wrapped-prose rule: https://google.github.io/styleguide/pyguide.html and https://peps.python.org/pep-0257/.

## Target Public Identity

- `athenspop` is a small Python library for validating long-form household travel-survey tables, constructing complete diary objects, scheduling feasible trips, generating activity/travel sequences, computing sequence dissimilarities, and clustering daily mobility patterns.
- Public documentation must not describe the package as a paper reproduction, a first release, a rewrite, a migration from wide form, or a final job handoff artifact.
- Public documentation may include a generic examples section, but it must not name or describe the paper reproduction; only `examples/athens`, internal plans, and retained internal history excluded from Sphinx may name the paper workflow.
- Public API names should remain generic: `validation`, `model`, `io`, `scheduling`, `generation`, `sequence`, `clustering`, and `visualization`.
- Internal planning files may mention the paper, first-release constraints, and migration history, but they must not be included in the public Sphinx toctree, generated Sphinx navigation/search output, or package README.

## Simplification Decisions

- Keep Sphinx, PyData Sphinx Theme, MyST Parser, `sphinx.ext.autodoc`, `sphinx.ext.napoleon`, and `sphinx.ext.viewcode`; changing to MkDocs or another docs stack adds churn without solving the actual coupling problem.
- Keep the library dependency set small: NumPy, pandas, SciPy, and Matplotlib are justified by dataframe boundaries, numerical sequence distances, hierarchical clustering, and the shared built-in cut-dendrogram visualization requirement; Pydantic, ActivitySim, PAM, Sequenzo, and MATSim adapters stay out of runtime dependencies unless a later measured need justifies them.
- Do not preserve backward compatibility with deleted `core`, `long`, `models`, or `utils` modules, old notebooks, wide-form APIs, or Python versions older than 3.12.
- Do not add a CLI while decoupling; examples can remain executable modules or notebooks, and the public package should stay an importable library.
- Do not create a large framework for example registration, plugin adapters, or paper-specific method selection; example-specific helpers stay as plain modules under `examples/athens`.
- Do not move generic tests into examples merely because they were discovered through the paper workflow; keep tests generic when their assertion describes reusable behavior.
- Do not hide methodological caveats; make generic caveats generic, and put paper-specific caveats inside the Athens example docs.

## Destination Layout

```text
README.md
docs/
  index.md
  concepts/
    data_model.md
    validation.md
    scheduling.md
    sequences.md
    clustering.md
    visualization.md
  user_guide/
    quickstart.md
    input_tables.md
    validation_report.md
    scheduling_and_generation.md
    sequence_clustering.md
  api/
    index.md
    validation.md
    model.md
    io.md
    scheduling.md
    generation.md
    sequence.md
    clustering.md
    visualization.md
  development/
    contributing.md
    code_style.md
    testing.md
  plans/
    generic_public_surface_decoupling_plan.md  # internal, retained in repo, excluded from Sphinx with source-relative patterns
examples/
  athens/
    README.md
    docs/
    tests/
    smoke.py
    reproduce.py
src/
  athenspop/
tests/
  test_canonical_dataframes.py
  test_distance_clustering.py
  test_io_boundary.py
  test_scheduling_generation.py
  test_sequence.py
```

## Public Documentation Plan

- Rewrite `README.md` so the first screen states the generic library purpose, shows a minimal dataframe validation and scheduling example, points to documentation, and does not mention the paper, first release, rewrite status, or old implementation history.
- Rewrite `docs/index.md` around the generic package identity, a short conceptual overview, and navigation to quickstart, concepts, user guide, API reference, and development notes.
- Remove `docs/design/*paper*`, `docs/design/*release*`, `docs/design/profiling_notes.md`, `docs/plans/long_canonical_rewrite_plan.md`, and any paper walkthrough page from the public Sphinx toctree.
- Move paper method contract, artifact manifest, paper walkthrough, source hashes, and reproduction instructions to `examples/athens/docs` or `examples/athens/README.md`.
- Keep a generic `docs/concepts/scheduling.md` that mentions uniform feasible-window scheduling, repeatable random seeds, and future probability/logit schedulers as generic concepts without naming the paper or first release.
- Keep a generic `docs/concepts/sequences.md` that explains episodes, fixed-width binning, state sequences, substitution costs, indel costs, and optimal matching without tying the method to any one publication.
- Keep a generic `docs/concepts/clustering.md` that explains pairwise dissimilarity matrices, average linkage, cluster labels, dendrogram coordinates, object-returning visualization, and profiling expectations without making the slow paper dendrogram workload the package identity.
- Keep a generic `docs/concepts/validation.md` that explains boundary validation as "collect all independent table, join, and domain errors, then build trusted model objects" and uses Pydantic-style explanation of validated output without introducing Pydantic as a dependency.
- Add `docs/development/code_style.md` explaining Python 3.12-only code, `src/` layout, no compatibility shims, Ruff/ty/pytest/Sphinx commands, Google-style docstrings, and the no-hard-wrapped-prose rule for this repository.
- Configure `docs/conf.py` with source-relative `exclude_patterns` such as `_build`, `plans/**`, generated example output patterns, and any retained internal-only notes; because Sphinx is run with `docs` as the source directory, repository-root patterns such as `docs/plans` are not sufficient.
- Add a Sphinx build gate that fails on public docs warnings and a text gate that fails if `README.md`, `docs/index.md`, `docs/concepts`, `docs/user_guide`, `docs/api`, `docs/development`, `src/athenspop`, or top-level `tests` mention the paper, `CSuM`, or first-release framing.
- Add a post-build public-output gate that searches `docs/_build/html` and the Sphinx search index for forbidden internal or example-specific page names such as `athens_method`, `athens_output`, `release_readiness`, `long_canonical_rewrite_plan`, `generic_public_surface_decoupling_plan`, and `profiling_notes`.

## Source Decoupling Plan

- Audit `src/athenspop` with `rg -n "CSuM|paper|v1|release|legacy|wide|rewrite|canonical paper|first complete"` and remove or rename any non-generic language from module docstrings, error messages, warnings, names, and examples.
- Keep `canonical` only for the validated normalized table/model contract, not as a release label.
- Make every public module docstring describe what the module provides, when to use it, and what assumptions it makes after validation.
- Make every public dataclass include a Google-style `Attributes:` section for each field, including `TimeWindow`, `Trip`, `PersonMetadata`, `HouseholdMetadata`, `Diary`, `SurveyDataset`, `SchedulingConfig`, `SchedulingIssue`, `SchedulingDiagnostics`, `ScheduledSurveyDataset`, `Episode`, `DendrogramLayout`, `CutDendrogramNode`, `TemporalDendrogramPlotStyle`, `ValidationIssue`, `ValidationReport`, `ValidationReportBuilder`, `NormalizedTables`, and `ValidationResult`.
- Make every public function and method use Google-style sections as applicable: `Args:`, `Returns:`, `Raises:`, `Examples:`, `Notes:`, `Warnings:`, and `See Also:`.
- Document public validation semantics carefully: a valid `ValidationResult` means the output dataframes/model objects are trusted by internal code; annotations describe contracts but do not enforce runtime types; validation errors and warnings are distinct.
- Add a focused public-docstring audit step that enumerates public modules, public classes, public dataclasses, public dataclass fields, public functions, and public methods, then verifies that generated API docs or source docstrings include the expected Google-style sections and field names; keep this as a checklist or small AST helper, not a broad custom documentation framework.
- Add short private docstrings only where the helper carries non-obvious policy, such as validation cascade stopping, timing-pattern detection, trip-chain ordering, feasible departure refinement, callable travel-time probing, return-home imputation hooks, episode partition verification, optimal-matching batching, and dendrogram coordinate conversion.
- Inline or rename private helpers whose only purpose is a one-line alias and whose required docstring would add more noise than clarity.
- Keep example-specific functions and names under `examples/athens`; if an example helper is copied, semantically duplicated, or clearly low-effort and realistic for future examples, first extract a neutral minimal function with tests in `src/athenspop`, then let the example compose it.
- Keep file writers, survey-code mappings, purpose/mode vocabularies, and publication artifact manifests in examples even when they use source primitives.

## Python 3.12 And Typing Plan

- Keep `requires-python = ">=3.12"` in `pyproject.toml`, pin `.python-version` to an installed Python 3.12 interpreter when feasible, and always run a minimum-supported-Python gate under Python 3.12 even if local development also uses a newer interpreter.
- Replace `from typing import TypeAlias` and `Name: TypeAlias = ...` with Python 3.12 `type Name = ...` statements in maintained source and tests where type aliases remain useful.
- Prefer standard-library Python 3.12 typing constructs such as `Self`, `Protocol`, `TypedDict`, `Required`, `NotRequired`, `Unpack`, `ParamSpec`, `override`, `Final`, `ClassVar`, `Never`, and `NoReturn` when they make a contract clearer.
- Avoid `typing_extensions` unless a needed typing feature is not available in Python 3.12 and its benefit is material.
- Fully specialize every generic annotation, including nested collections and NumPy arrays, and keep NumPy array annotations in direct `np.ndarray[Shape, np.dtype[Scalar]]` form.
- Remove `Any` and `object` annotations from maintained code; where external APIs are dynamic, validate and narrow values into precise local unions, dataclasses, protocols, or typed dictionaries at the boundary, and stop for a design decision rather than inventing fictitious precision if a truthful precise contract cannot be established.
- Keep `dtype=object` in pandas fixture construction only if it is necessary to model mixed external input values, and do not confuse that runtime pandas dtype with an `object` type annotation.
- Reorder unions according to the harness convention and prefer precise local aliases when a repeated union has real semantic meaning.
- Keep dataclasses `frozen=True` and `slots=True` where instances are trusted immutable value objects; use mutable classes only for builders or caches and document the mutation contract.
- Remove compatibility imports, version branches, shims, old aliases, and deprecated names from maintained package code instead of warning and forwarding.

## Tooling Plan

- Add a single tool configuration surface in `pyproject.toml` with `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.lint.pydocstyle]`, `[tool.ruff.format]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]` if coverage is kept, and `[tool.ty]` if ty supports the needed project configuration.
- Set Ruff `target-version = "py312"`, `src = ["src", "tests", "examples"]`, and `line-length` high enough or ignored where necessary to respect the no-hard-wrapped-prose rule.
- Set Ruff lint `select = ["ALL"]`, then add only narrow documented ignores for rules that conflict with the harness, Sphinx/Napoleon docstring rendering, pytest idioms, scientific code clarity, or no-hard-wrapped-prose.
- Set `lint.pydocstyle.convention = "google"` so Ruff and Sphinx agree on docstring style.
- Add per-file ignores only for tests, examples, and Sphinx configuration when a rule is demonstrably worse there; do not globally weaken docstring, typing, import, or bugbear checks merely to reduce the first lint diff.
- Keep the repair loop as `uv run ruff check . --fix`, `uv run ruff format .`, `uv run ruff check . --fix`, `uv run ty check`, `uv run pytest -q tests`, and `uv run sphinx-build -W -b html docs docs/_build/html`; final acceptance must use non-mutating checks.
- Add a small script or documented `rg` command for public-surface leakage checks rather than building a custom linter unless repeated failures justify automation.

## Test Decoupling Plan

- Keep top-level `tests/` focused on generic library contracts: input-table validation, optional persons/households, timing patterns, scheduling, generation, IO boundaries, episodes, sequence discretization, optimal matching, clustering, object-returning visualization, portability across mentioned survey families after local mapping, and public imports.
- Move `tests/test_athens_demographics.py`, `tests/test_athens_imputation.py`, `tests/test_athens_input_conversion.py`, `tests/test_athens_reproduction_artifacts.py`, `tests/test_athens_reproduction_smoke_example.py`, and `tests/test_athens_visualization.py` into `examples/athens/tests`.
- Move or merge `examples/athens/test_method.py` and `examples/athens/test_travel_time.py` into the same `examples/athens/tests` package so all example tests have one home.
- Rename imports from `examples.athens_reproduction_smoke` to `examples.athens.smoke` after moving the smoke module.
- Keep Athens example tests runnable with `uv run pytest -q examples/athens/tests` but separate from the generic package quality gate when a maintainer wants to test only the library.
- Keep the full validation gate as `uv run pytest -q tests examples/athens/tests` while the example remains part of the repository.
- Ensure generic tests do not import `examples.athens` and example tests may import `athenspop`, never the other way around.
- Add a dependency-direction check with `rg -n "examples\\.paper|athens_reproduction|CSuM" src tests README.md docs/index.md docs/concepts docs/user_guide docs/api docs/development` and treat any hit as a failure unless the searched path is explicitly an internal or example path.

## Example Decoupling Plan

- Make `examples/athens/README.md` the only public-facing place that names and explains the paper reproduction.
- Keep source verification, paper-specific wide-to-long conversion, paper travel-time resources, paper imputation, paper transition-cost construction, artifact manifests, and visualizations under `examples/athens`.
- Move paper-specific documentation pages from `docs/user_guide` and `docs/design` into `examples/athens/docs`, then adjust links relative to the example folder.
- Keep the example command as a direct module invocation such as `uv run python -m examples.athens.reproduce`; do not turn it into a package CLI.
- Keep generated artifacts under `examples/athens/output` ignored by Git.
- Keep paper source files and hashes documented only in the example docs, not in package docs.
- If public docs include a generic examples page, link only to generic examples or the examples directory without naming, describing, or elevating the paper workflow.

## Implementation Phases

### Phase 0: Baseline And Isolation

- Confirm the branch/worktree is task-isolated and record `git status --short --branch`.
- Record current leakage hits with `rg -n "CSuM|paper|Athens|v1|V1|release|legacy|rewrite" README.md docs src tests examples --glob "!examples/athens/data/**"` before editing.
- Record current public API and test surfaces with `rg --files src tests docs examples`.
- Do not revert unrelated existing changes; this branch is already in the middle of a rewrite and those changes are assumed intentional.

### Phase 1: Public Identity Rewrite

- Rewrite `README.md` to define `athenspop` generically, show a minimal dataframe-based quickstart, list core modules, and link to docs without first-release or paper language.
- Rewrite `docs/index.md` to remove paper and first-release language, remove the public design-note toctree, and introduce the new public docs structure.
- Create or revise concept and user-guide pages so each page explains one generic concept or workflow in plain language before API details.
- Keep the package name, author metadata, and library purpose stable unless a separate rename task is created.

### Phase 2: Internal And Example Documentation Relocation

- Move `docs/user_guide/athens_reproduction.md`, `docs/user_guide/athens_walkthrough.md`, `docs/design/athens_method_contract.md`, and `docs/design/athens_output_manifest.md` into `examples/athens/docs`.
- Move first-release evidence notes such as `docs/design/release_readiness.md`, `docs/design/profiling_notes.md`, and `docs/plans/long_canonical_rewrite_plan.md` out of the public Sphinx toctree; keep them as internal retained history excluded from Sphinx if still useful.
- Convert `docs/design/scheduling_method_note.md`, `docs/design/activitysim_adaptation_note.md`, and `docs/design/sequenzo_decision_gate.md` into generic concept or development notes by removing paper and first-release authority language, or move them to internal/example docs if they remain paper-specific.
- Update `docs/conf.py` `exclude_patterns` with source-relative patterns such as `plans/**` so internal plans and generated example outputs never appear in public builds by accident.

### Phase 3: Test And Example Boundary Cleanup

- Move paper tests into `examples/athens/tests` and update imports.
- Move `examples/athens_reproduction_smoke.py` into `examples/athens/smoke.py` and update the reproduction module and tests.
- Keep generic tests in top-level `tests/` and rewrite any generic test names or messages that still mention paper framing.
- Add a simple dependency-direction check to the validation notes or project scripts only if manual `rg` proves easy to forget.

### Phase 4: Source Docstring And API Contract Rewrite

- Rewrite module docstrings for `athenspop.validation`, `athenspop.model`, `athenspop.io`, `athenspop.scheduling`, `athenspop.generation`, `athenspop.sequence`, and `athenspop.clustering`.
- Add full Google-style public docstrings to validation report and schema APIs first because they define the trusted boundary.
- Add full Google-style public docstrings to model dataclasses next because they are the internal contract consumed by scheduling and sequence code.
- Add full Google-style public docstrings to scheduling/generation APIs next because stochastic behavior, seed handling, infeasibility diagnostics, and travel-time callables are high-confusion areas.
- Add full Google-style public docstrings to sequence, clustering, and visualization APIs last, including notes on seconds, binning, cost matrices, matrix shapes, SciPy linkage compatibility, returned Matplotlib figures, and file-writing non-goals.
- Run the public-docstring audit checklist against the listed public dataclasses and the public functions/methods in each public module before treating Sphinx as documentation-complete.
- Add short private helper docstrings only where they preserve non-obvious policy; inline trivial helpers instead of documenting noise.

### Phase 5: Python 3.12 Modernization

- Replace `TypeAlias` declarations with Python 3.12 `type` statements throughout maintained source.
- Audit typing imports and remove compatibility-era imports that are no longer needed.
- Replace broad or under-specialized annotations with precise contracts, especially pandas metadata values, travel-time callables, NumPy matrices, and report serialization structures.
- Run targeted runtime probes only where an upstream pandas, NumPy, SciPy, or Sphinx API type is unclear and the docs/source do not provide a precise stable contract.
- Keep runtime validation at dataframe/file boundaries and avoid defensive checks inside methods that receive trusted model objects.

### Phase 6: Ruff, Ty, Pytest, And Sphinx Gate Hardening

- Add Ruff configuration with `select = ["ALL"]`, `target-version = "py312"`, Google pydocstyle convention, import sorting, formatter settings, and narrow documented ignores.
- Add or update pytest configuration so bare `uv run pytest -q` collects the generic library suite under `tests` only; the full repository gate must explicitly pass both `tests` and `examples/athens/tests`.
- Add ty configuration only as needed to keep the typed surface checked without duplicating Ruff settings.
- Run the full quality loop and fix issues in coherent slices rather than broad mechanical churn.

### Phase 7: Final Leakage And Simplification Review

- Run public-surface leakage search and confirm no paper or first-release language remains in `README.md`, `src/athenspop`, top-level `tests`, or public docs.
- Confirm all paper language is isolated to `examples/athens`, internal plans, or retained historical notes excluded from Sphinx.
- Review every new or retained abstraction and remove any that exists only to serve the Athens example or imagined future adapters.
- Verify that docs, code, and tests describe the same generic library contracts.

## Acceptance Gates

- `rg -n -i "CSuM|paper|v1|first[-_ ]release|release[-_ ]readiness|release target|rewrite|legacy|publication|manuscript|reproduction" README.md src tests docs/index.md docs/concepts docs/user_guide docs/api docs/development` returns no hits after any false-positive vocabulary is deliberately removed or the searched path list is narrowed; internal paths such as `docs/plans/**` and example paths such as `examples/athens/**` are not searched by this public-surface gate.
- `rg -n "examples\\.paper|athens_reproduction|CSuM" src tests README.md docs/index.md docs/concepts docs/user_guide docs/api docs/development` returns no hits.
- `rg -n "TypeAlias|typing_extensions|sys\\.version|python_version|>=3\\.11|>=3\\.10|backward|compat" src tests pyproject.toml README.md docs/index.md docs/concepts docs/user_guide docs/api docs/development` returns no maintained-code or public-doc compatibility hits.
- `uv run --python 3.12 python -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version"` passes before the minimum-supported-Python quality gate.
- The minimum-supported-Python quality gate passes under Python 3.12: `uv run --python 3.12 ruff check .`, `uv run --python 3.12 ruff format --check .`, `uv run --python 3.12 ty check`, `uv run --python 3.12 pytest -q tests`, `uv run --python 3.12 pytest -q examples/athens/tests`, and `uv run --python 3.12 sphinx-build -W -b html docs docs/_build/html`.
- `uv run ruff check .` completes without remaining lint errors.
- `uv run ruff format --check .` passes.
- `uv run ty check` passes with no unreviewed findings; any unavoidable tool limitation must be recorded in a line-specific allowlist with the exact diagnostic, rationale, and removal condition.
- `uv run pytest -q tests` passes as the generic library gate.
- `uv run pytest -q examples/athens/tests` passes as the example gate.
- `uv run sphinx-build -W -b html docs docs/_build/html` passes and the built navigation contains no internal plan, release-readiness, or paper-method pages.
- The public-docstring audit confirms every public dataclass listed in the Source Decoupling Plan has an `Attributes:` entry for every field, every public callable has applicable Google-style sections for arguments, returns, raises, units, randomness, shapes, and caveats, and every exception is documented in a short reviewed allowlist.
- A post-build search of `docs/_build/html` and `docs/_build/html/searchindex.js` finds no forbidden internal or paper-specific page names such as `athens_method`, `athens_output`, `release_readiness`, `long_canonical_rewrite_plan`, `generic_public_surface_decoupling_plan`, or `profiling_notes`.
- `uv run python -m examples.athens.smoke` runs from repository-local fixtures without external paper source files and verifies that the example import boundary still works.
- `uv run python -m examples.athens.reproduce` still runs when the full example source files are present; if source files are not present, the command must fail with a clear documented missing-source message, and `examples/athens/README.md` must document the expected source layout, hashes, and acquisition/preparation steps.

## Risks And Controls

- Risk: Removing public paper language may accidentally erase useful methodological explanation; control this by rewriting method explanation generically and moving only dataset/publication-specific claims to the example.
- Risk: Moving tests can hide regressions if the default test command only runs `tests`; control this by documenting both the generic gate and the full repository gate.
- Risk: Ruff `select = ["ALL"]` can create a noisy first pass; control this by applying fixes module by module and documenting each ignore instead of suppressing categories globally.
- Risk: Full Google-style docstrings can become repetitive; control this by documenting public contracts fully, documenting private policy helpers briefly, and inlining trivial private helpers.
- Risk: Python 3.12 modernization can create type churn without behavioral value; control this by changing syntax and contracts only where they improve clarity or satisfy the harness, and preserving behavioral tests as the authority.

## Open Decisions

- Resolved: Keep `docs/plans` in the repository for internal continuity, exclude it from Sphinx with source-relative `plans/**`, and verify the generated HTML/search output does not expose internal plans.
- Resolved: Public README and public docs must not mention the Athens example; only `examples/athens`, internal plans, and retained internal history excluded from Sphinx may name it.
- Resolved: The package metadata remains `>=3.12`; `.python-version` should pin Python 3.12 when feasible, and the acceptance gates must run under Python 3.12 regardless of any newer local development interpreter.
- Resolved: Bare `uv run pytest -q` should collect the generic `tests` suite only through pytest configuration; the full repository gate explicitly runs `uv run pytest -q tests examples/athens/tests`.
