# CSuM2026 Athens Method Contract

This contract records the CSuM2026 example methodology for `athenspop`. The authoritative local sources are `CSuM2026.zip` and `CSuM2026.pdf`; package implementation may be refactored freely and kept generic, but the example workflow and release validation must preserve the behavior below unless this document is updated with evidence and tests.

## Source Provenance

- `CSuM2026.zip`: SHA256 `2EA15A9D1448FB29CFCDE5DA0C2BD3D515D52442EE558E41841138644A297841`.
- `CSuM2026.pdf`: SHA256 `5BC2AA37934F458B1E56BF8581F0A7FE7A156535AF59BD3FF98A0ED27BFACEE1`.
- Extraction command used for this contract: `Expand-Archive -LiteralPath CSuM2026.zip -DestinationPath $env:TEMP\athenspop-CSuM2026-source`.
- Source inventory: `main.tex` SHA256 `0C88CC332459B59FD0977B4D6C961547D32BA1DF6D240B53D54354D9B32161AE`; `methods.tex` SHA256 `59F7A9F030124BBB49A0D6545130AC852B84E742DD0683DA56CF6AB76A0CECC0`; `results.tex` SHA256 `58C80CF04493FB2F21F7E3998C3C05CA0CC6A5A3E7A5D7937E02CA4913ABDE8B`; `intro.tex` SHA256 `7E86656D9DF6FB5D96888D8953DD818F970CFC81CBD2C91EDAEB61097B519792`; `conclusion.tex` SHA256 `AF1C6C3D81001426071475C9E772475DE9C1AFA13425A6C53591C1543B8808C8`; `CSuM2026.bib` SHA256 `959845FCF78B5AC45DD714DF981C98B04479751B49AADD4B19B20E4128A2737B`.
- Figure source inventory: `figures/MarginalDistributions.pgf` SHA256 `395E505044F8C84E81C816E97061C883303BB17B0A1327C3EB341CCB17594AC8`; `figures/BivariateDistributions.pgf` SHA256 `1AF15D42D8CFB96536F6FBE06D81A34E01F308341E779BAB66653B929883E5AE`; `figures/Dendrogram.pdf` SHA256 `499D74210B23307725DF8BE07F6EB636DB6A29FDFEBDE79885D6883E6666EDA1`; `figures/Dendrogram.pgf` SHA256 `44C5211D0B2DE43E35B6AF8BE08CF505EDDD473CC0F9EB2B2C947EC82BA5D0B0`; `figures/Dendrogram.eps` SHA256 `272246A30AFA93D8F11DB8DE0487A9338535FE0A3EF0A4A1962E09D86E319BF3`.

## Reproduction Invariants

- Raw survey size: 513 travel diaries.
- Complete demographic records: 461 of 513 diaries.
- One diary is infeasible during scheduling and is discarded.
- Final scheduled sample size: 512 diaries.
- Observation window: `T = 86400` seconds, equivalent to 24 hours.
- Diary time-origin clock: `04:00`; diary second `0` is 04:00 and diary second `86400` is 04:00 on the following day.
- Discretization width: `delta_seconds = 900`, equivalent to 15 minutes.
- Sequence length: 96 bins.
- Original state alphabet: 7 activity purposes plus 8 travel modes, for 15 states.
- Compound state-period alphabet before reduction: 15 states times 4 periods, for 60 labels.
- Reduced state-period alphabet for cost construction: 3 activity groups plus 6 mode groups times 4 periods, for 36 labels.
- Indel cost for paper reproduction: scalar `gamma = 1`.
- Clustering method: agglomerative hierarchical clustering with average linkage on a precomputed dissimilarity matrix.
- Presented hierarchy: truncated dendrogram with the last 10 clusters shown as leaves.

## Survey Semantics

- Each diary records home zone, up to five trips on a typical workday, destination zone, destination purpose, travel mode, and reported departure-time interval.
- V1 canonical input must be converted to three long-form tables before model construction: required `trips`, optional `persons`, optional `households`.
- The first trip in a diary starts from the respondent home zone.
- Each later trip starts from the previous trip destination.
- Reported departure times in the source survey are intervals: six consecutive three-hour windows spanning 05:00 to 23:00 and one six-hour overnight window from 23:00 to 05:00.
- Concrete departure times in the paper are synthetic, not observed; they are sampled uniformly within reported intervals subject to chain feasibility and a 30-minute minimum activity duration.
- Travel times for car and public transit come from Google Routes API data collected on Thursday 22 May 2025 with two-hour sampling frequency over 00:00 to 24:00; other modes are scaled from car travel times by average speed ratios.
- Missing return-home trips are imputed when the final reported purpose is neither `home` nor `recreation`.
- Recreation activities may extend beyond the observation period.
- Diaries exceeding 24 hours are cropped to `[0, 86400]`.
- The single scheduling exclusion in the migrated legacy workflow is household/person `549`, trip `549_trip_2`, a train trip from zone `15` to zone `11` whose strict legacy routing lookup preserves a non-finite Google Routes transit sample. The generic package resolver may use finite-mean fallback for ordinary robust scheduling, but the paper artifact workflow uses strict missing-sample handling so the scheduling diagnostics reproduce the 512-diary analysis set.

## Episode And Sequence Contract

