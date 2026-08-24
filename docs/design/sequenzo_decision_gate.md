# Sequence Distance Dependency Decision

The project keeps its local transition-cost and optimal-matching implementations. The manuscript excludes self-transitions from both the numerator and denominator of transition probabilities. TraMineR's standard transition-rate denominator includes every valid source-state position, including self-transitions, so its built-in rule is not the Athens method.

## Pinned External Evidence

The comparison is pinned to the official CRAN archive artifact `TraMineR_2.2-12.tar.gz`, published 29 June 2025:

- Artifact URL: `https://cran.r-project.org/src/contrib/Archive/TraMineR/TraMineR_2.2-12.tar.gz`
- Artifact SHA256: `6463D32C937AF84413A01D77140D3961C69AD03383EBC90C0058609B85297A30`
- Member: `TraMineR/R/seqtrate.R`
- Member SHA256: `956E533B799A78C959BDF1D2689912626F7D8B03CAF8DB15A3791318E3FBC8A9`

In the pinned source, the denominator `PA` counts positions where the source state occurs and the lagged target is valid. The destination-specific numerator `PAB` is then divided by `PA`. The executable fixture `test_athens_transition_denominator_differs_from_traminer` records the resulting distinction:

- For `A, A, B, A, A, C`, the Athens rule gives `P(B|A) = 0.5`; the pinned TraMineR rule gives `0.25`.
- The corresponding symmetric substitution cost `c(A, B)` is `0.5` under the Athens rule and `0.75` under the pinned TraMineR rule.

## Decision

Adding TraMineR or Sequenzo would not replace the paper-specific cost rule. Sequenzo remains a possible acceleration path only if a measured performance requirement justifies the dependency and a custom-cost parity test passes on fixtures and the full Athens workload. Until then, the current local implementation is smaller and preserves the required semantics.
