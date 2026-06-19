# CSuM2026 Output Manifest

This manifest lists the v1 paper-reproduction artifacts that must be generated or explicitly deferred. The command `uv run python -m examples.athens.reproduce` verifies the CSuM2026 PDF/ZIP source hashes, converts the migrated 513-diary wide source, uses the strict paper travel-time workflow for reported trips, records the one legacy routing infeasibility, imputes missing return-home trips with the paper empirical inverse-transform policy, writes the current computational artifact set under `examples/athens/output/full`, and validates the release-relevant counts, shapes, hashes, and manifest paths before returning successfully. The separate `write_smoke_artifacts(...)` helper keeps the checked-in three-diary smoke workflow available for fast tests.

## Reproduction Inputs

| Artifact | Target path | Deterministic inputs | Acceptance rule |
| --- | --- | --- | --- |
| Source hash report | `examples/athens/output/full/source_hashes.json` | `CSuM2026.zip`, `CSuM2026.pdf`, and key members inside `CSuM2026.zip` | SHA256 values match `examples/athens/docs/athens_method_contract.md`. |
| Migrated wide diary source | `examples/athens/data/raw_diaries_athens_wide.csv` | Legacy 513-row survey export migrated from the removed `examples/v1` surface | 513 rows and the expected CSuM-style wide columns; the converter test reports 1347 canonical trips. |
| Input stage report | `examples/athens/output/full/input_stage_report.json` | Canonical input conversion | Reports raw diary count, canonical trip count, person count, household count, source fixture or full source path, and whether the run is smoke or full paper data. |
| Canonical trips table | `examples/athens/output/full/data/trips.csv` | Legacy raw survey export plus documented preprocessing | Long-form table with required canonical columns and exactly one supported timing pattern per row. |
| Canonical persons table | `examples/athens/output/full/data/persons.csv` | Legacy raw survey export plus demographic mappings | Optional table with canonical keys; demographic completeness is reported separately when demographic figures are regenerated. |
| Canonical households table | `examples/athens/output/full/data/households.csv` | Legacy raw survey export plus home-zone extraction | Optional table keyed by `household_id`; v1 may use one household per respondent if the source has no true household grouping. |
| Travel-time resource manifest | `examples/athens/data/travel_time/travel_time_manifest.json` | Migrated Google Routes derived resources plus deterministic resolver | Records provenance, matrix units, SHA256 hashes, mode scaling policy, and deterministic lookup behavior. |

## Validation And Scheduling Outputs

| Artifact | Target path | Deterministic inputs | Acceptance rule |
| --- | --- | --- | --- |
| Validation report | `examples/athens/output/full/validation_report.json` | Canonical trips/persons/households | No hard validation errors; methodological warnings are expected only when listed in the report. |
| Scheduling diagnostics | `examples/athens/output/full/scheduling_diagnostics.json` | Canonical dataset, strict travel-time resolver, fixed seed | Reports 513 attempted diaries, one strict-routing infeasible diary `household_id=549; person_id=549`, 512 scheduled diaries, and no unexplained exclusions. |
| Scheduled trips | `examples/athens/output/full/scheduled_trips.csv` | Canonical dataset, strict travel-time resolver for reported trips, finite-mean resolver for synthetic return trips, fixed seed | All scheduled movement trips have integer `departure_second`, `arrival_second`, positive duration, `is_imputed_return_home`, `imputation_method`, and `observed_last_trip_id`; the full workflow validates 124 imputed return-home trips and complete provenance for imputed rows. |
| Scheduled diary summary | `examples/athens/output/full/diary_summary.csv` | Scheduled survey dataset | One row per scheduled diary with 512 rows and chain-level diagnostics. |

## Sequence And Distance Outputs

| Artifact | Target path | Deterministic inputs | Acceptance rule |
| --- | --- | --- | --- |
| Episode table | `examples/athens/output/full/episodes.csv` | Scheduled trips plus observation-window policy | Episodes partition `[0, 86400]` for every diary without gaps or overlaps. |
| State sequences | `examples/athens/output/full/state_sequences.npy` | Episode table, `delta_seconds = 900` | Shape `(512, 96)`; bin assignment follows maximum overlap with earliest-start tie breaking. |
| Compound state sequences | `examples/athens/output/full/compound_state_sequences.npy` | State sequences plus paper period mapping | Shape `(512, 96)`; labels combine reduced state and period. |
| Transition counts | `examples/athens/output/full/transition_counts.csv` | Reduced compound state sequences | Self-transitions excluded; fixture values match tests. |
| Substitution matrix | `examples/athens/output/full/substitution_costs.csv` | Transition counts | Symmetric, diagonal zero, values in `[0, 2]`, indel scalar recorded as `1`. |
| Dissimilarity matrix | `examples/athens/output/full/dissimilarity_matrix.npy` | Compound sequences, substitution matrix, indel `1` | Shape `(512, 512)`, symmetric, diagonal zero, and deterministic numerical bounds matching the baseline table below unless a method change is documented. |

## Clustering And Figure Outputs

