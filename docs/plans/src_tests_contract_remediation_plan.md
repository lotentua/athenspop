# Source, Test, and Example Contract Remediation Plan

## Purpose

This plan covers the minimum controlled work needed to address every currently known source, test, example, tooling, and packaging issue in `src/`, `tests/`, and `examples/`, regardless of severity.

The goal is not to add new product surface.

The goal is to make the existing generic library surface and maintained examples smaller, clearer, contract-tested, style-compliant, and harder to accidentally regress.

## Current Baseline

The repository is on branch `integrate-generic-pivot-20260619`.

The direct baseline before this plan was clean according to `git status --short --branch`.

The last full configured checks passed with the current configuration: `uv run rtk pytest -q tests examples/athens/tests`, `uv run rtk ruff check src tests examples`, and `uv run rtk ty check src tests examples`.

Those checks are not sufficient because the current Ruff configuration suppresses structural line length, complexity in two source functions, and test magic numbers.

The stricter non-line-length isolated scan over `src` and `tests` found 35 issues: 2 `C901`, 1 `PLR0912`, and 32 `PLR2004`.

The command for that count was `ruff check src tests --isolated --select C901,PLR0912,PLR0915,PLR2004,SIM,ARG`.

The same stricter non-line-length isolated scan over `src`, `tests`, and `examples` found 99 issues: 2 `C901`, 1 `PLR0912`, 91 `PLR2004`, 4 `ARG001`, and 1 `SIM101`.

The command for that count was `ruff check src tests examples --isolated --select C901,PLR0912,PLR0915,PLR2004,SIM,ARG`.

Line-length findings must be counted with a prose-aware structural-line audit rather than a blunt isolated `E501` run, because the harness requires prose and docstrings not to be hard-wrapped.

The import graph shows that `athenspop.__init__` imports visualization, which imports Matplotlib through the visualization module.

The import graph also shows that `athenspop.model.survey` imports validation implementation details from `athenspop.validation.schema`.

The example import graph shows that maintained example modules and tests also import validation implementation details from `athenspop.validation.schema`.

The duplicate-body scan found identical `_materialize_sequences` implementations in clustering and visualization.

The duplicate-body scan found identical `_constant_travel_time` test helpers in two test modules.

The duplicate-name scan found repeated `_required_child`, `_optional_int`, `has_errors`, `raise_if_invalid`, and `travel_time_function` definitions that need either consolidation or explicit justification.

The cross-surface semantic duplicate scan found example-local `_issue` and `_diary_id` helpers that are operationally similar to scheduler internals, duplicated `_states` helpers across Athens method and visualization code, repeated `TimingPattern` imports from validation internals, and duplicate matrix/callable typing aliases across source, tests, and examples.

The example semantic duplicate scan found Athens purpose and mode vocabularies split across input conversion, sequence reduction, and travel-time resolution.

The time scan found time-domain constants split across `athenspop.io.clock`, `athenspop.sequence.episodes`, `athenspop.scheduling.engine`, and `athenspop.validation.schema`.

The time scan found duplicate `1800` defaults in scheduling and validation, duplicate `3600` constants in IO and sequence code, duplicate `86400` values in IO and scheduling, duplicated default `"04:00"` time-origin clock values in IO, and many repeated test timing literals.

The structural line scan found over-80-character structural Python code lines in every source module except small package initializers and in every test module.

The examples directory contains generated Python bytecode caches under `examples/**/__pycache__`, and similar generated caches exist under `src` and `tests`.

## Source Import Graph

The current source import adjacency is:

```text
athenspop -> athenspop.clustering, athenspop.generation, athenspop.io, athenspop.model, athenspop.scheduling, athenspop.validation, athenspop.visualization
athenspop.clustering -> athenspop.clustering.hierarchical
athenspop.clustering.hierarchical -> -
athenspop.generation -> athenspop.generation.schedules
athenspop.generation.schedules -> athenspop.model, athenspop.scheduling
athenspop.io -> athenspop.io.clock
athenspop.io.clock -> -
athenspop.model -> athenspop.model.survey
athenspop.model.survey -> athenspop.validation, athenspop.validation.schema
athenspop.scheduling -> athenspop.scheduling.engine
athenspop.scheduling.engine -> athenspop.model
athenspop.sequence -> athenspop.sequence.distance, athenspop.sequence.episodes
athenspop.sequence.distance -> -
athenspop.sequence.episodes -> athenspop.model
athenspop.validation -> athenspop.validation.report, athenspop.validation.schema
athenspop.validation.report -> -
athenspop.validation.schema -> athenspop.validation.report
athenspop.visualization -> athenspop.visualization.dendrogram
athenspop.visualization.dendrogram -> athenspop.clustering
```

