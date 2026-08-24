# Comprehensive pivot audit and implementation plan

**Status:** audit complete; implementation not started

**Audit date:** 2026-08-24

**Repository baseline:** `d593f8d` (`Checkpoint interrupted generic pivot`)

**Branch:** `integrate-generic-pivot-20260619`

**Remote baseline:** pushed to `origin/integrate-generic-pivot-20260619`

## Executive decision

The reusable library is a credible generic implementation of travel-diary validation, stochastic scheduling, sequence construction, optimal-matching dissimilarity, and average-linkage clustering. Its current tests support many local contracts.

The repository is not ready to ship as a reproduction of the attached paper. The current Athens artifacts pass their 86-check validator but do not reproduce the paper's clustering or demographic analysis. The release must preserve and distinguish two claims:

1. **Archived-result reproduction:** the historical realization and published paper outputs, validated against an independent paper oracle.
2. **Refactored reanalysis:** the corrected generic pipeline and any intentionally changed realization, with differences and regenerated interpretations disclosed.

Neither surface should be removed. They must not share an ambiguous “reproduction” label.

Public release is also conditional on documented redistribution authority for the survey and derived routing resources. The present MIT software license does not establish that authority.

## Scope and method

This audit covered the complete tracked repository, production source, generic tests, Athens tests and example code, the checked-in paper and LaTeX sources, generated full artifacts, packaging, Sphinx documentation, and all refactor plans under `.claude` and `docs/plans`.

No refactor was performed. The only repository mutation before the audit was the authorized checkpoint commit. Read-only probes and generated ignored build/test artifacts were permitted.

### Prescribed review execution

| Order | Review | Scope | Exact role | Model and effort | Result |
|---:|---|---|---|---|---|
| 1 | Plinth Methods | whole repository | `plinth_methods` | `gpt-5.6-sol`, high | Completed |
| 2 | Plinth Methods | `src` | `plinth_methods` | `gpt-5.6-sol`, high | Completed |
| 3 | Plinth Methods | all tests | `plinth_methods` | `gpt-5.6-sol`, high | Completed |
| 4 | Plinth Code | whole repository | `plinth_code` | `gpt-5.6-sol`, high | Completed |
| 5 | Plinth Code | `src` | `plinth_code` | `gpt-5.6-sol`, high | Completed |
| 6 | Plinth Code | all tests | `plinth_code` | `gpt-5.6-sol`, high | Completed |
| 7 | Ponytail debt | whole repository, full | main audit | full | Completed; no markers |
| 8 | Ponytail audit | whole repository, full | main audit | full | Completed |
| 9 | Ponytail debt | whole repository, ultra | main audit | ultra | Completed; no markers |
| 10 | Ponytail audit | whole repository, ultra | main audit | ultra | Completed |

The Plinth plugin was locally patched and reinstalled before review because its role profiles named an unsupported model. The installed `plinth_methods`, `plinth_code`, and `plinth_claims` profiles were verified as `gpt-5.6-sol`, high reasoning, and read-only. A direct exact-role smoke task succeeded. No fallback role or model was used.

No separate Plinth Claims pass was necessary: the two consequential parity failures were independently reproduced by the repository Methods, tests Methods, repository Code, and tests Code reviews, using the paper sources and retained historical artifacts.

### Direct validation observations

| Gate or probe | Observation | Interpretation |
|---|---|---|
| `uv run pytest -q -p no:cacheprovider` | 170 passed: 134 generic and 36 Athens tests | Useful internal consistency evidence, not paper parity |
| `uv run ruff check .` | Passed | Current lint configuration only |
| `uv run ty check` | Passed | Current type-check configuration only |
| Sphinx warning-clean HTML build | Passed | Athens walkthrough is absent from the built graph |
| `uv run ruff format --check .` | Failed; nine test files would change | Current release record is stale |
| `uv build` and isolated wheel import | Passed | Generic wheel is importable |
| Full Athens artifact validation | 86 checks passed | Validator is insufficient for scientific parity |

## Repository map and purpose

