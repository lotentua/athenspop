# Long Canonical Rewrite Plan

## Purpose

This plan defines the minimum realistic work needed for a first complete maintainable release of `athenspop` as a Python library whose canonical input is long-form travel survey data and whose v1 scientific target is to reproduce `CSuM2026.pdf` from the source in `CSuM2026.zip`.

The goal is not to preserve legacy code, legacy examples, or wide-form survey compatibility. The goal is a clean package that a small technical team, undergraduate students, and non-expert users can understand, test, document, and extend after the original author leaves.

## V1 Success Criteria

- The public library accepts one required `trips: pandas.DataFrame` and two optional tables, `persons: pandas.DataFrame | None` and `households: pandas.DataFrame | None`.
- The canonical join keys are `household_id`, `person_id`, and `trip_id`; v1 requires these conventional column names rather than a flexible column specification layer.
- The internal data model stores time as integer seconds from a declared `t0` and never stores pandas timestamps or fractional seconds internally.
- Input validation happens at the boundary and returns one validation report that groups schema, key, join, domain, timing, chain, and methodological warnings while suppressing downstream checks per bad row or chain so one root problem does not trigger cascades of duplicate errors.
- Internal modules assume validated model objects are complete and correct; they should not repeat expensive input validation throughout the package.
- The package reproduces the paper's core pipeline: feasible diary scheduling, 512 valid diaries, 04:00 anchored 24-hour observation window, 15-minute state sequences, compound state-period labels, reduced alphabet, paper-specific transition-rate substitution costs, optimal matching dissimilarities, average-linkage hierarchical clustering, and documented figures/tables needed for the examples.
- The examples folder contains only documented, step-by-step notebooks or scripts that recreate the paper from canonical long-form inputs; random exploratory scripts, old notebooks, and wide-form leftovers are removed or migrated.
- The package builds, imports, tests, and documents cleanly from a fresh checkout with `uv`, and the docs build is part of release validation.

## Evidence Base

- `CSuM2026.zip` is the methodological authority for v1. The paper defines diaries as continuous episodes partitioning a 24-hour window, discretizes to 15-minute bins, assigns states by maximum temporal overlap with earliest-start tie breaking, adds four demand periods, reduces activities and modes before transition counting, excludes self-transitions from transition denominators, uses `c(i, j) = 2 - P(j|i) - P(i|j)`, uses `gamma = 1`, computes optimal matching by generalized Wagner-Fischer, and clusters with average linkage.
- The 2022 NHTS user guide supports the ordinary household travel survey split into household, person, and trip files, including link variables between household, person, and trip files and trip records with start times, end times, and destinations: https://nhts.ornl.gov/assets/2022/doc/2022%20NextGen%20NHTS%20User%27s%20Guide%20V2_PubUse.pdf
- ActivitySim documents household/person dependent-table slicing with a primary household table and person rows connected through a foreign key, emphasizes vectorized pandas/NumPy operations for performance, includes established probabilistic and logit trip-scheduling model components, and is BSD-3-Clause licensed, which makes it a strong source to mimic, copy, or adapt where attribution and license obligations are satisfied: https://activitysim.github.io/activitysim/v1.0.4/core.html and https://activitysim.github.io/activitysim/v1.0.4/models.html and https://github.com/ActivitySim/activitysim
- ActivitySim remains the first external reference for any current or future overlap with activity-based travel-model algorithms, not only scheduling; relevant areas include table slicing, time windows, feasible alternatives, random streams, tracing, chunking, choice-model utilities, output summaries, and failure policies.
- PopulationSim, implemented on the ActivitySim framework and BSD-3-Clause licensed, is the companion reference for reproducible household/person seed tables, controls, configuration files, explicit output summaries, validation notebooks, and named CSV outputs. It is not a diary scheduler and its population-synthesis algorithms are out of scope for v1, but its reproducibility posture should shape the paper example outputs: https://activitysim.github.io/populationsim/ and https://activitysim.github.io/populationsim/application_configuration.html and https://activitysim.github.io/populationsim/validation.html and https://activitysim.github.io/populationsim/software.html and https://github.com/ActivitySim/populationsim
- TraMineR `seqtrate` and `seqcost` document the standard transition-rate cost formula and default indel behavior, but the source shows the denominator includes all source-state positions, including self transitions, whereas the paper intentionally excludes self transitions: https://traminer.unige.ch/doc/seqtrate.html and https://traminer.unige.ch/doc/seqcost.html and https://raw.githubusercontent.com/cran/TraMineR/master/R/seqtrate.R
- Sequenzo is a Python-native social sequence analysis package inspired by TraMineR, provides compiled distance computation, accepts custom substitution matrices for OM, and has active documentation and source, so it should be used only where it preserves the paper's exact semantics with less maintenance cost than local code: https://github.com/Liang-Team/Sequenzo and https://sequenzo.yuqi-liang.tech/zh/function-library/get-distance-matrix and https://raw.githubusercontent.com/Liang-Team/Sequenzo/main/sequenzo/dissimilarity_measures/get_distance_matrix.py
- PAM's current public docs show a useful activity-modeling package shape with core models plus `read.diary`, `read.matsim`, `write.diary`, `write.matsim`, clustering, distance, and time sampler modules; Wayback confirms the old GitHub source tree existed with modules such as `activity.py`, `core.py`, `read.py`, `write.py`, `planner`, `samplers`, and `policy`: https://arup-group.github.io/pam/latest/ and https://web.archive.org/web/20210320100721/https://github.com/arup-group/pam/tree/master/pam
- Documentation tooling should be chosen after a small repo-local spike because Material for MkDocs has announced maintenance mode and MkDocs 1.x uncertainty, while PyData Sphinx Theme is a maintained scientific-docs option with responsive design, API docs, and Jupyter support: https://squidfunk.github.io/mkdocs-material/blog/2025/11/11/insiders-now-free-for-everyone/ and https://pydata-sphinx-theme.readthedocs.io/en/stable/