The desired dependency direction is data model first, validation at the boundary, scheduling and sequence analysis on validated models, clustering on generic sequences or dissimilarities, and visualization as an optional leaf dependency.

## Success Criteria

All accepted issues from the previous review and the scans in this plan have either been fixed or documented with a narrow project-specific reason.

Every public contract has at least one durable test that exercises valid input and at least one durable test that exercises the most important invalid input.

Every boundary validator reports one primary row-level or chain-level error without creating noisy cascades for the same bad row or chain.

The source package contains only generic travel-diary validation, scheduling, imputation or generation support, sequence analysis, clustering, and low-effort generic visualization primitives.

Paper-specific, Athens-specific, and dataset-specific behavior lives outside the package, preferably in examples.

Maintained examples use the public or neutral package API and do not reach into validation, scheduling, clustering, or sequence implementation details unless the example explicitly demonstrates an advanced internal contract.

Maintained examples may perform file IO as teaching workflow code, but the package source must continue to accept and return Python objects rather than owning CSV, SVG, or notebook-file conversion.

The package can be imported without importing Matplotlib unless the visualization module is explicitly imported.

If visualization remains a mandatory installed dependency, the documentation and packaging metadata must say so plainly; otherwise Matplotlib should move to an optional visualization extra.

Configured tooling catches structural code lines that violate the selected code line limit while preserving the harness rule that prose is not hard-wrapped.

The source distribution excludes private notes, local caches, root paper artifacts, backup data, generated docs, and example-only raw data that is not meant to be packaged.

The import graph is checked by an automated architecture contract test or audit script.

Duplicate time constants, duplicated helper bodies, and duplicated generic column literals are either centralized or intentionally local with a documented reason.

Semantic duplicates across `src`, `tests`, and `examples` are either consolidated into a shared source primitive, moved to an example helper because they are genuinely example-specific, or documented as intentionally separate.

Generated bytecode caches and local generated artifacts are excluded from the maintained source, test, example, and packaging surface.

## Phase 1: Tooling, Style, and Packaging Contracts

Adopt a structural Python code line limit that follows PEP 8 and Google Python style expectations.

Set Ruff to enforce that code limit instead of using `line-length = 160` and globally ignoring `E501`.

Preserve the no-hard-wrapped-prose rule by using targeted ignores for prose-heavy docstrings, long URLs, and exact user-facing messages only where the style rule would force worse documentation.

Remove stale per-file complexity ignores for functions that can be simplified.

Keep only narrow per-file ignores that have a current explanation and a direct test or design reason.

Add a style contract test or local audit command that reports structural code line violations separately from prose, docstring, URL, and exact-message line length.

Add a packaging contract test that builds or inspects the sdist file list and fails if it contains `.claude/**`, `CSuM2026.pdf`, `CSuM2026.zip`, `docs/design/**`, `docs/plans/**`, generated docs, root Athens fixtures, or other private planning artifacts.

Add a repository hygiene audit that fails on generated bytecode caches such as `__pycache__` and `*.pyc` under `src`, `tests`, and `examples`.

Make maintained example tests part of the default configured test surface by adding `examples/athens/tests` to pytest collection or by defining one documented repository-local test wrapper as the authoritative test entry point.

Complete license and package metadata enough that a future maintainer can publish or archive the package without reverse-engineering provenance.

Update `pyproject.toml` comments so each remaining ignore explains the current project contract instead of an old temporary workaround.

## Phase 2: Boundary Validation Contracts