| Surface | Purpose | Current condition |
|---|---|---|
| `src/athenspop` | Generic validated survey model, scheduler, sequence analysis, clustering, and optional visualization | Broadly coherent; material boundary defects remain |
| `examples/athens` | Paper-specific input conversion, routing, imputation, method rules, demographics, figures, and reproduction writer | Maintained but scientifically divergent from the paper |
| `tests` | Generic contracts and repository architecture checks | Strong local coverage; several meta-tests duplicate tools or overclaim portability |
| `examples/athens/tests` | Fast Athens smoke and method checks | Does not gate full paper reproduction |
| `docs` | Sphinx concepts, guides, API, development notes, design evidence, and plans | Generic docs build; Athens notebook-like material is outside the toctree |
| `CSuM2026.pdf` and `CSuM2026.zip` | Primary scientific authority and source manuscript | Hashes match the recorded contract |
| `examples/athens/data` | Survey and routing inputs | Required for full analysis; runtime provenance and redistribution authority unresolved |

The intended architecture is sound: generic computation belongs in `src/athenspop`; Athens-specific mappings, data access, method choices, and artifact writing belong in `examples/athens`.

## Authorities and decision hierarchy

1. The checked-in paper PDF, manuscript sources, and equations govern claims of paper reproduction.
2. Explicit user requirements govern the refactor outcome and feature preservation.
3. Still-binding commitments from the existing plans govern functionality. Historical implementation prescriptions may be superseded when they conflict with stronger evidence or the current request.
4. The Google Python Style Guide governs Python style. PEP 8 fills gaps. Refactoring.Guru is a supplementary refactoring catalog, not a mandate to add patterns.
5. The live `aef-embeddings` baseline uses Python 3.12+, pytest importlib mode, Ruff rules `E`, `W`, `F`, `I`, and `UP`, and ty with default configuration.

References:

- <https://raw.githubusercontent.com/DimitrisMantas/aef-embeddings/main/pyproject.toml>
- <https://google.github.io/styleguide/pyguide.html>
- <https://peps.python.org/pep-0008/>
- <https://refactoring.guru/refactoring/catalog>

This document becomes the execution plan once accepted. Existing plans remain evidence until their still-binding feature commitments are migrated and checked off here; only then may redundant historical plans be removed.

## Aggregated Plinth findings

The following list deduplicates all six Plinth reports. Severity reflects release consequence, not implementation size.

### Release blockers

#### F01 — Current clustering is not the published clustering

The paper reports ordered Figure 3 leaf sizes `5, 1, 13, 83, 3, 89, 8, 101, 207, 2`, with normalized heights `.61, 0, .26, .58, .54, .50, .39, .55, .45, .46`. Historical arrays recoverable from `19751af^` reproduce them under average linkage and optimal leaf ordering.

The current artifacts report sizes `91, 3, 80, 14, 14, 70, 29, 205, 5, 1`. The sorted multisets differ, so relabeling cannot reconcile them. Only 5 of 512 current state-sequence rows exactly match their historical counterparts. Current and historical dissimilarity maxima are `184.02691458160282` and `188.1507639519005`; the maximum elementwise difference is about `113.34`.

**Evidence:** `examples/athens/reproduce.py`, `examples/athens/smoke.py`, current ignored full artifacts, paper Figure 3, and historical artifacts at `19751af^`.

**Resolution:** restore an explicit historical realization profile and gate it against a small independent oracle containing input hashes, state-sequence hash, dissimilarity invariants, linkage invariants, ordered cluster sizes/heights, and partition-invariant membership. Label changed output as reanalysis.

#### F02 — Artifact validation can certify a scientifically different result

`validate_athens_artifacts` checks paths, selected counts, shapes, and broad properties but not the published state sequences, distance values, linkage contents, cluster memberships, Figure 3 sizes/heights, or cross-artifact cluster identity. It never validates the content of `cluster_summaries.csv` and derives some expected values from the output manifest being tested.

Documented but unenforced invariants include 1,466 scheduled trips with positive integer timing; 3,179 partitioning episodes; 231 non-self transitions; 1,296 symmetric bounded substitution-cost rows with zero diagonal; dissimilarity bounds; valid linkage; ten unique paper clusters; 10, 244, and 3,841 summary rows; demographic counts; and meaningful SVG content.

**Resolution:** map every output-manifest acceptance row to a mechanical check. Use an independent paper oracle for reproduction-only values. Add content-corruption tests by artifact category and a separately marked full fixed-data release test.