- A diary is converted into continuous episodes that partition `[0, 86400]` without gaps or overlaps.
- An episode is `(state, start_second, end_second)` with `0 <= start_second < end_second <= 86400`.
- Activity states come from destination purposes; travel states come from modes; activity and mode labels must be disjoint by construction.
- For the paper, each sequence bin is `[i * 900, (i + 1) * 900)` except the final bin, which includes the endpoint at 86400.
- The overlap duration between episode `k` and bin `i` is `max(0, min(beta_k, bin_end_i) - max(alpha_k, bin_start_i))`.
- The state assigned to a bin is the state with maximum total overlap duration.
- Ties are resolved by the earliest-starting overlapping episode.
- Period labels are assigned from the bin start second, not the clock time.
- Period 1 covers `[0, 10800)` and `[54000, 86400]`, corresponding to clock 04:00-07:00 and 19:00-04:00.
- Period 2 covers `[10800, 21600)`, corresponding to clock 07:00-10:00.
- Period 3 covers `[21600, 43200)`, corresponding to clock 10:00-16:00.
- Period 4 covers `[43200, 54000)`, corresponding to clock 16:00-19:00.

## Reduced Alphabet Contract

- Activity `home` remains `home`.
- Activities `education` and `work` become `rigid`.
- Activities `market`, `recreation`, `service`, and `other` become `flexible`; if the raw data has already merged `service` into `other`, this still maps to `flexible`.
- Mode `taxi` becomes `car`.
- Modes `bicycle` and `escooter` become `micromobility`.
- Modes `car`, `motorcycle`, `bus`, `train`, and `walk` remain separate.
- Compound labels must be encoded only after activity/mode reduction and period assignment are complete.

## Dissimilarity Contract

- Transition counting operates on reduced compound state-period sequences.
- Self-transitions are excluded from both numerator and denominator.
- For distinct states `s` and `s_prime`, `P(s_prime | s) = TransitionCount(s, s_prime) / sum_{u != s} TransitionCount(s, u)`.
- If a state has no non-self outgoing transitions, all outgoing transition probabilities from that state are zero for substitution-cost construction.
- Substitution cost is `0` on the diagonal.
- For `s != s_prime`, substitution cost is `c(s, s_prime) = 2 - P(s_prime | s) - P(s | s_prime)`.
- The substitution matrix must be symmetric and bounded in `[0, 2]`.
- The dissimilarity computation uses generalized Wagner-Fischer optimal matching with the paper substitution matrix and constant indel cost `1`.
- The output should be called a dissimilarity matrix unless a later proof or test establishes metric properties.

## Clustering Contract

- Average linkage is required for paper reproduction.
- Ward linkage is invalid for v1 paper reproduction because the paper does not assume Euclidean distances and explicitly selects average linkage.
- The release output must include cluster labels for the 10-cluster presentation, a linkage matrix or equivalent hierarchy, cophenetic diagnostic availability, and a dendrogram visualization with embedded temporal state distributions.
- Exact publication styling is not a v1 blocker, but the generated figure must preserve the interpretation of the hierarchy, leaf sizes, node state distributions, and root-normalized linkage distances.

## Historical Legacy Artifact Baseline

- Before the canonical cleanup, the removed legacy `examples/v1/res/survey/wide.csv` had 513 rows, 28 columns, and 513 unique `pid` values.
- Before the canonical cleanup, the removed legacy `examples/v1/res/survey/preprocessed.csv` had 513 rows, 33 columns, and 513 unique `pid` values.
- Before the canonical cleanup, the removed legacy `examples/v1/res/survey/long/trips.csv` had 1347 rows, 7 columns, and 513 unique `pid` values.
- Before the canonical cleanup, the removed legacy `examples/v1/state_sequences.npy` had shape `(512, 96)`, dtype `<U15`, and 13 unique labels.
- Before the canonical cleanup, the removed legacy `examples/v1/distance_matrix.npy` had shape `(512, 512)`, dtype `float64`, minimum `0.0`, and maximum `188.1507639519005`.
- The migrated routing resource `examples/athens/data/travel_time/routing.npz` has SHA256 `AD0D374DDC65E9ADE0EDE53041534041D8305FE06FCFA839AF7815082DACC5DC`; `examples/athens/data/travel_time/zone_encoder.json` has SHA256 `AED03BAC02F1FD0D56CEE0A8CA4589AABEBFC08CF336A3F98D047E5656949873`.
- These historical values are migration and regression-triage evidence only. The live examples surface is canonical and must regenerate inputs and outputs from the long-form API rather than trusting old notebooks, arrays, or wide-form files as authoritative.

## Release Acceptance Rules

- The paper reproduction command must verify the source hashes above before running.
- The preprocessing stage must report 513 raw diaries, 461 complete demographic records when demographic figures are regenerated, 1 strict-routing infeasible scheduled diary, and 512 final diaries.
- The sequence stage must report shape `(512, 96)` for the final paper state sequences.
- The cost stage must report a symmetric substitution matrix with zero diagonal, scalar indel `1`, and a dedicated self-transition exclusion fixture.
- The clustering stage must report average linkage and a 10-cluster presentation.
- The output manifest in `docs/design/athens_output_manifest.md` lists the required public artifacts and their v1 acceptance rules.