Normalize key columns in the copied boundary tables before duplicate-key checks, join checks, chain grouping, and model construction so values such as `1` and `"1"` cannot pass validation and then collapse inside the model.

Add duplicate-key tests for trips, persons, and households after key normalization.

Add cross-table key-normalization tests where `1` and `"1"` appear across trips, persons, and households.

Reject non-scalar reserved identity and movement-domain fields before key, join, timing, and model construction.

Add tests for non-scalar `household_id`, `person_id`, `trip_id`, `origin`, `destination`, `purpose`, and `mode` that expect one clear validation error rather than implementation crashes or trusted stringification.

Make `convert_clock_columns` return nullable integer columns for mixed converted and missing values, or make validation explicitly accept pandas nullable integer values and reject floats consistently.

Add tests proving clock conversion preserves integer-second semantics for all supported missing-value combinations.

Reject non-scalar clock cells at the IO boundary with a clear `ValueError` instead of leaking pandas ambiguous truth-value errors.

Validate `SchedulingConfig` at construction time.

Reject negative minimum activity duration, non-positive observation windows, and non-boolean flags.

Add tests proving invalid scheduling config values fail before scheduling starts.

Replace the validation-layer duplicate `DEFAULT_MIN_ACTIVITY_DURATION_SECONDS` warning threshold with a value provided by a generic policy object or with a validation warning that does not pretend to know scheduler configuration.

Add tests proving the scheduler and validator do not silently diverge on minimum dwell assumptions.

Make `schedule_once` return persons and households metadata that correspond to the scheduled diaries that remain after infeasible diaries are dropped, or document and test an explicit diagnostic-preserving alternative.

Add tests for infeasible-diary metadata filtering with persons present, households present, both present, and neither present.

Unify the `TravelTimeFunction` type alias so model, scheduling, validation, and tests share one canonical callable contract.

Add a small import/source audit proving public modules import or re-export `TravelTimeFunction` from one canonical owner, while behavioral tests continue to exercise callable travel-time success and failure cases.

Either centralize validated integer-second narrowing in the neutral schema or time vocabulary module, or document that validation owns narrowing while model `_optional_int` is only a post-validation extraction helper.

Add a regression test proving validation prevents float and nullable-integer drift before model construction.

## Phase 3: Time and Column Vocabulary Contracts

Create one small source of truth for time unit constants, using actual English names such as `SECONDS_PER_MINUTE`, `SECONDS_PER_HOUR`, `SECONDS_PER_DAY`, `DEFAULT_OBSERVATION_WINDOW_SECONDS`, `DEFAULT_SEQUENCE_INTERVAL_SECONDS`, and `DEFAULT_TIME_ORIGIN_CLOCK`.

Do not reintroduce the shorthand `t0` in code, docs, tests, or comments.

Use a clear term such as `time_origin_clock`, `time_origin_second`, or `survey_time_origin_second` whenever the concept is needed.

Move repeated canonical column-name groups to one source module that is generic and does not import validation implementation.

Keep dataframe column literals in tests only when the local literal makes the fixture easier to read than a constant import.

Add an AST-based contract test that fails if source modules define duplicate uppercase time constants, duplicate default time-origin clocks, or inline default time values that should come from the shared constants.

Add a test-scope timing-literal audit with a narrow allowlist for readable fixtures, or require a review note explaining why repeated test timing literals remain local.

Add a source scan test for forbidden terminology such as standalone `t0` in public code and docs.

## Phase 4: Model and Dependency Direction Contracts

Remove or invert the dependency from `athenspop.model.survey` to `athenspop.validation.schema`.

Move shared schema constants or canonical column groups to a neutral low-level module if both model and validation need them.

Keep validation as a boundary concern and keep internal model construction lean.

Add an import-graph contract test that asserts visualization is a leaf dependency and that model does not import validation implementation modules.

Make the import-graph contract explicitly assert that `athenspop.__init__` does not import `athenspop.visualization` or any visualization symbol unless the project intentionally documents root visualization re-exports as mandatory public surface.

Add an import smoke test proving `import athenspop` does not import `matplotlib.pyplot`.

Decide whether Matplotlib belongs in mandatory dependencies or an optional visualization extra.