#### F03 — Tabular and displayed cluster identifiers are different namespaces

Flat labels come from SciPy `fcluster`; displayed cut leaves receive independent left-to-right labels. In the current output, displayed clusters 1–10 correspond to flat labels `10, 1, 2, 3, 4, 5, 6, 7, 8, 9`. No mapping is emitted.

**Evidence:** `src/athenspop/clustering/hierarchical.py:133-156`, `:343-375`, `:579-619`; `src/athenspop/visualization/dendrogram.py`; `examples/athens/reproduce.py:523-538`.

**Resolution:** make the exact-k cut partition the single authority and derive both exported labels and displayed leaves from it. Export one canonical presented-cluster ID and validate referential consistency.

#### F04 — Demographic reproduction implements a different analysis

The paper uses 461 complete cases, decade age bins, and the four strongest bias-corrected Cramér's V associations: employment–income `.457`, age–employment `.452`, education–employment `.410`, and education–income `.392`.

Current code uses `18–24`, `25–34`, and later bins; substitutes gender–car ownership for education–employment; and exports only counts and shares. The test imports the same incorrect pair constant used by the implementation.

**Evidence:** `examples/athens/demographics.py:28-130`, `examples/athens/tests/test_demographics.py:3-29`, paper Figure 2, and retained notebook source. Independent computation with the retained bins reproduced `0.457309`, `0.452141`, `0.410252`, and `0.392168`.

**Resolution:** implement the documented bias-corrected statistic, restore paper bins, select or validate the published pairs, export the values, and test against an independent fixture.

#### F05 — Data provenance and redistribution authority are unresolved

Runtime verification covers the manuscript but not the raw survey, routing matrix, zone encoder, or conversion policy. No data license, consent/ethics statement, data-availability statement, or explicit redistribution authority was found for the tracked survey and derived routing resources.

**Resolution:** record and verify all computation-driving hashes plus code revision, lock identity, RNG family, seeds, and policies. Before public release, document authority for each resource or omit non-redistributable inputs from published artifacts and provide an acquisition/verification procedure.

### High-priority scientific and integration findings

#### F06 — The nominal 15-state paper alphabet is collapsed too early

Input conversion maps `service` to `other` and `taxi` to `car`, so unreduced sequences contain 13 rather than 15 categories. The raw source contains 9 service and 52 taxi trips.

**Resolution:** preserve all paper categories through canonical trips and unreduced descriptive sequences. Apply service/taxi reduction only in the optimal-matching cost branch. Document any legacy 13-state deviation.

#### F07 — Random realization provenance changed materially

The retained workflow used NumPy `default_rng(seed=0)`; the current workflow uses Python `Random` and seed 2026 for scheduling and return-home imputation. The output manifest does not record the RNG family or policy.

**Resolution:** restore the historical RNG contract for reproduction and record RNG family, seed, sampling interval, and imputation policy in every manifest. Keep the current corrected policy under the reanalysis profile. Require multi-seed sensitivity only for claims of stability or behavioral generalization.

#### F08 — The one-diary exclusion is stronger than retained evidence

The paper reports one completely infeasible diary. Current documentation identifies person 549 and equates a strict non-finite transit sample with temporal infeasibility. The generic finite-mean policy schedules all 513 diaries.

**Resolution:** recover durable evidence linking diary 549 to the paper exclusion. Otherwise call it a missing-routing-data exclusion and distinguish it from temporal infeasibility.

#### F09 — Return-home imputation evidence is inadequate

The existing one-point empirical fixture cannot test inverse-transform sampling, truncation by minimum activity duration, purpose strata, seed behavior, last-mode preservation, exemptions, missing strata, travel-time failures, or imputation-induced infeasibility. Current code samples absolute return departure seconds by previous purpose; the paper describes sampling a valid activity duration.

**Resolution:** settle the method from the manuscript/legacy code, then add a hand-computable multi-point fixture covering the listed branches. The full gate must retain the expected 124 imputed returns and downstream oracle.

#### F10 — Construction-time travel-time callables are discarded for window trips

`SurveyDataset.from_dataframes(..., travel_time_function=...)` accepts the callable, but the dataset does not retain it and window trips remain unresolved. `schedule_once(dataset)` then reports `missing_travel_time_function` unless the caller supplies the callable again.

