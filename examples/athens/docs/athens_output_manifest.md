# Athens migrated reanalysis output contract

`uv run python -m examples.athens.reproduce` writes and validates `examples/athens/output/reanalysis`. These outputs are a migrated reanalysis, not an end-to-end reproduction of the paper result reference.

## Provenance

| Artifact | Acceptance rule |
| --- | --- |
| `source_hashes.json` | Manuscript PDF/ZIP and selected ZIP members match the fixed hashes. The 513-row survey, routing matrix and zone encoder match their fixed hashes. The report records the lockfile hash, Git revision, tracked-worktree state, Python version and core package versions. |
| `input_stage_report.json` | Reports 513 raw diaries, 1,347 canonical trips, 513 persons and 513 households for the reanalysis. |
| `manifest.json` | Uses workflow `athens_migrated_reanalysis` and claim status `migrated_reanalysis_not_end_to_end_reproduction`; records the time origin, window, interval, activity-duration policy, routing fallback, category counts, linkage choice, RNG families, seeds, stream boundaries and SHA256 identity of every other artifact. |

The upstream data are excluded from source distributions but are already present in the public Git repository and its pushed integration branch. Their redistribution authority remains unresolved; the software-only distribution boundary does not undo that exposure.

## Canonical and scheduled data

| Artifact | Acceptance rule |
| --- | --- |
| `data/trips.csv` | Required canonical columns, explicit chain order and one supported timing pattern per row. Canonical categories preserve 7 purposes and 8 modes. |
| `data/persons.csv`, `data/households.csv` | Canonical keys remain joinable to trips. Demographic completeness is evaluated against all 513 persons, independently of scheduling exclusions. |
| `validation_report.json` | No hard input errors. |
| `scheduling_diagnostics.json` | 513 attempted diaries, 512 scheduled diaries and only `household_id=549; person_id=549` excluded by strict routing lookup. |
| `scheduled_trips.csv` | Concrete integer departures and arrivals, positive movement durations, and complete provenance for all 124 activity-duration-imputed return-home trips. Of these, 43 begin after the 24-hour horizon and 4 cross it; the manifest records both counts. |
| `diary_summary.csv` | Exactly one row per scheduled diary in the same order as every row-indexed numerical artifact. |
| `episodes.csv` | Episodes partition `[0, 86400]` for each scheduled diary without gaps or overlaps. |

## Sequence and distance evidence

| Artifact | Acceptance rule |
| --- | --- |
| `state_sequences.npy` | Shape `(512, 96)` and the observed 15-state paper alphabet: 7 activities plus 8 namespaced travel modes. |
| `compound_state_sequences.npy` | Shape `(512, 96)` and all 36 reduced state-period labels. |
| `transition_counts.csv` | Counts only non-self transitions. |
| `substitution_costs.csv` | Symmetric, zero diagonal, bounded in `[0, 2]`, with indel cost 1 supplied to optimal matching. |
| `dissimilarity_matrix.npy` | Shape `(512, 512)`, finite, symmetric within absolute tolerance `1e-12`, and zero diagonal within the same tolerance. |

The slow validator reconstructs state sequences from persisted episodes, compound sequences from persisted raw sequences, transition and cost tables from compound sequences, the complete distance matrix from compound sequences, and the linkage and cluster distributions from their persisted upstream artifacts. It also checks every artifact against the SHA256 inventory in `manifest.json`.

## Clustering evidence

| Artifact | Acceptance rule |
| --- | --- |
| `linkage_method_comparison.csv` | Contains `single`, `complete`, `average` and `weighted` cophenetic correlations computed without optimal ordering; average is strictly highest among those four candidates. |
| `linkage_average.npy` | Average linkage with optimal leaf ordering and shape `(511, 4)`. |
| `cluster_labels.csv` | 512 ordered diary keys and canonical left-to-right IDs 1–10 derived from the same exact ten-leaf cut used by the visualization. |
| `cluster_summaries.csv` | IDs, sizes and shares are recomputed from `cluster_labels.csv`; sizes sum to 512. |
| `cluster_state_distribution.csv`, `cluster_time_distribution.csv` | Use exactly the same cluster-ID namespace and cover every cluster. |
| `dendrogram_layout.json`, `figures/dendrogram.svg` | Leaf indices equal the linkage leaf order; leaf labels refer to the same ordered diary keys. The SVG is semantic output, not a byte-identical publication figure. |

## Demographic evidence

| Artifact | Acceptance rule |
| --- | --- |
| `demographics/complete_records.csv` | 461 records complete across gender, age, education, employment, income and car ownership from the original 513-person table. |
| `demographics/demographic_associations.csv` | All 15 unique off-diagonal pairs, ranked by Bergsma bias-corrected Cramér’s V using decade age bins and `chi2_contingency(..., correction=False)`. |
| `demographics/bivariate_demographics.csv` | The four highest pairs and values match the literal paper reference: employment–income, age–employment, education–employment and education–income. |
| `demographics/marginal_demographics.csv` and SVG figures | Counts for each marginal variable sum to 461; the bivariate SVG displays the selected association values. |

## Reference comparison

`validate_paper_result_reference(...)` is intentionally separate from `validate_athens_artifacts(...)`. It validates retained numerical identity and clustering invariants and, when `demographic_associations_path` is supplied, the four literal demographic associations in the reference. The reanalysis passes its own cross-artifact contract and fails the exact paper-reference hashes. That failure is expected and prevents a scientifically different result from being mislabeled as a reproduction.
