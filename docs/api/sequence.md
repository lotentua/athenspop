# Sequence API

Episode functions represent a concrete schedule over continuous time or fixed-width state bins. Distance functions compare symbolic sequences with caller-supplied optimal-matching costs.

Read [Sequences and clustering](../concepts/sequences.md) before choosing an interval width, state vocabulary, or edit-cost scheme.

```{eval-rst}
.. automodule:: athenspop.sequence.episodes
   :members: Episode, TravelStateLabeler, discretize_episodes,
             episodes_from_diary, overlap_duration, state_sequence_from_diary,
             trip_mode_state

.. automodule:: athenspop.sequence.distance
   :members: CostMatrix, DistanceVector, EncodedTargetMatrix,
             dissimilarity_matrix, optimal_matching_dissimilarity
```
