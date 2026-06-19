# Profiling Notes

This note records the rudimentary profile-guided optimization pass requested for v1. The goal is to identify whether sequencing, distance-matrix construction, clustering, or dendrogram generation blocks a non-expert workflow, not to optimize prematurely.

## Current Gate

The v1 release threshold in the plan is 10 minutes wall-clock time and 4 GB peak memory on an ordinary laptop for the full paper recreation excluding optional notebook rendering. The current normal full artifact command is well below that runtime threshold.

## Normal Full Command Timing

`uv run python -m examples.paper.reproduce` completed successfully in 41.776 seconds and validated the full artifact set under `examples/paper/output/full`.

## Stage Timing Probe

The staged timing probe mirrors the maintained full workflow without `cProfile` or `tracemalloc` instrumentation. It does not replace the full artifact command; it explains where the runtime goes.

| Stage | Seconds |
| --- | ---: |
| Load canonical paper inputs | 0.080 |
| Validate canonical dataframes | 1.091 |
| Build `SurveyDataset` model | 1.209 |
| Schedule reported trips | 1.178 |
| Impute return-home trips | 0.019 |
| Compound sequence construction | 0.177 |
| Optimal-matching dissimilarity matrix | 36.466 |
| Average-linkage clustering | 0.003 |
| Extract 10 cluster labels | 0.000 |
| Cluster summary tables | 0.011 |
| Episode table and raw state sequences | 0.166 |
| Transition and substitution tables | 0.008 |
| Cluster temporal distribution | 0.017 |
| Dendrogram layout | 0.005 |
| Demographic summaries | 0.056 |
| Write SVG figures | 0.100 |
| Total staged workflow | 40.592 |

The dominant cost is the local optimal-matching distance computation, which accounts for about 90% of ordinary runtime in the staged probe. Scheduling, validation, model construction, sequence construction, clustering, dendrogram layout, and SVG generation are not current blockers.

## Instrumented Profile

The `cProfile` plus `tracemalloc` full artifact run completed in 161.544 seconds with a 52.616 MB peak Python allocation trace. The instrumentation slows the NumPy-batched dynamic-programming loop substantially, so the instrumented wall time should not be used as the user-facing runtime estimate.

The top cumulative functions in the instrumented run were `examples.paper.reproduce.write_full_artifacts`, `examples.paper_reproduction_smoke.run_pipeline`, `examples.paper.method.paper_dissimilarity_matrix`, `athenspop.sequence.distance.dissimilarity_matrix`, and `athenspop.sequence.distance._batch_optimal_matching_dissimilarities`.

## Decision

No v1 optimization beyond the current integer-state encoding and NumPy-batched dynamic programming is justified. The next performance work, if needed later, should compare the local OM implementation against Sequenzo with a custom substitution matrix, no normalization, indel `1`, identical label ordering, and exact pairwise parity on fixtures and the full paper dataset before changing the default.
