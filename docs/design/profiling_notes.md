# Reanalysis Runtime Note

The stabilized migrated reanalysis completes below 2 minutes on the release-check machine. A precommit run on 24 August 2026 took 89.385 seconds, including input verification, scheduling, imputation, sequence construction, pairwise optimal-matching distances, clustering, demographics, figures, artifact writing, and the then-current 162-check contract. The final contract adds five canonical-data and independent-provenance checks, for 167 checks total.

The documented release threshold is 10 minutes on an ordinary laptop, so the measured run has substantial runtime margin. Peak memory was not remeasured for this revision and no current memory claim is made.

Pairwise optimal matching remains the expected hotspot because the workflow computes a symmetric 512 by 512 dissimilarity matrix. An earlier staged profile located about 90% of runtime there, and the current run does not indicate a release blocker. No additional optimization or dependency is justified without a measured regression or a stricter operating requirement.
