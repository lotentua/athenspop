# Generic Source Stop Condition

This note records the narrowing decision for the generic library pivot started from backup commit `19751af`.

## Outcome

The package source is complete enough when the same family of library primitives can support an Athens diary-clustering notebook plus UK NTS/PAM, US NHTS, French ENTD/EMP, ActivitySim-style, and PopulationSim-adjacent examples without adding survey-specific package code.
Dataset-specific work may appear in examples: source-file reading, survey-code decoding, purpose and mode grouping, weights, vehicle tables, return-home conventions, location mappings, travel-time resources, figure styling, and artifact writing.
Shared, repeated, or cheaply generalizable mechanics should live in source when they are realistic across examples and easier to maintain once than repeatedly in examples.

## Evidence

The PAM UK example reads household, person, and trip tables into pandas, renames arbitrary National Travel Survey columns into a small diary schema, maps source-specific activity and mode codes, loads those dataframes into PAM, validates/fixes plans, and then inspects activity and mode classes. The documented common fields include person id, household id, sequence, household zone, origin zone, destination zone, purpose, mode, start time, end time, and frequency. That is a dataframe-to-diary boundary, not a UK-code-specific library boundary.
The companion matrix in `docs/design/travel_survey_genericity_checks.md` records the same rule for NHTS, ENTD/EMP, ActivitySim, and PopulationSim-style examples.

## Source Invariants

- Source APIs accept and return Python objects: pandas dataframes, immutable model objects, NumPy arrays, SciPy linkage matrices, Matplotlib figures, and plain Python containers.
- Source does not read or write CSV, SVG, XML, notebooks, or paper artifacts.
- Source does not define default activity purposes, default travel modes, home-purpose labels, recreation exceptions, paper period labels, UK NTS mappings, Athens mappings, or MATSim/PAM adapters.
- Source validation checks structural and timing validity needed to build trusted diaries; methodology-specific warnings live in examples or caller code.
- Source sequence construction exposes generic activity-state and travel-state naming hooks instead of hard-coding `home` or `trip_`.
- Source clustering returns linkage, flat labels, cut-tree structure, and summary dataframes.
- Source visualization may return generic Matplotlib figures when the figure type is shared across examples; examples still own state grouping, labels, colors, and saving files.

## First Loop

1. Remove source CSV and SVG writer APIs from imports, docs, and tests.
2. Remove default-purpose/default-mode warnings and return-home conventions from validation.
3. Remove source return-home imputation only if the Athens example already has a reusable example-level imputer; otherwise keep imputation as a caller-configured primitive without `home` baked in.
4. Keep generic departure-window scheduling, because both Athens and UK-style survey workflows may need conversion from reported times to concrete diaries.
5. Generalize sequence state construction so callers choose initial activity labels and travel-state labels.
6. Keep tests focused on generic contracts and move paper-specific assertions to example tests.

## Review Findings

- High: Hard-coded source categories make the package fail the UK/PAM stop condition because UK examples use `shop`, `visit`, `escort`, `medical`, `pt`, and other labels outside Athens defaults.
- High: File-format helpers in source contradict the Python-object-only boundary and make examples look like production artifact runners.
- Medium: Return-home imputation and missing-return-home warnings encode a paper-specific diary-completion assumption unless parameterized as a generic imputation primitive.
- Medium: A file-writing SVG renderer with presentation, color palettes, and mode/purpose grouping is an example concern, but the shared cut-dendrogram temporal-distribution figure primitive is generic enough to keep in source as a Matplotlib object-returning helper.