If Matplotlib stays mandatory, keep visualization lazy-loaded but revise the plan wording and docs so "optional" means optional import surface rather than optional installation.

If Matplotlib becomes optional, add an isolated minimal-install or metadata check proving `import athenspop` succeeds without visualization extras and that `athenspop.visualization` has the expected missing-extra behavior until the extra is installed.

Decide whether root-level re-exports should include optional visualization functions.

Require tests to import `TimingPattern` from its final public or neutral owner, or to construct model fixtures through public `SurveyDataset.from_dataframes` when that better matches the tested contract.

Require maintained examples and example tests to import `TimingPattern`, `TravelTimeFunction`, `DissimilarityMatrix`, and other shared contracts from their final public or neutral owners rather than from implementation modules.

Prefer importing visualization from `athenspop.visualization` explicitly so ordinary users do not pay optional plotting import cost.

## Phase 5: Scheduling and Generation Contracts

Keep one scheduler core for realizing departure ranges and for repeated generation.

Keep the public semantics separated: `schedule_once` realizes one dataset, while `generate_schedules` repeatedly samples from the same validated model.

Add property-like deterministic tests for seed stability, diary feasibility, no negative travel times, no negative activity durations, and no unintended metadata retention.

Add boundary tests for deterministic and callable travel-time functions.

Add explicit tests for non-FIFO callable behavior when `refine_callable_departure_windows` is enabled or disabled.

Add tests for trips at the observation-window boundary and final-trip exceptions.

Make scheduler diagnostics preserve enough information for a non-expert user to understand why a diary was skipped.

## Phase 6: Sequence, Clustering, and Visualization Contracts

Reject negative, NaN, and infinite substitution costs before computing sequence dissimilarities.

Reject non-finite or non-positive `indel_cost` values in both sequence-distance public functions.

Reject negative, NaN, infinite, nonsymmetric, or nonzero-diagonal precomputed dissimilarity matrices before linkage.

Reject non-square, wrong-rank, and too-small precomputed dissimilarity matrices before calling SciPy linkage.

Add tests proving invalid distances cannot produce negative linkage heights.

Centralize `_materialize_sequences` in one generic helper module used by clustering and visualization.

Centralize or intentionally separate `_required_child` so tree traversal behavior cannot drift between clustering and visualization.

Mark visualization constants such as `_DEFAULT_COLORS` with explicitly parameterized `Final[...]` annotations.

Mark `DENDROGRAM_COORDINATE_COUNT` with an explicitly parameterized `Final[...]` annotation.

Convert package `__all__` definitions to immutable typed constants such as `__all__: Final[tuple[str, ...]] = (...)`.

Add a typed-constant audit that rejects bare `Final` annotations; every `Final` marker must include the bracketed concrete type, such as `Final[int]`, `Final[str]`, or `Final[tuple[str, ...]]`.

Either centralize the duplicated `DissimilarityMatrix` type alias in a neutral low-level module or document why sequence and clustering intentionally keep separate aliases despite identical contracts.

Split `episodes_from_diary` into small named helpers that reflect the diary construction order.

Keep the resulting sequence code readable and add comments only for the non-obvious interval and cropping logic.

Validate cluster labels as finite positive integers.

Add tests rejecting float, NaN, infinite, zero, negative, and missing cluster labels where integer clusters are required.

Add visualization invalid-input tests for sequence-count mismatch, unequal sequence length, empty sequences, missing state groups, invalid cluster counts, and invalid linkage shape.

Strengthen the visualization smoke test so it asserts stable public semantics such as displayed cut count, displayed cluster membership, state-panel content, and legend labels.

Reduce coupling to exact SciPy dendrogram coordinates by testing stable public semantics such as cluster membership, displayed cut count, and figure axes content.

## Phase 7: Test Suite Contracts

Move repeated test travel-time helpers into `tests/conftest.py` or a small local test helper module.

Use named constants for repeated expected test timings where the constant clarifies the scenario.

Do not replace every numeric example with a constant if doing so makes a single-row fixture harder for students to read.

Apply the same named-constant or allowlist rule to example tests, especially artifact counts such as 513, 1347, 512, 461, 288, 96, and travel-time fixture values.

