# Sequences

Sequence analysis converts scheduled diaries into fixed-width labels that can be compared across people.

First, a scheduled diary becomes episodes: continuous intervals of activity or travel that partition the observation window.
Activity episodes use the previous destination purpose by default, and travel episodes use a caller-provided labeler or the raw mode label.

Second, the observation window is divided into equal-width bins.
Each bin receives the state with the largest overlap duration.
Ties use the earliest-starting episode so the rule is deterministic.

Third, sequences can be compared with optimal matching.
The caller supplies substitution costs, and the library supplies the dynamic-programming alignment and pairwise dissimilarity matrix.

The sequence layer does not choose a behavioral alphabet or derive substitution costs from a specific study.
Those are analysis decisions layered on top of the generic sequence functions.