## Locked V1 Decisions

- The canonical input API is dataframe-first: `SurveyDataset.from_dataframes(trips, persons=None, households=None, *, travel_time_fn=None, t0_label=None)`.
- The dataframe loader expects canonical time columns to already be integer seconds relative to `t0`; clock-string parsing is a separate helper with an explicit `t0_clock`, overnight wrap policy, and documented output columns.
- For paper reproduction, the clock parser uses `t0_clock = "04:00"` and wraps times before 04:00 to the next diary day, so a clock time such as `03:30` becomes 84600 seconds after diary start rather than 12600 seconds after civil midnight.
- V1 uses required conventional column names rather than a user-provided column map. A later `ColumnSpec` feature can be added if real datasets make it necessary.
- `trips` must contain `household_id`, `person_id`, `trip_id`, `origin`, `destination`, `purpose`, and `mode`, plus exactly one valid timing pattern per row.
- `persons` is optional; when provided it must contain `household_id` and `person_id`, and any extra columns become typed person metadata.
- `households` is optional; when provided it must contain `household_id`, and any extra columns become typed household metadata.
- Table identity is explicit: `households` is unique on `household_id`, `persons` is unique on `(household_id, person_id)`, and `trips` is unique on `(household_id, person_id, trip_id)`.
- The package will not support backward compatibility for current wide-form scripts or old intermediate table layouts.
- The package will not use concrete timestamps internally. Boundary helpers may parse clock strings, timedeltas, or timestamps, but validated internal objects store integer seconds from `t0`.
- For the paper example, documentation should set `t0` to 04:00 local diary time and explain that `departure_second = 0` is valid.
- V1 supports concrete timings through `departure_second + arrival_second`, `departure_second + travel_time_seconds`, and `departure_second + travel_time_fn` when `travel_time_fn` is supplied at dataframe loading or model construction.
- V1 supports uncertain timings only as a departure window with either `travel_time_seconds` or a construction-time deterministic `travel_time_fn`: `earliest_departure_second + latest_departure_second + travel_time_seconds` or `earliest_departure_second + latest_departure_second + travel_time_fn`.
- Arrival windows and combined departure-window plus arrival-window inputs are deferred because they require a richer interval feasibility model and are not needed to reproduce the paper.
- The scheduler and trip generator are semantically separate public APIs but share the same internal realization engine.
- Validation reports may include methodological warnings, but hard errors should be concise and should suppress downstream checks per affected row or chain while continuing to collect independent errors into one report.
- The clustering module may depend on Sequenzo only if custom substitution matrices, indel behavior, normalization, ordering, missing handling, and performance are verified against the paper and existing local multithreaded implementation.
- If Sequenzo's built-in `TRATE` differs from the paper because of self-transition treatment, v1 must keep local paper-specific transition counting and pass a custom substitution matrix or keep local distance code.

## Deliberately Deferred

- Wide-form input compatibility.
- Backward-compatible imports for old `core`, `io`, `models`, and exploratory scripts.
- Flexible user column mapping.
- Arrival-time ranges.
- Joint departure and arrival ranges.
- MATSim import/export adapters.
- PAM-compatible adapters.
- Full trip-generation modeling beyond repeated calls to the range-realization engine.
- External cluster validation and full sensitivity analysis beyond paper reproduction tests.
- Public CLI, GUI, service API, or workflow orchestration.
- Publishing or maintaining GitHub issues from this plan. If remote project management is wanted later, create one feature request for arrival-window support and one for MATSim/PAM interoperability after v1 is green.

## Current Implementation Snapshot

Reviewed on 2026-06-19 against the current `implement-long-canonical-v1` worktree.

- Canonical package surface exists under `src/athenspop` with `validation`, `model`, `io`, `scheduling`, `generation`, `sequence`, and `clustering` modules, plus an intentional public API in `athenspop.__init__`.
- Legacy active-surface packages and examples have been removed from the maintained source tree: `athenspop.core`, `athenspop.long`, `athenspop.models`, `athenspop.utils`, `athenspop.main`, `tests/long`, `tests/models`, and `examples/v1`.
- Boundary validation, lean dataclass model construction, dataframe/CSV IO helpers, scheduling, repeated generation, generic sequence construction, paper-specific sequence/cost construction, local OM dissimilarities, average-linkage clustering, docs, and source-hash checks are implemented and covered by the current test suite.
- The migrated paper source and routing resources are checked in under `examples/paper/data/`; `load_paper_wide_diaries()` verifies 513 raw diaries, 1347 canonical trips, 513 person rows, and 513 household rows.
- The generic paper resolver default uses finite-mean fallback for missing routing samples and schedules all 513 migrated diaries; the strict paper resolver preserves the legacy non-finite transit sample for `549_trip_2` and produces the 512-diary paper analysis set with an explicit scheduling diagnostic.
- `uv run python -m examples.paper.reproduce` now writes and validates the current computational artifact set under `examples/paper/output/full`: canonical tables, source hashes, input-stage report, validation report, scheduling diagnostics, scheduled trips, diary summary, episodes, state sequences, compound state sequences, transition counts, substitution costs, dissimilarity matrix, average-linkage matrix, cluster labels, cluster summaries, state distributions, temporal cluster distributions, demographic summaries, SVG figures, dendrogram layout, dendrogram SVG, and manifest.
- The maintained smoke path remains available through `examples.paper.reproduce.write_smoke_artifacts(...)` and `examples/paper_reproduction_smoke.py` for fast tests and documentation examples.
- Current broad validation evidence from the latest implementation slice: `uv run rtk pytest -q tests examples\paper` reports 95 tests passing; `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run sphinx-build -W -b html docs docs\_build\html`, `uv build`, and `uv run python -m examples.paper.reproduce` with automatic artifact validation have passed.
- Current completion state: the implementation checklist below is crossed off, release validation and profiling notes are recorded, and the user-requested completion panel is intentionally separate from this implementation pass.