**Resolution:** retain the construction-time resolver as the dataset default; keep the scheduler argument only as an explicit override. Test the documented one-call workflow.

#### F11 — Reverse bounds omit final-trip arrival feasibility

The final trip's latest departure is not reduced by its travel duration. A feasible `[0, 86400]` one-trip window with 100-second duration can sample 86,302 and be rejected even though departures through 86,300 are feasible.

**Resolution:** constrain each latest departure by the permitted arrival horizon, including callable bisection and both after-window policies. Add fixed and callable regressions.

#### F12 — Callable resolution can invalidate a previously trusted chain

Validation checks overlap before deterministic concrete-departure travel times are resolved. Later resolution can create overlapping trips without revalidation.

**Resolution:** resolve deterministic concrete-departure callables once before final chain validation, persist the result, and test callable-created overlap.

#### F13 — Optional invalid table types escape report-based validation

`persons=42` and `households=42` correctly register `table_not_dataframe`, then crash on unconditional `.copy()`.

**Resolution:** copy and inspect optional tables only after the shape check succeeds. Return one table-level issue without an implementation exception.

#### F14 — Duplicate dataframe index labels corrupt rows and diagnostics

Label-based mutation and selection make two distinct rows indexed `[0, 0]` produce false duplicate-key errors and indistinguishable diagnostics.

**Resolution:** use private positional row identities throughout normalization and validation; preserve original labels only as context. An explicit unique-index input contract is acceptable only if documented and rejected before mutation.

#### F15 — The two cluster-cut APIs disagree at tied linkage heights

SciPy `maxclust` returns at most `k`; the displayed tree performs an exact top-down cut. Four equidistant observations requested at `k=2` yield one flat cluster and two displayed leaves.

**Resolution:** use the existing exact top-down partition as the single exact-k operation for both APIs. Add a tied-height partition-equality regression.

#### F16 — Metadata column normalization can lose values

Distinct labels `1` and `"1"` pass validation, then collide when converted to string dictionary keys.

**Resolution:** require unique string column names, or detect post-normalization collisions before model construction.

#### F17 — A non-callable value can authorize callable timing

Pattern detection checks only `travel_time_function is not None`; `42` passes validation and later raises incidental `TypeError`.

**Resolution:** validate `callable(...)` at the boundary and emit a normal diagnostic.

#### F18 — Generic activity and travel labels can collide

The default travel label is the raw mode, while activity labels are raw purposes. Equal strings merge both domains in state occupancy. Athens avoids this with `trip_`; the generic contract does not.

**Resolution:** namespace the default travel label while preserving custom labelers, or enforce a documented disjoint-alphabet precondition.

### Medium-priority correctness and evidence findings

#### F19 — The generic clock defaults to Athens 04:00

Public conversion helpers silently use `"04:00"`. Non-Athens callers can shift an entire day without an error.

**Resolution:** use civil midnight as the generic default or require the origin explicitly. The Athens adapter must pass 04:00.

#### F20 — Clock conversion accepts fractional and missing temporal scalars

Python microseconds and pandas nanoseconds are truncated; `pd.NaT` returns floating `nan` despite an integer contract.

**Resolution:** reject missing and non-whole-second temporal scalars. Cover Python and pandas inputs.

#### F21 — Overlapping clock source/target mappings are order-dependent

`convert_clock_columns` reads later sources from an already-mutated result. Swapping `start` and `end` corrupts the second conversion.

**Resolution:** read all source series from the immutable input snapshot and reject duplicate targets.

#### F22 — Dissimilarity validation uses an unsuitable relative tolerance

`np.allclose` accepts materially contradictory large off-diagonal values and a nonzero diagonal; `squareform(checks=False)` then silently selects one triangle.

**Resolution:** declare an absolute tolerance tied to the numeric contract and validate before disabling downstream checks. Add accept/reject boundary cases.

#### F23 — Callable exception policy is unresolved

Scheduling converts selected arithmetic, lookup, and value errors into diary diagnostics, while `RuntimeError` aborts the batch and model construction propagates all callable failures.

**Resolution:** document one public taxonomy. Contain expected backend/data failures per diary; propagate programming and process-control errors. Test both sides.

#### F24 — Average-linkage selection evidence is not retained