Add tests for every validation issue code that is part of the public report contract.

Add tests for every supported timing pattern and every unsupported timing-column combination.

Add tests for table-level validation diagnostics including `table_not_dataframe`, `duplicate_columns`, and `missing_required_columns`.

Add tests for unsupported arrival-window columns.

Add tests for missing trip sequence diagnostics when duplicate concrete departure times cannot define diary order.

Add tests for scheduler `missing_travel_time_function` and `travel_time_function_error` diagnostics.

Add tests or narrow unreachable-branch explanations for every documented public `SchedulingIssue.code` emitted by `schedule_once`, including `arrival_after_observation_window`, `activity_duration_too_short`, `infeasible_future_departure`, `missing_departure`, `infeasible_departure_window`, `non_positive_travel_duration`, `missing_travel_time_function`, `travel_time_function_error`, and `invalid_travel_time_function_result`.

Add tests for `ValidationReport.has_warnings()` and warning-only reports.

Add tests for optional persons and households tables in all four combinations: neither, persons only, households only, and both.

Add tests proving join validation is vacuous after a row is already marked invalid.

Add tests proving chain validation is vacuous after a chain is already marked invalid.

Add tests proving metadata accepts only the documented scalar types and rejects nested objects with one clear error.

Rename portability tests so they do not overclaim real-world survey coverage.

Keep synthetic portability tests as generic adapter-shape smoke tests only.

Move any example-data fixtures that are paper-specific or Athens-specific under `examples/athens/` or another example-owned location.

Remove unused Attica shapefile bundles from tests unless a retained test proves they are needed.

## Phase 8: Documentation Contracts

Update API documentation so the IO page describes clock conversion only and does not imply a broader IO framework.

Document that the library accepts and returns Python objects such as pandas dataframes, model objects, NumPy arrays, and Matplotlib figures.

Document that file formats, CSV loading, SVG writing, paper-specific artifacts, and dataset-specific schema adapters belong in examples or user code.

Document the validation report lifecycle: schema errors, row errors, chain errors, warnings, invalid rows, invalid chains, and `raise_if_invalid()`.

Document scheduler semantics with plain English definitions of departure second, arrival second, travel time, departure window, observation window, and time origin.

Document the sequence and clustering method at a conceptual level without tying it to the Athens example.

Document that examples are teaching workflows and not strict audit scripts.

Remove or rewrite stale internal plan references that mention removed scripts or obsolete canonical terminology.

Keep internal plans out of public package distributions.

## Phase 9: Maintained Example and Artifact Contracts

These items are part of the blocking remediation surface for maintained example code, example tests, and checked-in example documentation.

Keep the paper reproduction as an Athens example, not as canonical package behavior.

Move paper-specific tests to the example area or rewrite them as generic package contract tests.

Split or restructure `examples/athens/reproduce.py` so the call order and pipeline stages are readable without forcing future maintainers to navigate a thousand-line script.

Consolidate or justify semantic duplicate helpers across examples and source, including Athens `_issue`, `_diary_id`, `_states`, travel-time helper aliases, and matrix type aliases.

Consolidate or test the Athens canonical purpose and mode vocabulary so every `MODE_MAP` output is accepted by sequence mode reduction and the travel-time resolver vocabulary, and every `PURPOSE_MAP` output is accepted by activity reduction or explicitly exempted.

Keep example-specific file IO in example modules only, and keep package source free of CSV, NPY, JSON, and SVG writer responsibilities.

Replace example imports from package implementation modules with public or neutral package contracts.

Add example-level architecture tests or audits so maintained examples do not reintroduce validation-internal imports, source-internal type aliases, or root visualization imports.

Add example-level style/tooling gates equivalent to the source/test gates, with narrow allowlists only where a teaching fixture is clearer with a local literal.

Either document maintained example entry points as trusted-only internals or add boundary/error contract tests with clear messages for malformed wide diary inputs, missing wide columns, non-positive fixture travel times, malformed activity/time cells, missing demographic columns, malformed routing resources, and infeasible `run_pipeline` scheduling.