## Target Package Shape

- `athenspop.validation`: dataframe schema checks, staged row checks, join checks, domain checks, timing-pattern checks, chain feasibility prechecks, warnings, `ValidationReport`, `ValidationError`, and `raise_if_invalid()`.
- `athenspop.model`: lean validated dataclasses or Pydantic models for `Trip`, `Diary`, `SurveyDataset`, `PersonMetadata`, `HouseholdMetadata`, `TimeWindow`, and typed scalar metadata values.
- `athenspop.io`: dataframe boundary functions only, with CSV helpers as thin wrappers around pandas; no hidden global state.
- `athenspop.scheduling`: shared interval realization engine, deterministic seeded sampling, feasibility checks, generic return-home imputation support, and explicit diagnostics for infeasible diaries. Paper-specific empirical return-home imputation lives in `examples.paper.imputation` so the generic scheduler API stays lean.
- `athenspop.generation`: repeated schedule realization APIs that call the scheduler internals but expose generation semantics, sample counts, seeds, and aggregation helpers.
- `athenspop.sequence`: generic episode construction, discretization, overlap accounting, state-sequence extraction, and optimal-matching dissimilarity preparation from caller-provided costs.
- `athenspop.clustering`: average-linkage hierarchical clustering, cluster extraction, cophenetic diagnostics, state-distribution summaries, and no-plot dendrogram geometry for precomputed dissimilarity matrices.
- `athenspop.examples` should not exist as importable runtime code unless needed for packaged example data; executable narrative examples belong under `examples/`.
- `docs/`: user guide, API reference, validation guide, paper reproduction guide, design notes, and generated example outputs.

## ActivitySim Adaptation Gate

- Treat ActivitySim as the main external software reference for relevant activity-based travel-model algorithms and mathematical patterns, including household/person/trip table conventions, dependent table slicing, row-independent processing, reproducible random streams, vectorized dataframe operations, probabilistic/logit scheduling algorithms, choice-model utilities, feasible-alternative construction, and transportation-model package ergonomics.
- Before implementing any feature that overlaps ActivitySim now or in the future, inspect the ActivitySim docs and source for the corresponding algorithm, mathematical formulation, data contract, and validation pattern, then record whether the implementation will mimic the idea, adapt code, or deliberately stay local.
- Copy code only when it is smaller and clearer than reimplementation, compatible with the repo license, and accompanied by required BSD-3-Clause attribution and any local tests needed to prove behavior.
- Prefer adapting ActivitySim concepts over importing ActivitySim as a dependency for v1; this package is a paper-reproduction and survey-sequence library, not a full activity-based simulation framework.
- Candidate concepts to inspect are `households` as primary table, `persons` and `trips` as dependent tables, stable table indexes and foreign keys, chunking/slicing by household, deterministic random-number handling, tracing/diagnostics, table writing, person time windows, feasible-period masks, probability tables over feasible scheduling alternatives, tour/trip scheduling order, and logit-based scheduling/departure choice.
- Candidate PopulationSim concepts to inspect are explicit seed/input table inventories, expression-backed preprocessing only where it remains readable, output table manifests, validation summary statistics, validation notebook organization, and clear separation between generated outputs and source data.
- Follow ActivitySim's algorithmic and mathematical ideas wherever they fit the paper problem or a future extension, but translate them into a smaller, explicit, undergraduate-friendly `athenspop` interface rather than copying ActivitySim's expert-oriented API, configuration style, or terminology.
- Sequence analysis, paper-specific transition costs, optimal matching, and clustering are governed by `CSuM2026`, TraMineR/Sequenzo evidence, and local verification fixtures rather than ActivitySim or PopulationSim.

## Canonical Schema

### Trips Table

- Required identity columns: `household_id`, `person_id`, `trip_id`.
- Required movement columns: `origin`, `destination`.
- Required behavior columns: `purpose`, `mode`.
- Optional ordering column: `trip_sequence`; when present it must contain non-negative integer values that are unique within each `(household_id, person_id)` chain. If absent, ordering must be uniquely inferable from concrete departure information. Rows with uncertain windows, equal departures, or otherwise unresolved order require `trip_sequence`; input order is only a deterministic tie-break after the validation report has established that the tie is behaviorally harmless.
- Concrete timing pattern A: `departure_second`, `arrival_second`.
- Concrete timing pattern B: `departure_second`, `travel_time_seconds`.
- Concrete timing pattern C: `departure_second`, with `travel_time_fn` supplied to the dataframe loader or model constructor.
- Uncertain timing pattern D: `earliest_departure_second`, `latest_departure_second`, `travel_time_seconds`.
- Uncertain timing pattern E: `earliest_departure_second`, `latest_departure_second`, with `travel_time_fn` supplied to the dataframe loader or model constructor.
- A single trips DataFrame may contain the superset of timing columns, but each trip row must match exactly one timing pattern after null or non-applicable values are considered.
- Optional paper-specific source columns may be accepted only if they are explicitly documented as raw survey columns and converted into canonical columns before model construction.

### Persons Table

- Required columns when present: `household_id`, `person_id`.
- Optional metadata examples: `sex`, `age`, `education`, `employment_status`, `monthly_income`, `car_ownership`.
- Extra columns are preserved as typed metadata and are not interpreted unless a documented method uses them.

### Households Table

- Required columns when present: `household_id`.
- Optional metadata examples: `home_zone`, `household_size`, `vehicles`, `income_band`.
- Extra columns are preserved as typed metadata and are not interpreted unless a documented method uses them.