Direct reconstruction supports average linkage: historical cophenetic correlations are single `.493`, complete `.693`, average `.748`, weighted `.564`; current values are `.504`, `.630`, `.751`, `.663`.

**Resolution:** retain a deterministic paper-dataset comparison table or release test. Do not add a generalized selection framework.

#### F25 — Several paper-specific tests are self-derived or incomplete

Missing independent known answers include travel-time interpolation at a midpoint and midnight wrap; vocabulary closure across conversion, reduction, and routing; a pinned TraMineR comparison; and proof that uniform scheduling calls an established integer draw over the exact interval.

**Resolution:** add the smallest independent fixture for each claim. Use a fake RNG only where it proves the exact draw boundary.

#### F26 — Maintained example failure behavior is mostly untested

Missing cases include absent wide columns, malformed cells and durations, malformed routing resources, missing demographic columns, infeasible pipelines, and corrupt artifact content.

**Resolution:** add one focused invalid-input test for each maintained trust boundary, or mark a helper internal and route external calls through a tested boundary.

#### F27 — The portability test overclaims named-survey compatibility

All named survey families use the same synthetic canonical tables; only prefixes, metadata names, and timing patterns differ.

**Resolution:** rename the test to canonical-schema/timing-pattern portability. Claim a named survey only after an independently sourced adapter fixture exists.

#### F28 — Release evidence and executable gates disagree

Release notes report 65 generic tests and a passing format gate. The actual suite has 134 generic tests, 36 Athens tests, and nine unformatted test files. Testing docs say bare pytest excludes Athens tests while `pyproject.toml` includes them.

**Resolution:** make one root release command authoritative, align configuration and docs, and regenerate dated evidence only from the final revision.

#### F29 — Notebook-like Athens documentation is outside Sphinx

`examples/athens/docs/athens_walkthrough.md` is useful but outside the Sphinx source tree and toctree. `nbmake` is installed although no notebook exists.

**Resolution:** make `docs/examples/athens/` the canonical MyST notebook-like narrative, link it from the toctree, and execute a fast path using the same functions. Keep the 512-diary run as a release-only command. Do not add `.ipynb` files or a notebook runner unless executable notebooks become an explicit requirement.

#### F30 — The sdist exposes non-runnable examples and tests

The source distribution includes tests and Athens example code while excluding their required data and paper sources.

**Resolution:** publish a minimal generic sdist and wheel. Keep full reproduction checkout-only and state that clearly. Repository examples and tests remain maintained; they are not removed.

## Explicitly supported or clean areas

- Manuscript PDF/ZIP and selected member hashes match the recorded contract.
- The 04:00 day, 24-hour window, 15-minute bins, and four paper demand periods agree with the paper.
- Episode partitioning, maximum-overlap assignment, and earliest-start tie breaking are coherent.
- Athens state reduction equations, self-transition exclusion, conditional transition probabilities, and `2 - P(j|i) - P(i|j)` costs match the manuscript when applied at the proper stage.
- Generalized Wagner–Fischer optimal matching and symmetric pairwise construction are coherent for supplied costs.
- Average linkage is correctly applied to precomputed dissimilarities and is empirically supported among the retained candidates.
- Boundary validation followed by immutable trusted models is a defensible architecture.
- `schedule_once` and `generate_schedules` have a useful semantic separation.
- Matplotlib remains an optional leaf dependency and is not imported by `import athenspop`.
- No material leakage, train/test contamination, inappropriate predictive evaluation, or basis for stronger behavioral claims was found. The workflow is descriptive and unsupervised.
- The paper's stated limitations remain appropriate: representativeness, small trip counts, timing uncertainty, imperfect substitution semantics, absent external cluster validation, and incomplete sensitivity analysis.

## Ponytail debt and over-engineering audit

### Debt ledger

Both full and ultra scans found zero comments matching `(#|//) ponytail:`. There is no recorded Ponytail debt.

### Full-mode findings

