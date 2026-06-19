# Sequenzo And TraMineR Decision Gate

## Purpose

This note records the current v1 decision for sequence dissimilarities so the project does not accidentally drift from `CSuM2026.pdf` into standard TraMineR or Sequenzo `TRATE` semantics.

## Checked Sources

- `CSuM2026.zip` and `CSuM2026.pdf`, recorded in `docs/design/paper_method_contract.md`, are the v1 methodological authority.
- TraMineR `seqtrate` documentation defines transition rates as observed state-to-state transition probabilities and points to their use for optimal-matching substitution costs: https://traminer.unige.ch/doc/seqtrate.html
- The TraMineR `seqtrate` source computes the denominator for a source state from all positions where that source state appears before the lagged target position, so self transitions contribute to the denominator when present. The current fixture is derived from TraMineR 2.2-12 documentation/source as served by rdrr.io on 2026-06-18; release validation should replace this live-source citation with a CRAN tarball version/hash or an executed pinned TraMineR output before declaring v1 complete: https://rdrr.io/cran/TraMineR/src/R/seqtrate.R
- Sequenzo describes itself as a Python-native social sequence analysis package inspired by TraMineR and exposes `get_distance_matrix` for OM, OMspell, HAM, DHD, LCP, and related methods: https://github.com/Liang-Team/Sequenzo
- Sequenzo's `get_distance_matrix` documentation says OM supports `sm="TRATE"` or a user-provided square substitution-cost matrix, uses `indel="auto"` unless specified, can return full or condensed matrices, and uses compiled backends with unique-sequence compression: https://sequenzo.yuqi-liang.tech/zh/function-library/get-distance-matrix
- Sequenzo's current source validates custom substitution matrices for OM-like methods and routes string `TRATE` through its own substitution-cost construction rather than the paper-specific local function: https://raw.githubusercontent.com/Liang-Team/Sequenzo/main/sequenzo/dissimilarity_measures/get_distance_matrix.py and https://raw.githubusercontent.com/Liang-Team/Sequenzo/main/sequenzo/dissimilarity_measures/get_substitution_cost_matrix.py

## Current Decision

V1 keeps transition counting and substitution-cost construction local because the paper excludes self transitions from both the numerator and denominator, while TraMineR-style `seqtrate` includes self transitions in the denominator.

V1 keeps a transparent local optimal-matching implementation as the reference path until Sequenzo custom-matrix OM parity is proven on paper-shaped fixtures.

Sequenzo should not be added as a runtime dependency just to access built-in `TRATE`, because that would silently encode a different transition-probability denominator for the paper reproduction.

Sequenzo remains the preferred future acceleration candidate for distance computation if `get_distance_matrix(..., method="OM", sm=custom_matrix, indel=1, norm="none")` preserves labels, ordering, missing handling, full versus condensed output semantics, pairwise values, and performance on the paper dataset.

## Release Gate

- Keep an executable fixture where `("A", "A", "B", "A", "A", "C")` yields `P(B|A) = 0.5` under the paper rule and `P(B|A) = 0.25` under the TraMineR-style denominator.
- Keep an executable fixture where the same sequence yields paper substitution cost `c(A, B) = 0.5` and TraMineR-style cost `c(A, B) = 0.75`.
- Treat the current TraMineR-style expected values as pinned-source-derived constants, not as an installed TraMineR execution. Before v1 release, either run the same fixture against a pinned TraMineR package or store the exact pinned source artifact and hash used to derive the constants.
- Do not add a required Sequenzo executable fixture while Sequenzo is not a project dependency. If Sequenzo becomes an optional test dependency, add a skipped-when-unavailable fixture that records the Sequenzo version/source and demonstrates why built-in `TRATE` is not the v1 default.
- If Sequenzo is introduced, add parity tests that compare local OM and Sequenzo OM with a custom paper substitution matrix on several tiny fixtures and on a deterministic sample from the paper reproduction data.
- If Sequenzo is introduced, profile local OM versus Sequenzo OM on the full paper distance-matrix workload and record the result in the Phase 12 profiling notes before changing the default.