## Time Semantics

- All internal time values are `int` seconds from `t0`.
- `0` is valid and means exactly `t0`, not missing.
- The default observation window for paper reproduction is `[0, 86400]`.
- Boundary parsing may accept `HH:MM`, `HH:MM:SS`, pandas timedeltas, Python timedeltas, or integer seconds, but parsed output must be seconds before validation returns valid model objects.
- V1 should enforce integer seconds at validation boundaries. Internal arithmetic should use integers; any travel-time function returning a float should be rejected or rounded only if an explicit documented policy is chosen before implementation.
- The travel-time callable protocol should be minimal for v1: `TravelTimeFn(origin, destination, mode, departure_second) -> int`. Time-dependent deterministic functions are allowed, but seeded reproducibility is guaranteed only when the callable is deterministic with respect to its arguments and stable external data. Stochastic travel-time callables are deferred until the protocol can pass scheduler-controlled random state or an explicit realization context; user callables that close over their own mutable random state are outside the scheduler seed contract.
- Because a deterministic time-dependent callable can still depend on external dynamic data, each resolver call is a scheduler boundary: the scheduler must check the returned type and domain immediately and convert violations into scheduler diagnostics or errors without repeating full dataframe validation.

## Validation Design

- Validation is staged so one blocking problem suppresses downstream checks for that row or chain while independent errors elsewhere continue to be collected into one report.
- Stage 1 checks table presence, dataframe type, duplicate column names, required columns, and forbidden ambiguous timing combinations.
- Stage 2 checks key nulls, explicit table identity uniqueness, and stable row identity.
- Stage 3 checks joins: trip persons exist when `persons` is provided, trip households exist when `households` is provided, person households exist when both optional tables are provided, and optional tables do not introduce orphan rows unless explicitly allowed by a documented flag.
- Stage 4 checks scalar domains: seconds are integers and non-negative, purposes and modes are known or explicitly allowed as unknown categories, origins and destinations are present, and travel times are positive when they represent movement duration.
- Stage 5 checks timing pattern semantics: exactly one timing pattern per trip, departure before arrival, positive travel duration, valid departure windows, and no unsupported arrival range.
- Stage 6 checks diary-chain consistency by `(household_id, person_id)`: order can be resolved, trips do not overlap, activity gaps are representable, duplicate composite trip keys are invalid, and origin can either match prior destination or generate a warning/error according to the documented policy.
- Stage 7 checks paper-specific methodological warnings: missing return-home trip, final recreation exception, sequence cropping, unusually short activity duration, unknown mode aggregation, and travel-time function availability for timing patterns that require it.
- Current implementation covers Stage 7 warnings for missing return-home trips, the final recreation exception, unusually short concrete activity gaps, unknown paper purposes, and unknown paper modes. Sequence cropping and paper full-reproduction stage-count diagnostics remain release-validation work.
- The diagnostic report structure should expose `errors`, `warnings`, `invalid_rows`, `invalid_chains`, `summary`, `has_errors`, `has_warnings`, and `raise_if_invalid()`.
- If validated or normalized tables are returned, they should live in a separate `ValidationResult(report, normalized_tables)` or loader result rather than inside the diagnostic report itself.
- Error messages should be written for non-experts and include table name, row identifier, column name, bad value when safe, and one suggested fix.

## Scheduling And Generation

- The scheduler's first responsibility is to turn valid timing ranges into concrete feasible times while preserving the validated trip order and trip-chain constraints.
- The scheduler should also support the paper's constrained uniform sampling within departure intervals, minimum activity duration, return-home imputation, and 24-hour cropping.
- The scheduler design should compare the paper's uniform interval sampling against ActivitySim's probabilistic trip scheduling, trip scheduling choice, trip departure choice, person time-window, and feasible-alternative machinery, then implement only the direct paper-uniform method for v1 while leaving a small private seam for future probability-table or logit scheduling.
- The public scheduling API should be explicit, for example `schedule_once(dataset, *, seed=None, config: SchedulingConfig | None = None) -> ScheduledSurveyDataset`, where `SchedulingConfig` is a tiny typed options object rather than an open-ended configuration escape hatch.
- The public generation API should be explicit, for example `generate_schedules(dataset, n, *, seed=None, config: SchedulingConfig | None = None) -> list[ScheduledSurveyDataset]` or an iterator; this makes repeated stochastic realizations conceptually different from ordinary validation.
- The shared internal engine should accept a random generator, a feasibility policy, and a travel-time resolver, and should return diagnostics that explain infeasible diaries without exposing internal implementation details. V1 should keep any sampler seam private and minimal, such as one `choose_departure(feasible_interval, rng)` helper; public pluggable sampler or strategy objects are deferred until a probability-table or logit scheduler is actually implemented.
- V1 should prefer simple rejection sampling with bounded attempts if it reproduces the paper reliably. Only add optimization or constraint-programming machinery if rejection sampling cannot meet the paper's feasibility and runtime requirements.
- The minimum activity duration for paper reproduction is 30 minutes, i.e. 1800 seconds, unless the source paper or implementation evidence contradicts it.
- A failed diary should be excluded only by an explicit policy that records the reason, since the paper reports one infeasible diary and a final sample of 512.
- Imputed return-home movements are synthetic scheduled trips with explicit provenance such as `is_imputed_return_home = True`, a collision-proof generated trip ID namespace, and documented inclusion in sequence construction but separate treatment from observed survey trips in diagnostics and outputs.

## Sequence And Cost Construction