| Rank | Target | Simplification | Preserved behavior |
|---:|---|---|---|
| 1 | `pyproject.toml` | Remove unused `nbmake` and `pytest-cov` development dependencies | Built MyST docs and all requested gates remain |
| 2 | Ruff and ty configuration | Replace `select = ["ALL"]`, broad ignores, and per-file exception matrices with Ruff defaults plus `extend-select = ["E", "W", "F", "I", "UP"]`; remove custom ty settings | Requested AEF/Google baseline and ty defaults |
| 3 | `tests/test_repository_contracts.py` | Delete custom AST/tokenize checks for line width, `Final` syntax, unique aliases/constants, exact pytest configuration, bytecode tracking, and the redundant static plotting-import check | Keep runtime import isolation, package contents, and material dependency/layer checks |
| 4 | `examples/athens/reproduce.py` | Delete the `_json_value` identity helper and consolidate the three repeated artifact-name/path registries into one source of truth | All artifact names, outputs, diagnostics, and semantic checks |
| 5 | sdist configuration | Ship only the self-contained generic source distribution instead of incomplete tests/examples | Repository tests and reproduction workflow remain available from a checkout |

Conservative full-mode saving: two direct development dependencies and about 220–320 lines of configuration, meta-tests, and duplicated registry plumbing. Correctness and scientific acceptance checks may add lines elsewhere; those are not eligible for simplification.

### Ultra-mode additions

| Rank | Target | Simplification | Evidence |
|---:|---|---|---|
| 1 | Historical plans | After migrating every still-binding feature and decision into this plan and final docs, delete four superseded plans | 1,190 lines; history remains in Git |
| 2 | `tests/example_data/shp_zones` | Delete the unreferenced shapefile fixture set | No current code, test, doc, or plan reference; 539,139 bytes |
| 3 | `.claude/settings.local.json` | Stop tracking machine-local tool permissions and ignore the path | Not a product or repository contract |
| 4 | Notebook tooling | Use MyST narrative pages and the existing Python smoke path; do not introduce notebook files, kernels, or execution plugins | Meets “notebook-like” documentation requirement with the current Sphinx stack |
| 5 | Public clustering implementation | Reuse the existing exact top-down partition for labels and display instead of adding another clustering abstraction | Fixes F03/F15 with one authority |

Ultra-mode saving after commitment migration: approximately 1,450–1,700 maintained text lines, two dependencies, one local settings file, and 539,139 bytes of unused fixtures. This estimate excludes required tests and validation, so the final repository's net line change is intentionally not predicted.

### Deliberately retained complexity

- Trust-boundary validation and diagnostic aggregation remain; Ponytail does not simplify away input validation.
- The paper-specific workflow remains separate from the generic library.
- The custom temporal dendrogram remains because its state-distribution panels are an existing feature not supplied directly by SciPy or Matplotlib.
- `schedule_once` and `generate_schedules` remain separate because their semantics differ.
- Full paper reproduction remains a distinct slow release gate; it is not folded into every fast test run.

## Target tooling and style contract

Use the following minimal policy:

```toml
[tool.pytest.ini_options]
addopts = ["--import-mode=importlib"]
testpaths = ["tests", "examples/athens/tests"]

[tool.ruff]
target-version = "py312"
line-length = 80
src = ["src", "tests", "examples"]

[tool.ruff.lint]
extend-select = ["E", "W", "F", "I", "UP"]
```

Do not add a `[tool.ty]` section unless a demonstrated project-specific defect requires one; the requested contract is ty defaults. Apply Google Python style to source and tests, use PEP 8 only where Google is silent, and use Refactoring.Guru only to name a demonstrated code smell or established refactoring. Do not introduce design patterns speculatively.

Ruff and ty must cover source, tests, examples, and `docs/conf.py`. Suppressions must be narrow, local, and justified by the adjacent code; a repository-wide ignore is not an acceptable substitute for correction.

## Concrete implementation plan

The phases are ordered by evidence dependency. Each phase must preserve all existing and documented functionality.

### Phase 0 — Freeze release claims and resolve distribution authority

**Work**

1. Add explicit “paper reproduction” and “refactored reanalysis” terminology to the README, Athens docs, commands, manifests, and output directories.
2. Make archived-result reproduction the gate for claims tied to published Figures 2 and 3.
3. Record the owner decision and evidence for survey/routing redistribution. If authority is unavailable, keep full inputs checkout-local or externally acquired and publish only verification hashes/instructions.
4. Record whether diary 549 is a temporal-infeasibility exclusion or a routing-missingness exclusion.

**Acceptance**

