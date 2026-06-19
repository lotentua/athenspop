# ActivitySim Adaptation Note

This note records the ActivitySim ideas that `athenspop` should mimic or adapt for v1 and future work. It is a design reference, not a dependency decision; v1 remains a small long-form travel-survey library with CSuM2026 maintained as an example workflow.

## Checked Sources

- ActivitySim 1.0.4 Core Components: https://activitysim.github.io/activitysim/v1.0.4/core.html
- ActivitySim 1.0.4 Models: https://activitysim.github.io/activitysim/v1.0.4/models.html
- ActivitySim 1.0.4 How the System Works: https://activitysim.github.io/activitysim/v1.0.4/howitworks.html
- ActivitySim source/license reference: https://github.com/ActivitySim/activitysim
- PopulationSim introduction, configuration, validation, and software notes: https://activitysim.github.io/populationsim/ and https://activitysim.github.io/populationsim/application_configuration.html and https://activitysim.github.io/populationsim/validation.html and https://activitysim.github.io/populationsim/software.html
- PopulationSim source/license reference: https://github.com/ActivitySim/populationsim
- PopulationSim current public docs are versioned as 0.5.1, while the GitHub repository lists v0.10.0 as the latest release on 2025-11-03; treat docs as the conceptual reference and inspect source/release notes before copying behavior exactly.

## Concepts To Mimic

- Table identity and dependency: ActivitySim uses `households` as a primary table, `persons` as a dependent table through `household_id`, and `trips` as a trip-level table. `athenspop` v1 mirrors the same conceptual split but keeps composite keys explicit: `households` unique on `household_id`, `persons` unique on `(household_id, person_id)`, and `trips` unique on `(household_id, person_id, trip_id)`.
- Row-independent processing: ActivitySim emphasizes that most household/person/tour/trip choices are independent by row group and can be vectorized or sliced. `athenspop` should process diary chains independently after validation, which supports deterministic testing, future chunking, and clearer diagnostics.
- Vectorized dataframe boundaries: ActivitySim treats pandas/NumPy vectorization as essential for performance. `athenspop` should validate and normalize dataframes in bulk where readability remains high, then switch to simple validated model objects for method code.
- Stable random streams: ActivitySim uses repeatable random streams at household/person granularity. `athenspop` v1 should expose deterministic seeds for scheduling and generation, and future work should derive per-diary random streams from stable diary keys rather than global mutable randomness.
- Time-window feasibility: ActivitySim person time windows represent available and occupied periods. `athenspop` does not need the full timetable machinery for v1, but its scheduler should represent feasible alternatives explicitly enough that departure-window scheduling and future probabilistic scheduling can share internals.
- Probabilistic trip scheduling: ActivitySim assigns trip departure periods from probability tables conditioned by purpose, direction, tour hour, and trip order, retrying until a feasible set is found or applying a configured fallback. `athenspop` v1 should keep the paper's uniform sampling and preserve only a small private departure-choice seam, so probability-table and logit samplers can be added later without making v1 a generic scheduling framework.
- Diagnostics and tracing: ActivitySim has substantial tracing and pipeline output. `athenspop` should keep diagnostics smaller and friendlier: validation reports, scheduling diagnostics, output manifests, stage counts, and profile notes.
- PopulationSim survey-weighting posture: PopulationSim is not a travel diary scheduler, but it is relevant because it treats household/person tables, seed samples, controls, configuration, output summaries, and validation reports as first-class reproducibility artifacts. `athenspop` should copy that discipline for paper inputs and outputs: explicit source inventories, stage counts, validation summaries, and friendly notebook/docs outputs for non-experts.
- PopulationSim validation posture: PopulationSim validates synthetic population outputs against controls using summary differences, average percentage difference, standard deviation, RMSE, and plots. `athenspop` should not add those exact statistics to v1 scheduling, but the paper reproduction should similarly emit compact stage summaries and diagnostic tables rather than relying on hidden notebook state.
- PopulationSim output posture: PopulationSim writes synthetic households and persons as explicit CSV outputs with configurable identifiers and selected attributes. `athenspop` should mirror that transparency for canonical paper outputs by writing scheduled trips, diary summaries, sequence arrays, clustering labels, and diagnostics as named artifacts with documented provenance.
- PopulationSim expression posture: PopulationSim control expressions are vectorized pandas-style expressions over seed household/person tables. `athenspop` should not expose expression-driven configuration in v1, but validators and example preprocessing should stay dataframe-native and vectorized where that keeps the code clearer.
- Future overlap rule: before adding any activity-based travel-model feature now or later, first inspect ActivitySim's matching docs and source for the algorithm, mathematics, table assumptions, validation pattern, and failure handling, then record whether `athenspop` mimics the idea, adapts code with attribution, or deliberately keeps a smaller local implementation.

## Concepts Not To Copy For V1

- Do not import ActivitySim as a runtime dependency for v1.
- Do not import PopulationSim as a runtime dependency for v1.
- Do not copy ActivitySim's configuration-heavy pipeline, injection system, model registry, or CLI.
- Do not copy PopulationSim's population-synthesis algorithms, IPF/IPU/entropy balancing/list balancing/integerization machinery, or geography-control framework; they solve population expansion and survey weighting, not diary scheduling or sequence clustering.
- Do not introduce tour-level abstractions unless the paper reproduction requires them.
- Do not add multiprocessing before profile evidence shows it is needed; ActivitySim itself keeps single-process development conceptually dominant and uses multiprocessing as an execution layer.
- Do not use ActivitySim terminology in the undergraduate-facing API when simpler terms are clearer.

## License And Code Copy Rule

ActivitySim and PopulationSim are BSD-3-Clause licensed. Copying code is allowed only if the copied portion is smaller and clearer than reimplementation, attribution and license obligations are recorded, and local tests prove that the adapted code preserves `athenspop` semantics. The default is to adapt algorithms and ideas, not code.

## V1 Decisions

- Keep `athenspop.validation` as the boundary gate and use its validated output as the source of truth for model construction.
- Keep the public scheduling API simple: `schedule_once(...)` for one realization and `generate_schedules(...)` for repeated stochastic realizations.
- Implement the paper-uniform scheduler first, with only a minimal private helper boundary that can later host ActivitySim-like probability tables or logit choice.
- Keep sequence analysis, transition-cost construction, optimal matching, and clustering governed by `CSuM2026`, TraMineR/Sequenzo evidence, and local fixtures rather than ActivitySim.
- Keep the Athens example outputs PopulationSim-like in discipline: every source, conversion count, validation report, scheduling diagnostic, sequence array, distance matrix, cluster table, and figure-preparation artifact should have an explicit path and provenance record.