- Convert each scheduled diary into continuous episodes that partition the observation window without gaps or overlaps.
- Use the paper's activity/trip alphabet: activities from purposes plus travel states from modes, with activities and modes disjoint by construction.
- Discretize to 96 bins for the paper using `delta_seconds = 900`.
- Assign each bin to the state with maximum overlap duration; ties resolve to the earliest-starting overlapping episode.
- Period mapping for paper reproduction is based on diary time, not clock time: period 1 for `[0, 3h) U [15h, 24h]`, period 2 for `[3h, 6h)`, period 3 for `[6h, 12h)`, and period 4 for `[12h, 15h)`.
- Compound labels are `(state, period)` values encoded as stable atomic symbols only after all methodological transformations are complete.
- Reduced alphabet for cost construction groups activities into `home`, `rigid`, and `flexible`; groups taxi with car; groups bicycle and e-scooter as micromobility; and leaves the remaining modes as paper-defined categories.
- Transition counts for paper reproduction exclude self-transitions from both numerator and denominator. This is the key divergence from vanilla TraMineR/Sequenzo `TRATE` behavior and must have a dedicated test.
- Substitution costs are symmetric, zero on the diagonal, and computed as `c(i, j) = 2 - P(j|i) - P(i|j)` for `i != j`.
- Indel cost is the scalar `1` for paper reproduction.
- The distance output should be called a dissimilarity matrix unless a future proof or test establishes metric properties.

## Sequenzo Decision Gate

- Add a small verification fixture with a few short sequences where self-transition inclusion changes transition probabilities; compute the paper matrix and a pinned-source TraMineR-style matrix. A Sequenzo-style executable fixture is deferred unless Sequenzo becomes a runtime or optional test dependency, because v1 does not use Sequenzo built-in `TRATE`.
- Record the current decision in `docs/design/sequenzo_decision_gate.md`: keep paper-specific transition counting local for v1, keep the transparent local OM baseline, and consider Sequenzo only for a later custom-matrix OM wrapper after exact parity and performance checks.
- Gate TraMineR divergence with an authoritative tiny reference fixture: either run a pinned TraMineR version in release validation or store expected outputs derived from a pinned TraMineR source/version, then assert where the paper-specific matrix intentionally differs.
- Use Sequenzo for OM only if `get_distance_matrix(..., method="OM", sm=custom_matrix, indel=1, norm="none")` preserves labels, ordering, missing handling, and pairwise values exactly against local reference cases.
- Keep local distance code if Sequenzo requires awkward label padding, silently normalizes distances, changes missing semantics, lacks predictable ordering, or loses the existing multithreaded performance advantage.
- If both options are valid, prefer Sequenzo because compiled wheels and active maintenance reduce long-term burden.
- If local code stays, isolate it behind `athenspop.sequence.distance` with one clean public function, retain multithreading only where measured useful, and document why Sequenzo was not selected for v1.

## Clustering Module

- Implement paper reproduction with SciPy average-linkage hierarchical clustering on the precomputed dissimilarity matrix.
- Do not use Ward linkage because the paper does not assume Euclidean distances and explicitly selects average linkage.
- Provide helpers for cophenetic correlation, extracting the 10-cluster hierarchy, cluster labels, leaf ordering, and state-distribution summaries.
- Keep visualization helpers separate from core clustering so the algorithm can be tested without matplotlib.
- The dendrogram visualization should reproduce the paper enough for documentation, but exact publication styling is not a v1 blocker unless it changes interpretation.

## Documentation Tooling

- Default to Sphinx + PyData Sphinx Theme for v1 because this is a scientific Python library with notebooks and API reference needs, and Material for MkDocs has announced maintenance mode.
- Before implementation locks tooling, run only a bounded smoke test that proves the selected stack can build one quickstart page, one API page, and one notebook page in this repo.
- Reconsider MkDocs + mkdocstrings only if the Sphinx smoke test fails or creates disproportionate configuration.
- Current implementation decision: use Sphinx 9, PyData Sphinx Theme 0.19, MyST Parser 5, `sphinx.ext.autodoc`, `sphinx.ext.napoleon`, and `sphinx.ext.viewcode`. The smoke command is `uv run sphinx-build -W -b html docs docs/_build/html`.
- Public docs should include installation, quickstart, canonical schema, validation report guide, scheduling guide, sequence/clustering guide, paper reproduction walkthrough, API reference, glossary, and a short design rationale.
- Docs should be friendly and explicit, like PAM/Pydantic-style docs, but should not hide methodological constraints behind marketing prose.

## Release Task List

### Phase 0: Stabilize The Package Surface

- Remove tracked `__pycache__` files from version control and update `.gitignore` so generated bytecode no longer dirties the repo.
- Add a real `README.md` because `pyproject.toml` declares it and current project commands can fail without it.
- Update `pyproject.toml` with accurate package metadata, runtime dependencies, optional extras, dev dependencies, and supported Python versions.
- Add test dependency groups to `uv`, including pytest, coverage, SciPy, matplotlib, and notebook smoke-test tooling; defer docs-stack dependencies until the documentation spike records the selected tooling.
- Configure one static type check for exported public modules, preferably pyright or mypy over `src/athenspop`, or explicitly document a runtime-contract-test fallback if static typing proves disproportionate for v1.
- Keep `src/` layout and make `athenspop.__init__` export only intentional public APIs.
- Current implementation decision: use plain dataclasses plus explicit validation reports for v1 boundary and model contracts; remove `pydantic` from runtime dependencies unless a later measured need justifies it.

### Phase 1: Lock Paper Reproduction Requirements