- No document calls a divergent reanalysis an exact reproduction.
- Every shipped data resource has provenance, authority, and availability text.
- Release cannot proceed while either decision is unresolved.

**Findings closed:** F01, F05, F08.

### Phase 1 — Establish independent scientific oracles and provenance

**Work**

1. Create one small versioned paper-oracle manifest derived from the manuscript and retained historical artifacts. Include source hashes, input hashes, algorithm/profile identity, RNG family/seed, expected row counts and shapes, state-sequence hash, dissimilarity bounds/hash, linkage invariants, ordered paper cluster sizes/heights, partition-invariant membership hash, demographic pairs/statistics, and expected exclusions.
2. Verify raw survey, routing NPZ, zone encoder, routing manifest, manuscript, conversion-policy revision, lockfile, and code revision before full execution.
3. Add a `full_reproduction` pytest marker or explicit release command. Keep it out of the ordinary fast test run.
4. Add artifact-content mutation tests that prove each validator category fails on corruption.

**Acceptance**

- Current divergent artifacts fail the paper-reproduction validator.
- Retained historical artifacts pass it.
- A changed input, RNG policy, cluster mapping, or demographic statistic fails with a specific diagnostic.

**Findings closed:** F01–F05, F07, F24.

### Phase 2 — Restore Athens paper parity and retain reanalysis

**Work**

1. Preserve all 15 paper categories through canonical conversion and unreduced outputs; reduce only the cost branch.
2. Restore the historical scheduling and imputation realization contract for the reproduction profile, including RNG and seed.
3. Resolve return-home sampling as activity-duration versus absolute-departure sampling from the manuscript and legacy implementation.
4. Restore decade age bins, bias-corrected Cramér's V, the four paper pairs, and statistic-bearing outputs.
5. Make one exact-k partition assign canonical presented cluster IDs across labels, summaries, distributions, dendrogram data, SVG, and narrative.
6. Persist the candidate-linkage cophenetic table as paper-specific evidence.
7. Retain the current corrected behavior as a separately named reanalysis profile and regenerate its interpretations from its own outputs.

**Acceptance**

- Reproduction matches the complete Phase 1 oracle.
- Reanalysis is deterministic under its recorded profile and never borrows paper cluster interpretations without evidence.
- Both profiles exercise the same generic library APIs; paper-specific choices remain under `examples/athens`.

**Findings closed:** F01, F03, F04, F06–F09, F24–F25.

### Phase 3 — Repair generic trust boundaries and scheduling

**Work packages**

1. **Dataframe identity and type safety:** fix optional-table copying, use positional row identities, reject normalized metadata collisions, and validate callable inputs.
2. **Travel-time lifecycle:** retain the dataset resolver, resolve concrete departures before final chain validation, define exception policy, and permit explicit scheduler override.
3. **Feasible bounds:** include arrival-horizon constraints for every final and intermediate trip under fixed and callable timing and both observation-window policies.
4. **Clock IO:** use a generic origin contract, reject fractional/missing values, snapshot source columns, and reject target collisions.
5. **Clustering:** make exact-k partitioning authoritative and use a declared absolute dissimilarity tolerance.
6. **Sequence labels:** prevent activity/travel alphabet collision by default while preserving custom labels.

**Acceptance**

- Every direct probe described in F10–F23 has one focused regression.
- Validation returns domain diagnostics rather than incidental pandas/Python errors.
- The root suite passes under Ruff and ty without broad suppressions.
- Athens paper-oracle output is unchanged except where Phase 2 deliberately restores it.

**Findings closed:** F10–F23.

### Phase 4 — Make tests measure claims rather than implementations

**Work**

1. Replace implementation-imported expected constants with independent fixtures.
2. Add midpoint/midnight interpolation, vocabulary closure, pinned TraMineR, exact uniform-draw, multi-point imputation, and invalid-input fixtures.
3. Rename synthetic portability tests to the exact generic contract they establish.
4. Keep fast smoke tests small; move 512-diary parity to the explicit release gate.
5. Delete redundant meta-tests listed by Ponytail. Keep runtime optional-import isolation, package-content checks, and material source-boundary checks.

**Acceptance**

- Mutating each scientific invariant causes an independent test failure.
- Test names do not claim support for datasets or methods absent from fixtures.
- Default collection remains generic plus maintained Athens fast tests and is documented accurately.

