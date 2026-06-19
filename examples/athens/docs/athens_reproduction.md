# Athens Reproduction

The Athens example target is to reproduce the CSuM2026 paper from canonical long-form inputs. The current full command verifies the CSuM2026 source hashes, loads the migrated 513-diary wide source through the canonical converter, applies the strict paper routing policy to reported trips, records the one legacy routing exclusion, imputes missing return-home trips with the paper empirical inverse-transform policy, writes the 512-diary sequence and clustering artifacts, writes demographic summaries from the 461 complete records, writes a dendrogram SVG with temporal cluster state strips, records an output manifest, and validates the deterministic baseline listed in `examples/athens/docs/athens_output_manifest.md`.

The repository includes a small executable smoke example at `examples/athens/smoke.py`. It uses three in-memory canonical dataframes, runs validation, builds the internal model, schedules departure windows, constructs reduced compound state-period sequences, computes the paper-specific optimal-matching dissimilarity matrix, clusters with average linkage, and prepares no-plot dendrogram geometry.

Run it from the project root with:

```powershell
uv run python -m examples.athens.smoke
```

Use the importable function when you want the actual outputs:

```python
from examples.athens.smoke import run_example

outputs = run_example()

assert outputs.scheduled.diagnostics.scheduled_diaries == 3
assert outputs.dissimilarity_matrix.shape == (3, 3)
assert len(outputs.sequences[0]) == 96
```

This example is intentionally tiny. It is not evidence that the paper dataset has been reproduced; it is a maintained bridge that keeps the documentation, public APIs, and tests aligned while the full paper workflow evolves.

The full artifact-writing workflow is `examples/athens/reproduce.py`.

```powershell
uv run python -m examples.athens.reproduce
```

The default output directory is `examples/athens/output/full`, which is ignored by Git because it is generated. The command verifies `CSuM2026.pdf`, `CSuM2026.zip`, and the key LaTeX/figure members recorded in the method contract, converts the migrated 513-diary wide source into canonical long-form `trips`, `persons`, and `households`, applies the strict paper travel-time resolver to reported trips, records `household_id=549; person_id=549` as the single routing-infeasible diary, imputes 124 synthetic return-home trips using empirical return-departure sampling, writes `source_hashes.json`, `input_stage_report.json`, scheduling diagnostics, scheduled trips, episodes, sequences, transition counts, substitution costs, dissimilarity matrix, linkage matrix, cluster labels, cluster summaries, state distributions, dendrogram layout, and the manifest, then validates the generated artifact directory before returning successfully.

The migrated full wide diary source is `examples/athens/data/raw_diaries_athens_wide.csv`. The maintained converter loads it with `examples.athens.inputs.load_athens_wide_diaries()` and currently verifies 513 raw diaries, 1347 canonical trips, 513 person rows, and 513 household rows. With placeholder 900-second travel times and the paper cropping policy, all 513 diaries can be scheduled; this is a source-conversion and scheduler-boundary check, not yet the final paper result, because the paper reports one infeasible diary and 512 final scheduled diaries.

The migrated routing resources are in `examples/athens/data/travel_time/`, with provenance in `travel_time_manifest.json`. Load them with `examples.athens.travel_time.AthensTravelTimeResolver.from_files()` and pass the resolver as the canonical `travel_time_function` after calling `load_athens_wide_diaries(fixture_travel_time_seconds=None)`. The default resolver uses finite-mean fallback for missing routing samples and the generic scheduler realizes all 513 migrated source diaries with the deterministic resolver and observation-window cropping policy. The paper analysis-set scheduling path uses `AthensTravelTimeResolver.from_files(missing_sample_policy="strict")`, preserving the legacy non-finite Google Routes transit sample for person `549`, trip `549_trip_2`; this produces the 512 scheduled diaries used by the current computational artifacts and records the excluded diary in scheduling diagnostics.

The maintained artifact writer has two entry points. `python -m examples.athens.reproduce` writes and validates the current full computational paper artifacts under `examples/athens/output/full`. For fast tests or documentation smoke checks, call `examples.athens.reproduce.write_smoke_artifacts(Path("examples/athens/output/smoke"))`. The full workflow writes canonical tables, validation and scheduling reports, scheduled trips with `is_imputed_return_home`, `imputation_method`, and `observed_last_trip_id` provenance for synthetic return-home rows, demographic CSV/SVG outputs, episodes, state sequences, compound state sequences, transition counts, substitution costs, the OM dissimilarity matrix, average-linkage output, cluster labels, cluster summaries, state distributions, temporal cluster distributions, dendrogram geometry, a dendrogram SVG, source-hash reports, and a manifest. On the current development machine this full workflow completed in about 42 seconds, with most time spent in pairwise optimal matching.

The current full command proves the canonical long-form 512-diary analysis path, empirical return-home imputation stage, demographic summaries, dendrogram visualization, clustering artifact shape, deterministic computational baselines, and exported imputation provenance. Migration validation and profiling evidence are recorded in `docs/design/release_readiness.md` and `docs/design/profiling_notes.md`.

ActivitySim remains the reference to check before adding overlapping travel-model functionality. PopulationSim is the companion reference for reproducible survey table inputs, stage summaries, validation notebooks, and named output artifacts. Future table slicing, random streams, feasible alternative construction, diagnostics, output summaries, chunking, and probability/logit choice machinery should first be compared against the relevant ActivitySim or PopulationSim docs and source, then adapted into the smaller undergraduate-friendly `athenspop` interface only when the paper workflow needs it.