- Convert the equations and methodological choices from `CSuM2026.zip` into `docs/design/paper_method_contract.md`.
- Record reproduction invariants: 513 raw diaries, 461 complete demographic records, one infeasible diary, 512 scheduled diaries, `t0 = 04:00`, `T = 86400`, `delta = 900`, 96 bins, 15 original states, 60 compound state-period labels, 36 reduced state-period labels, one constant indel, average linkage, and 10-cluster presentation.
- Record `CSuM2026.zip` and `CSuM2026.pdf` SHA256 hashes, extracted source-file inventory, canonical extraction/preprocessing command, expected row and diary counts at each stage, exact full reproduction command, and numerical/visual tolerance table.
- Create `docs/design/paper_output_manifest.md` listing each required figure, table, matrix, and summary output from `CSuM2026.pdf`, its generated artifact path, deterministic inputs/seeds, acceptance rule, and any explicitly deferred output.
- Review ActivitySim's table, pipeline, random, tracing, scheduling, and documentation patterns and record the small subset to mimic or adapt for v1.
- Write a short scheduling method note comparing paper-uniform scheduling with ActivitySim-style probability-table and logit scheduling, including why v1 chooses the simpler method and which internal seams preserve future compatibility.
- Add small deterministic fixtures that exercise interval sampling, return-home imputation, self-transition exclusion, period mapping, and overlap tie-breaking.
- Compare current `long` branch behavior to the paper and list code that can be deleted after canonical replacements pass.
- Current implementation status: `docs/design/paper_output_manifest.md` now contains the deterministic full-artifact baseline and release tolerances for counts, shapes, matrix structure, key numerical bounds, demographic summaries, temporal cluster distributions, and non-empty SVG outputs.

### Phase 2: Implement Canonical Validation

- Create the `athenspop.validation` module and its report types.
- Implement staged validators with row/chain skip behavior to prevent cascades.
- Implement canonical timing-pattern detection and precise errors for ambiguous or unsupported timing columns.
- Implement join validation for optional `persons` and `households` tables.
- Implement methodological warnings separately from hard errors.
- Add tests for every validator stage and for the "one root row error, no cascade" behavior.

### Phase 3: Implement The Lean Internal Model

- Create immutable or low-mutation model types for trips, diaries, scheduled diaries, metadata, and survey datasets.
- Store all times as integer seconds.
- Attach person and household records through metadata containers rather than bloating the diary model.
- Add constructors only from validated boundary data, not from arbitrary loose dicts.
- Add tests that internal constructors do not revalidate external dataframe mistakes and that validated edge cases such as `departure_second = 0` work.

### Phase 4: Implement Dataframe Loading

- Implement `SurveyDataset.from_dataframes(...)` or an equivalent top-level `load_survey(...)`.
- Preserve extra person and household columns as metadata.
- Preserve extra trip columns only if they are documented raw fields or metadata; otherwise warn or reject according to the validation policy.
- Add CSV helpers only as thin wrappers around dataframe loading.
- Regenerate or rewrite example data into canonical long-form CSVs.

### Phase 5: Implement Scheduling And Generation

- Build the shared realization engine for concrete departures, departure windows, fixed travel times, and user travel-time functions.
- Model feasible scheduling alternatives explicitly enough to support the paper's constrained uniform sampler. Preserve a minimal private choice helper so future ActivitySim-like probability-table or logit scheduling can reuse the same feasible intervals without shaping the v1 public API.
- Implement `schedule_once(...)` for converting ranges to feasible actual times.
- Implement `generate_schedules(...)` as repeated stochastic scheduling with shared internals and explicit seed handling.
- Implement the paper policies: constrained uniform sampling, 30-minute minimum activity duration, return-home imputation except final recreation, and 24-hour cropping.
- Current implementation status: strict reported-trip routing exclusion now yields the 512-diary analysis set; generic scheduler return-home imputation and cropping workflows are covered; and the full paper workflow now applies `examples.paper.imputation.impute_paper_return_home_trips(...)`, fitting observed return-home departures by previous activity purpose and adding 124 synthetic return-home trips with explicit provenance while preserving the single strict reported-trip routing exclusion.
- Add tests for deterministic seeding, infeasible diary diagnostics, stochastic travel-time functions, and integer second enforcement.

### Phase 6: Implement Sequence Construction

- Build continuous episode construction from scheduled diaries.
- Implement origin/destination-aware trip episodes and purpose-aware activity episodes.
- Implement discretization, overlap duration calculation, earliest-start tie-breaking, period mapping, compound labels, and reduced-label aggregation.
- Add tests that reproduce the paper's equations on small hand-computable diaries.

### Phase 7: Implement Distance And Clustering

- Implement paper-specific transition counting with self-transition exclusion.
- Implement substitution matrix construction and indel selection.
- Run the Sequenzo decision gate and either wrap Sequenzo with a custom matrix or isolate the local multithreaded implementation.
- Implement average-linkage clustering and cluster summary outputs.
- Add regression tests for distance values on small fixtures and snapshot-like tests for the paper dataset outputs within deterministic tolerances.

### Phase 8: Rebuild Examples As Documentation

- Treat `examples/` as documentation source, not a separate unsupported surface, and replace it with a documented paper recreation notebook sequence: data preparation, validation, scheduling, episode construction, sequence encoding, dissimilarity computation, clustering, visualization, and result interpretation.
- Keep `examples/paper_reproduction_smoke.py` as the maintained miniature canonical pipeline until the full paper notebook sequence is rebuilt; it should run validation, model loading, scheduling, sequence construction, dissimilarity calculation, average-linkage clustering, and dendrogram layout on tiny in-memory data.
- Keep `examples/paper/reproduce.py` as the maintained full artifact-writing workflow for the migrated CSuM2026 dataset; it writes named CSV, JSON, and NumPy outputs matching the paper output manifest shape so hidden notebook state does not become part of the reproducibility contract.
- Keep `examples/paper/inputs.py` as the wide-to-canonical converter scaffold: it converts both the checked-in three-diary fixture and migrated 513-diary source into canonical long-form tables. The migrated travel-time resolver now exists in `examples/paper/travel_time.py`; its default finite-mean policy supports robust generic scheduling of all 513 migrated diaries, while `missing_sample_policy="strict"` preserves the legacy non-finite routing sample for `549_trip_2` and yields the 512-diary paper analysis set.
- Keep notebooks executable in CI where runtime is reasonable and ensure they are linked from or built into public docs; if full distance computation is slow, add a smoke notebook plus a documented full reproduction command.
- Remove old random scripts after their useful logic has been migrated or explicitly discarded.
- Make example outputs deterministic by default with documented seeds.
- Current implementation status: `docs/user_guide/paper_walkthrough.md` is the notebook-like step-by-step guide around the maintained full computational artifact command. It calls the canonical library and example functions directly, and generated SVG figures remain reproducible output paths under `examples/paper/output/full/figures` rather than copied into built docs so documentation builds stay fast and independent of the full OM run.