| Artifact | Target path | Deterministic inputs | Acceptance rule |
| --- | --- | --- | --- |
| Linkage matrix | `examples/athens/output/full/linkage_average.npy` | Dissimilarity matrix | SciPy-compatible average-linkage hierarchy on the precomputed dissimilarity matrix. |
| Cluster labels | `examples/athens/output/full/cluster_labels.csv` | Linkage matrix | 512 rows with 10-cluster assignment and stable diary identifiers. |
| Cluster summaries | `examples/athens/output/full/cluster_summaries.csv` | Cluster labels, state sequences, respondent metadata | Cluster sizes and dominant state distributions are reported for interpretation. |
| Cluster temporal state distributions | `examples/athens/output/full/cluster_time_distribution.csv` | Cluster labels and unreduced state sequences | Contains purpose and mode state counts and shares for every cluster and 15-minute bin represented in the 512-diary sequence set. |
| Complete demographic records | `examples/athens/output/full/demographics/complete_records.csv` | Canonical persons table | Exactly 461 records complete across gender, age, education, employment status, monthly income, and car ownership. |
| Marginal demographic distributions | `examples/athens/output/full/demographics/marginal_demographics.csv` and `examples/athens/output/full/figures/marginal_demographics.svg` | Complete demographic records | Six marginal variables are reported; each variable's counts sum to 461. |
| Bivariate demographic distributions | `examples/athens/output/full/demographics/bivariate_demographics.csv` and `examples/athens/output/full/figures/bivariate_demographics.svg` | Complete demographic records | Reports the selected v1 pairs `gender` by `car_ownership`, `age_group` by `employment_status`, `education` by `monthly_income`, and `employment_status` by `monthly_income`. |
| Dendrogram figure | `examples/athens/output/full/figures/dendrogram.svg` | Linkage matrix, state sequences, selected cluster cut | Shows the cut average-linkage hierarchy with each displayed node replaced by activity-purpose and travel-mode temporal distributions; exact publication styling is not required. |

## Deterministic Baseline And Tolerances

These values are the current v1 artifact baseline from `uv run python -m examples.athens.reproduce` on 2026-06-19. Exact integer counts and array shapes should match exactly. Floating-point values should be compared with `rtol = 1e-9` and `atol = 1e-9` unless a dependency upgrade changes only harmless last-bit rounding and the change is recorded with a before/after validation note.

| Stage | Artifact or check | Current baseline | Release tolerance |
| --- | --- | --- | --- |
| Source conversion | Raw diaries, canonical trips, persons, households | `513`, `1347`, `513`, `513` | Exact match. |
| Validation | Hard validation errors | `0` | Exact match. |
| Scheduling | Attempted diaries, scheduled diaries, infeasible diary | `513`, `512`, `household_id=549; person_id=549` | Exact match. |
| Return-home imputation | Synthetic return-home trips | `124` | Exact match while the paper empirical imputation policy and source data are unchanged. |
| Scheduled trips | Rows and diary count | `1466` rows across `512` diaries | Exact match. |
| Diary summary | Rows | `512` | Exact match. |
| Episodes | Rows | `3179` | Exact match unless a documented episode-boundary bug fix changes the canonical interpretation. |
| State sequences | Shape and dtype | `(512, 96)`, string dtype | Exact shape; dtype may vary only among NumPy string dtypes. |
| Compound state sequences | Shape and dtype | `(512, 96)`, string dtype | Exact shape; dtype may vary only among NumPy string dtypes. |
| Transition counts | Non-self transition rows | `231` | Exact match while alphabet reduction and self-transition policy are unchanged. |
| Substitution costs | Matrix rows | `1296` | Exact match because the reduced compound alphabet has 36 labels. |
| Dissimilarity matrix | Shape, symmetry, diagonal, minimum, maximum | `(512, 512)`, symmetric, zero diagonal, min `0.0`, max `184.02691458160282` | Exact shape and structural checks; min/max within floating tolerance. |
| Linkage matrix | Shape | `(511, 4)` | Exact match. |
| Cluster labels | Rows and clusters | `512` rows, `10` clusters | Exact match for the deterministic average-linkage cut. |
| Cluster summaries | Rows | `10` | Exact match. |
| Cluster state distribution | Rows | `244` | Exact match unless cluster labels or state alphabet change with a documented method update. |
| Cluster temporal distribution | Rows and cluster-bin coverage | `3841` rows over `10 * 96` cluster-bin pairs | Exact cluster-bin coverage; row count exact while the state alphabet and labels are unchanged. |
| Complete demographic records | Rows | `461` | Exact match. |
| Marginal demographic summary | Rows | `22` | Exact match. |
| Bivariate demographic summary | Rows | `48` | Exact match for the selected four v1 pairings. |
| Generated SVG figures | Dendrogram, marginal demographics, bivariate demographics | Non-empty SVG files currently `1174175`, `5281`, and `7461` bytes | Non-empty SVG with required semantic inputs; byte-identical output is not required. |

## Explicitly Deferred Or Non-Blocking Outputs

- Exact PGF reproduction of the Springer figure files is deferred because public v1 documentation should prefer portable SVG or PNG generated by the canonical Python workflow.
- Exact pixel-level reproduction of `figures/Dendrogram.pdf` is deferred; v1 acceptance is based on hierarchy, cluster sizes, temporal state distributions, and interpretability.
- Full demographic sensitivity analysis is deferred; v1 must reproduce the reported marginal and selected bivariate summaries needed by the paper walkthrough.
- MATSim and PAM export files are deferred until after v1 paper reproduction is green.

## Full Reproduction Command

The documented command is `uv run python -m examples.athens.reproduce`. It writes full artifacts to `examples/athens/output/full`, verifies the CSuM2026 source hashes, loads the canonical paper inputs, reports 513 attempted diaries, records the single strict-routing infeasible diary, imputes 124 synthetic return-home trips, writes the 512-diary outputs listed above, and validates the generated artifact directory with `examples.athens.reproduce.validate_athens_artifacts(...)`.