Add a narrow justification or consolidation decision for `AthensArtifactValidation.raise_if_invalid()` versus `ValidationReport.raise_if_invalid()`.

Strengthen Athens artifact validation only where it guards documented example outputs.

Remove machine-local absolute paths from generated example output manifests.

Verify documented routing resource hashes or remove the claim that they are verified.

Fix the Athens dendrogram reproduction by plotting the cut dendrogram at the selected cluster count and replacing displayed cut nodes with purpose and mode distributions across the observation period.

Compare the generated Athens dendrogram against the paper figure as an example-level visual regression or manual review artifact, not as a core package test.

## Optional Post-Remediation Performance and Profiling Follow-Up

These items are retained because slow sequence distance and dendrogram workflows were raised in the broader project review, but they should not block closure of the source/test contract remediation unless profiling exposes an avoidable generic algorithmic defect.

Add a small profile-guided optimization pass after correctness and contracts are stable.

Profile sequence distance construction, dendrogram construction, cut-tree visualization, and any Athens example steps that are currently painfully slow.

Keep optimizations local and measurement-driven.

Prefer vectorization, batching, caching, and library routines over clever custom code.

Add lightweight performance smoke tests or benchmark notes only where they prevent obvious regressions without making CI fragile.

## Phase 11: Automated Review Loop

After each coherent slice, run `uv run rtk pytest -q tests examples/athens/tests`.

After each coherent slice, run `uv run rtk ruff check src tests examples`.

After each coherent slice, run `uv run rtk ty check src tests examples`.

After style tooling changes, run the non-line-length strict Ruff slice equivalent to `ruff check src tests examples --isolated --select C901,PLR0912,PLR0915,PLR2004,SIM,ARG`.

After style tooling changes, run the prose-aware structural-line audit instead of an isolated `E501` command.

After package-boundary changes, run an sdist build and inspect the archive contents.

After import-direction changes, run the import-graph contract test, example import-graph contract test, and root import smoke test.

After documentation changes, build the docs and check for stale generated pages.

After the implementation is complete, run one integrated main-agent completion review over requirements, evidence, docs-code-test consistency, deterministic checks, and residual risk.

Run independent panel review only when explicitly requested by the user or required by project-local instructions.

When an independent panel is requested, scope it to the current change and include `src`, `tests`, and `examples` only when all three surfaces are affected.

Do not close the work until direct checks, integrated review findings, and plan items agree.

## Work Order

First, fix tooling so future checks can catch code style, complexity, import-direction, and package-boundary regressions.

Second, centralize time constants, column vocabulary, and travel-time callable typing because these changes reduce duplication before behavioral fixes.

Third, fix validation boundary bugs and add contract tests.

Fourth, fix scheduling config and scheduling metadata behavior and add contract tests.

Fifth, fix sequence, clustering, and visualization validation and add contract tests.

Sixth, simplify duplicated helpers and overly complex functions.

Seventh, clean package artifacts, docs, examples, and stale internal references.

Eighth, clean maintained example code and tests so they use public contracts, avoid semantic duplicate primitives, and have explicit artifact-count constants or allowlists.

Ninth, run the full direct validation and integrated completion review loop.

After remediation is closed, run the optional profiling follow-up only if requested or if deterministic checks reveal a concrete generic performance defect.

## Settled Decisions

Decision: use an 80-character structural Python code line limit for maintained source, tests, and examples.

Rationale: the project is explicitly following PEP 8 and Google Python style, while the harness separately forbids hard-wrapping prose.

Implementation note: enforce structural code width with Ruff and/or a prose-aware audit, and keep narrow exceptions for docstrings, comments, URLs, and exact user-facing messages that must remain unwrapped.

Decision: create `athenspop.time_units` as the neutral source of truth for time unit constants and generic time defaults.

Rationale: `time_units` is plain English, discoverable, and narrower than a vague `_constants` module.

Decision: create a neutral schema contract module for canonical table names, column names, timing patterns, and dataframe schema vocabulary needed by both validation and model construction.

Rationale: model construction must not import validation implementation details, and validation must not be the owner of generic dataframe vocabulary.

Decision: create a neutral type contract module for shared callable and matrix aliases that are used across model, scheduling, generation, sequence, clustering, tests, and examples.