### Phase 9: Build Public Docs

- Add docs configuration using the chosen stack.
- Add docs dependencies to `uv` only after the docs stack is selected and recorded.
- Add user-facing guides for install, quickstart, canonical schema, validation reports, scheduling/generation, paper reproduction, sequence analysis, clustering, and API reference.
- Add a "For students" glossary that explains diary, episode, state sequence, transition rate, substitution cost, indel, dissimilarity matrix, and hierarchical clustering in plain language.
- Add a design note explaining why v1 requires conventional column names and why arrival ranges are deferred.
- Add a short interoperability note mapping long-term PAM/MATSim ideas without promising v1 adapters.

### Phase 10: Clean Legacy Surface

- [x] Delete or quarantine old wide-form modules, stale imports, broken tools, old notebooks, and generated bytecode.
- Remove dependencies that no surviving code imports.
- Ensure all public names are documented or private.
- Add deprecation notices only if needed for current examples; otherwise delete unsupported APIs because backward compatibility is not a v1 goal.
- Current implementation status: the obsolete `athenspop.core`, `athenspop.long`, `athenspop.models`, `athenspop.utils`, sample `athenspop.main`, old `tests/long`, old `tests/models`, old `examples/v1` artifacts, and stale `tools/compile_resources.py` resource compiler have been removed from the active surface. The retained example surfaces are `examples/paper_reproduction_smoke.py` for fast smoke coverage and `examples/paper/` for the full paper workflow.

### Phase 11: Release Validation

- Run unit tests, integration tests, paper reproduction tests, linting, configured static type checks or documented runtime-contract fallback tests, package build, import smoke tests, and docs build from a clean environment.
- Verify that a fresh user can run the quickstart with only the documented commands.
- Verify that validation errors are understandable on intentionally bad data.
- Verify that the paper example reproduces the expected diary count, sequence dimensions, cost matrix properties, clustering method, and documented figures/tables.
- Verify the reproduction source hashes, output manifest, exact reproduction command, and TraMineR divergence fixture before declaring v1 complete.
- Record residual risks in a release note rather than claiming the package is "bug free" in an absolute sense.
- Current implementation status: release validation evidence and residual risks are recorded in `docs/design/release_readiness.md`. The deliberate full-artifact validation check is implemented by `examples.paper.reproduce.validate_paper_artifacts(...)` and is run automatically by `write_full_artifacts(...)`; the installed-wheel quickstart smoke passed in a temporary virtual environment.

### Phase 12: Rudimentary Profile-Guided Optimization

- After correctness, documentation, and paper reproduction are complete but before declaring the v1 release finished, run a small profiling pass on the full paper recreation and record wall-clock time and peak memory for scheduling, episode construction, discretization, transition counting, distance matrix construction, hierarchical clustering, and dendrogram visualization.
- Current implementation note: after integer-state encoding and NumPy-batched dynamic programming in `athenspop.sequence.distance`, the strict migrated paper pipeline completes in about 42 seconds on the current development machine and constructs the 512x512 OM dissimilarity matrix inside the full artifact workflow.
- Current implementation status: `docs/design/profiling_notes.md` records the profiling pass. The normal full artifact command completed in 41.776 seconds, the staged timing probe completed in 40.592 seconds, the OM dissimilarity matrix took 36.466 seconds, average linkage took 0.003 seconds, dendrogram layout took 0.005 seconds, SVG writing took 0.100 seconds, and no v1 optimization is justified under the 10-minute threshold.
- Treat the currently slow sequencing scripts, distance-matrix path, and dendrogram code as known performance-risk areas, but optimize only if the documented full paper reproduction exceeds the v1 release threshold, fails CI/docs smoke constraints, or prevents a non-expert from completing the workflow on stated hardware. The provisional threshold is 10 minutes wall-clock time and 4 GB peak memory on an ordinary laptop for the full paper recreation excluding optional notebook rendering.
- Prefer simple improvements first, following ActivitySim's performance posture where applicable: vectorized pandas/NumPy operations where they stay readable, precomputed code mappings, avoiding repeated dataframe scans, household/person-level chunking where useful, condensed distance storage where supported, caching stable sequence encodings, and moving plotting data preparation out of per-node loops.
- Preserve the paper's numerical and clustering outputs exactly while optimizing; every performance change needs a before/after timing note and the relevant regression tests.
- Do not add compiled extensions, multiprocessing complexity, or new heavy dependencies unless the profile shows that simple Python/NumPy/SciPy/Sequenzo-level improvements are insufficient for a documented v1 workflow.

## Next Implementation Priorities

