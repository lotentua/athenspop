# Sequence API

Sequence operations convert scheduled diaries into episodes and fixed-interval state tuples, then compare symbolic sequences with explicit optimal-matching costs.

```{eval-rst}
.. automodule:: athenspop.sequence.episodes
   :members: Episode, discretize_episodes, episodes_from_diary, overlap_duration,
             state_sequence_from_diary, trip_mode_state

.. automodule:: athenspop.sequence.distance
   :members: dissimilarity_matrix, optimal_matching_dissimilarity
```