Rationale: `TravelTimeFunction` and `DissimilarityMatrix` are cross-module contracts; keeping local aliases invites drift.

Decision: do not re-export visualization symbols from `athenspop.__init__`.

Rationale: visualization remains available through `athenspop.visualization`, while root import remains lightweight and does not import Matplotlib.

Decision: move Matplotlib to an optional visualization extra, and include that extra in the development/test dependency surface.

Rationale: validation, scheduling, sequence, and clustering should install without plotting dependencies, but maintained visualization tests still need a supported dependency path.

Decision: remove the generic validation warning that assumes the scheduler's default minimum activity duration.

Rationale: scheduler feasibility policy belongs to scheduling configuration and diagnostics; generic dataframe validation should not warn using a duplicated scheduler default.

## Implementation Progress

Completed: the open decisions above are settled and explicitly recorded in this plan.

Completed: `athenspop.time_units`, `athenspop.schema`, and `athenspop.types` now hold shared time constants, dataframe schema vocabulary, timing patterns, travel-time callable typing, and dissimilarity matrix typing.

Completed: package `__all__` definitions and new constants use bracketed `Final[...]` annotations, and a repository contract test rejects bare `Final`.

Completed: root package imports no longer re-export visualization, and repository tests prove `import athenspop` does not load Matplotlib or `athenspop.visualization`.

Completed: Matplotlib has moved from core dependencies to the `visualization` optional extra, while the development dependency surface installs Matplotlib deliberately for maintained visualization tests.

Completed: maintained tests and examples import `TimingPattern`, `TravelTimeFunction`, and `DissimilarityMatrix` from neutral owners rather than validation implementation modules.

Completed: key normalization now happens in copied boundary tables before duplicate-key checks, and tests cover duplicate keys after string normalization plus non-scalar identity and movement fields.

Completed: clock conversion returns nullable integer seconds for mixed missing values and rejects non-scalar clock cells with a clear boundary error.

Completed: `SchedulingConfig` validates policy values at construction/post-init time, and tests cover negative dwell, non-positive windows, and non-boolean flags.

Completed: validation no longer emits `short_activity_duration` based on the scheduler's default minimum activity duration, and tests prove validation does not assume that scheduling policy.

Completed: `schedule_once` filters optional person and household metadata to the scheduled diaries that remain after infeasible diaries are dropped, while diagnostics still record skipped diaries.

Completed: sequence dissimilarity rejects invalid insertion/deletion costs and invalid substitution costs before dynamic-programming computation.

Completed: clustering rejects invalid precomputed dissimilarity matrices, invalid linkage matrices, invalid cluster counts, and non-integer cluster labels before SciPy calls or summary construction.

Completed: clustering and visualization share one private equal-length sequence materializer instead of carrying duplicate helper bodies.

Completed: visualization tests cover sequence-count mismatch, empty sequences, unequal sequence length, empty or unknown state groups, invalid cluster counts, and invalid linkage shape.

Completed: Ruff now formats structural Python code at 80 characters, and a repository contract test enforces the same structural width while exempting strings, comments, docstrings, and f-string message/prose lines.

Completed: the source distribution now excludes private notes, generated docs, internal plans/design notes, root paper artifacts, Athens raw/routing data, and local test data through Hatchling sdist rules plus a built-archive contract test.

Completed: a source import-graph contract now verifies visualization remains optional, model code does not import validation implementation modules, and Matplotlib imports stay inside `athenspop.visualization`.

Completed: validation report tests now cover warning-only reports through `has_warnings` and `raise_if_invalid()`.

Completed: validation and scheduling diagnostic issue codes emitted by source are now covered by tests, and the unreachable `missing_arrival` scheduler diagnostic was removed in favor of an internal invariant check.

Latest direct validation: `uv run rtk pytest -q` passed with 170 tests.

Latest direct validation: `uv run rtk ruff check src tests examples` passed after the completed slices.

Latest direct validation: `uv run rtk ty check src tests examples` passed after the completed slices.

Pending: continue example boundary tests, documentation consistency, and optional profiling follow-up.