1. [x] Resolve paper return-home imputation parity: inspect the removed empirical sampler and paper method text, decide whether v1 must reproduce it exactly or document a simpler replacement, then implement the chosen policy in `examples/paper` without changing the generic scheduler API unless a generic boundary is genuinely needed. This is implemented in `examples.paper.imputation` as empirical inverse-transform return-departure sampling by previous activity purpose; the full workflow uses strict routing for reported trips, finite-mean routing for synthetic return trips, writes 124 imputed trips, and validates the count in the artifact manifest.
2. [x] Add full artifact validation that checks the release-relevant generated files and stage counts from `uv run python -m examples.paper.reproduce`, including 513 attempted diaries, the single strict-routing `549_trip_2` exclusion, 512 scheduled diaries, `(512, 96)` sequence arrays, `(512, 512)` dissimilarity matrix, 10-cluster labels, source hashes, and manifest paths. This is implemented by `examples.paper.reproduce.validate_paper_artifacts(...)`, covered on smoke artifacts in `tests/test_paper_reproduction_artifacts.py`, and run automatically by the full artifact writer so ordinary unit tests do not pay the full OM runtime.
3. [x] Regenerate and document demographic outputs from the 461 complete records: marginal summaries, selected bivariate summaries, unavailable or ambiguous pair-selection rules, and figure artifact targets. This is implemented by `examples.paper.demographics`; the full artifact workflow writes `demographics/complete_records.csv`, `demographics/marginal_demographics.csv`, `demographics/bivariate_demographics.csv`, `figures/marginal_demographics.svg`, and `figures/bivariate_demographics.svg`, with the four selected bivariate pairs documented and tested.
4. [x] Produce the dendrogram visualization artifact or a documented plotting-ready intermediate that preserves hierarchy, the selected cluster cut, cluster sizes, and temporal state distributions. This is implemented by `athenspop.visualization`; the full artifact workflow writes `cluster_time_distribution.csv` with all clusters by time bin and `figures/dendrogram.svg` as a cut dendrogram whose displayed nodes contain activity-purpose and travel-mode distributions.
5. [x] Fill the numerical and visual tolerance table in `docs/design/paper_output_manifest.md` after the full artifact workflow, imputation policy, demographic outputs, and dendrogram outputs stabilize. The manifest now records deterministic current baselines for source conversion, validation, scheduling, imputation, sequence arrays, transition/cost tables, dissimilarity structure and max value, linkage shape, cluster outputs, demographic summaries, temporal cluster distributions, and non-empty SVG figures.
6. [x] Export richer per-row return-home imputation provenance in `scheduled_trips.csv`. Internal imputed trips already carried `is_imputed_return_home`, `imputation_method`, and `observed_last_trip_id`; the full artifact CSV now exports all three columns and artifact validation checks that imputed rows have complete provenance.
7. [x] Convert the paper workflow into a documented step-by-step notebook or notebook-like guide that calls the canonical library and example functions rather than reimplementing hidden notebook logic. This is implemented as `docs/user_guide/paper_walkthrough.md`, linked from the Sphinx user guide, and checked with a focused runtime probe for the source, conversion, validation, scheduling, imputation, episode, sequence, toy cost, and demographic snippets.
8. [x] Run a clean-environment release validation pass and record a short readiness note with residual risks, exact commands, package build evidence, docs build evidence, installed-wheel import evidence, and any deferred outputs. This is recorded in `docs/design/release_readiness.md`; the installed-wheel quickstart smoke passed in a temporary Python 3.12.11 environment, `uv build` produced both sdist and wheel, the docs build passed, and the full paper artifact command passed in 41.776 seconds.

## Minimum Test Matrix

- Validation tests for missing required columns, duplicate keys, orphan joins, ambiguous timing patterns, unsupported arrival ranges, negative seconds, float seconds, null keys, unknown categories, overlapping trips, impossible windows, and one-error-per-row cascade suppression.
- Scheduler tests for concrete times, fixed travel times, deterministic time-dependent travel-time callables, callable return-type and domain enforcement, scheduler-owned seed reproducibility, infeasible diary exclusion, minimum activity duration, final recreation exception, return-home imputation, and 24-hour cropping.
- Model tests for seconds-from-`t0`, `departure_second = 0`, optional persons, optional households, metadata preservation, and no accidental pandas timestamp leakage.
- Sequence tests for episode partitioning, overlap equation, tie-breaking, period mapping, label encoding, reduced alphabet mapping, and sequence length.
- Distance tests for self-transition exclusion, substitution matrix symmetry, diagonal zero, bounds `[0, 2]`, indel `1`, Sequenzo/local parity if Sequenzo is used, and multithreaded/local parity if local code remains.
- Reference tests for the pinned TraMineR-style fixture so the intentional self-transition divergence is executable evidence, not only a comment.
- Clustering tests for average linkage on a precomputed matrix, deterministic labels for a small fixture, and cophenetic diagnostic availability.
- Reproduction tests for the canonical paper dataset with deterministic seed, source hashes, output manifest, stage counts, and documented tolerances.
- Docs tests for importable API examples and executable quickstart snippets.

## Review Risks To Watch

- The biggest scientific risk is accidentally using standard TraMineR/Sequenzo `TRATE` semantics instead of the paper's self-transition-excluding transition probabilities.
- The biggest user-experience risk is overbuilding schema configurability before the canonical v1 path is stable.
- The biggest maintenance risk is keeping both old wide-form code and new long-form code alive; v1 should migrate useful logic and delete the rest.
- The biggest scheduling risk is letting stochastic generation and one-shot range realization share internals but blur public semantics.
- The biggest documentation risk is choosing a docs stack before testing notebook, API reference, and build ergonomics in this repo.

## First Implementation Slice

- Add README and package hygiene fixes.
- Add validation report types and canonical schema checks.
- Add model types and dataframe loading for concrete timing patterns.
- Add tests proving `departure_second = 0` is valid.
- Add one paper-derived fixture and make it pass through validation and model construction.
- Only then implement scheduling ranges, generation, sequences, distances, clustering, examples, and docs in the phase order above.