**Findings closed:** F02, F09, F25–F28.

### Phase 5 — Integrate notebook-like Sphinx documentation

**Work**

1. Move the maintained Athens narrative into `docs/examples/athens/` as canonical MyST pages covering inputs, validation, scheduling, imputation, sequence construction, distance, clustering, demographics, artifacts, reproduction, and reanalysis.
2. Add the pages to `docs/index.md`. Link from `examples/athens/README.md` rather than maintaining a second narrative.
3. Use ordinary fenced Python and recorded output blocks. Reuse the tested smoke functions; do not duplicate pipeline code in documentation.
4. Document the full release command, expected runtime/resources, output profiles, paper deviations, provenance, and data availability.
5. Run a fast documentation code path in tests and a warning-clean Sphinx build. Do not execute the 512-diary optimal-matching workflow during normal docs builds.

**Acceptance**

- The built navigation contains the complete Athens walkthrough.
- Every code-bearing step routes through maintained functions exercised by tests.
- `nbmake` is absent unless actual executable notebooks are later requested.

**Findings closed:** F29.

### Phase 6 — Simplify configuration, plans, fixtures, and packaging

**Work**

1. Apply the target Ruff/pytest/ty contract and format the entire maintained Python surface.
2. Remove unused `nbmake` and `pytest-cov`; keep Matplotlib as the visualization extra and test dependency.
3. Consolidate artifact registries and delete identity/duplicate helpers without weakening validation.
4. Remove the unreferenced shapefile fixture and tracked local Claude settings.
5. After checking every commitment against this plan, remove superseded plans; Git preserves their history.
6. Build a minimal generic sdist/wheel. Keep repository-only examples, data, paper sources, and full tests out of the published distribution unless made self-contained and licensed.

**Acceptance**

- Ruff configuration has no broad `ALL` selection or blanket example ignore list.
- Ty runs with defaults.
- The formatter check passes.
- Sdist and wheel contents match their documented purpose and install in isolation.
- No existing or planned feature disappeared during cleanup.

**Findings closed:** F28, F30 and all Ponytail findings.

### Phase 7 — Final release validation and ship

Run from a clean checkout and fresh Python 3.12 environment:

```text
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -q
uv run sphinx-build -W -b html docs docs/_build/html
uv run pytest -q -m full_reproduction
uv build
```

Then:

1. Inspect sdist and wheel contents.
2. Install the wheel in an isolated environment and import the root package without Matplotlib.
3. Run the public quickstart and Athens smoke path from documented commands.
4. Run full reproduction from verified inputs and archive its manifest, validator report, environment identity, and checksums.
5. Confirm the reanalysis profile produces separately named outputs and documentation.
6. Regenerate release-readiness evidence from the exact release commit.
7. Tag and push only after all blockers are closed.

## Release gate matrix

| Gate | Fast CI | Full release | Blocking condition |
|---|:---:|:---:|---|
| Ruff lint and format | Yes | Yes | Any maintained Python failure |
| Ty defaults | Yes | Yes | Any type error |
| Generic tests | Yes | Yes | Any failure |
| Athens smoke tests | Yes | Yes | Any failure |
| Sphinx `-W` | Yes | Yes | Warning or missing Athens navigation |
| Package build/install/import | Optional | Yes | Wrong contents or failed isolated import |
| Input provenance | No | Yes | Hash or identity mismatch |
| Paper oracle | No | Yes | Any Figure 2/3, sequence, distance, linkage, or exclusion mismatch |
| Reanalysis manifest | No | Yes | Unrecorded policy or reproduction-label ambiguity |
| Data authority | No | Yes | Missing provenance or redistribution decision |

## Owner decisions required before implementation can ship

1. Provide or identify the survey and routing-resource redistribution authority, or approve an acquisition-only public release surface.
2. Confirm the retained historical workflow is the authoritative implementation oracle for exact reproduction where the manuscript is underspecified.
3. Provide any surviving evidence for the paper's one-diary infeasibility classification. Without it, the documentation will use the narrower routing-missingness description.

These decisions do not block implementation of generic correctness fixes, documentation integration, or tooling cleanup. They do block an unqualified public paper-reproduction release.
