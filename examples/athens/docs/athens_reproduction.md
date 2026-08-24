# Athens paper result and migrated reanalysis

The repository exposes two distinct evidence surfaces. They must not be conflated.

## Paper result reference

`examples/athens/paper_result_reference.json` identifies the numerical arrays retained at historical commit `75d1cd5ae186ece22c3f0f7eabb58c2a4659df0f`. It records exact file hashes, array shapes, the normalized average-linkage hash, all ten displayed cluster memberships, sizes and heights, the inferred ordered respondent-key hash, and the four reported demographic associations.

Reclustering the retained dissimilarity matrix reproduces the cluster sizes and two-decimal root-normalized heights shown in the paper. The reference is not an end-to-end reproduction: the migrated code does not regenerate those arrays, and the retained sequences contain 13 labels because the historical implementation merged `service` into `other` and `taxi` into `car` before sequence construction, although the manuscript describes 15 unreduced states.

Candidate retained arrays can be checked with:

```python
from examples.athens.reproduce import validate_paper_result_reference

validation = validate_paper_result_reference(
    state_sequences_path,
    dissimilarity_matrix_path,
    diary_summary_path,
    demographic_associations_path=demographic_associations_path,
)
validation.raise_if_invalid()
```

This proves reference identity only. End-to-end reproduction would require a clean revision to regenerate the reference arrays from hashed upstream inputs without reading those arrays.

## Migrated reanalysis

The maintained executable workflow is a migrated reanalysis. It preserves all seven purposes and eight modes through canonical input conversion, applies the documented reductions only in the cost-construction branch, computes all 15 demographic associations before selecting the reported top four, and records its current RNG and scheduling policies.

Run it from the repository root:

```powershell
uv run python -m examples.athens.reproduce
```

The command writes `examples/athens/output/reanalysis`, which is generated and ignored by Git. Before analysis, it verifies the manuscript, actual supplied survey, routing and zone-encoder hashes, and records the current lockfile hash. It also records the Git revision and dependency versions; converts 513 wide diaries into 1,347 canonical trips; records person 549 as a missing-routing-data exclusion; schedules 512 diaries; imputes 124 return-home trips from empirical activity durations; and writes the sequence, distance, clustering, demographic and visualization artifacts.

The routing encoder lacks six of the 36 survey zones. The manifest records the network-mean fallback and its affected zones, trips, diaries and imputed returns. This is a migrated-reanalysis limitation. It is not attributed to the paper method.

The output manifest uses `claim_status = migrated_reanalysis_not_end_to_end_reproduction`. Different RNG machinery, scheduling policy and pre-reduction sequencing mean its cluster result must be interpreted independently of the paper result reference.

`write_full_artifacts(...)` remains as a compatibility entry point and delegates to `write_reanalysis_artifacts(...)`. New code should use the latter name.

## Smoke workflow

The three-diary smoke workflow checks the public APIs without making a paper-result claim:

```powershell
uv run python -m examples.athens.smoke
```

For named smoke artifacts, call `write_smoke_artifacts(...)`. The default test suite exercises this path; the full reanalysis is a separate release gate because pairwise optimal matching is materially slower.

## Claim boundary

- “Paper result reference” means byte identity for retained arrays and agreement with the recorded clustering invariants. The respondent-key order is an explicitly labeled reconstruction inferred from retained historical evidence.
- “Migrated reanalysis” means a fresh run from the identified upstream inputs under the recorded software and policies.
- “End-to-end reproduction” is not currently claimed.
- Person 549 is described as a missing-routing-data exclusion. The retained evidence does not establish that this is the same condition the paper called complete temporal infeasibility.
