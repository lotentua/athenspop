# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Compute optimal-matching dissimilarities for state sequences."""

import math
from collections.abc import Mapping, Sequence
from typing import cast

import numpy as np

import athenspop._sequences
import athenspop.types

#: Dense substitution-cost matrix indexed by encoded states.
type CostMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
#: Encoded target sequences used by the vectorized recurrence.
type EncodedTargetMatrix = np.ndarray[tuple[int, int], np.dtype[np.int64]]
#: Dissimilarities from one source to each target sequence.
type DistanceVector = np.ndarray[tuple[int], np.dtype[np.float64]]


def optimal_matching_dissimilarity(
    first: Sequence[str],
    second: Sequence[str],
    *,
    substitution_cost: Mapping[tuple[str, str], float],
    indel_cost: float = 1.0,
) -> float:
    """Compute Wagner-Fischer optimal-matching dissimilarity for two sequences.

    Args:
        first: First symbolic state sequence.
        second: Second symbolic state sequence.
        substitution_cost: Pairwise substitution costs keyed
            by `(source_state, target_state)`.
        indel_cost: Positive insertion and deletion cost.

    Returns:
        Optimal-matching dissimilarity between the two sequences.

    Raises:
        TypeError: If either sequence contains a state that is not a non-empty string.
        ValueError: If either sequence is empty,
            `indel_cost` is not positive, or a required substitution cost is missing.
    """
    indel_cost = _validate_positive_cost(indel_cost, name="indel_cost")
    first, second = athenspop._sequences.materialize_sequences((first, second))
    rows = len(first) + 1
    columns = len(second) + 1
    previous = [index * indel_cost for index in range(columns)]
    for row_index in range(1, rows):
        current = [row_index * indel_cost, *([0.0] * (columns - 1))]
        source = first[row_index - 1]
        for column_index in range(1, columns):
            target = second[column_index - 1]
            delete_cost = previous[column_index] + indel_cost
            insert_cost = current[column_index - 1] + indel_cost
            substitute_cost = previous[column_index - 1] + _lookup_substitution_cost(
                source, target, substitution_cost
            )
            current[column_index] = min(delete_cost, insert_cost, substitute_cost)
        previous = current
    return previous[-1]


def dissimilarity_matrix(
    sequences: Sequence[Sequence[str]],
    *,
    substitution_cost: Mapping[tuple[str, str], float],
    indel_cost: float = 1.0,
) -> athenspop.types.DissimilarityMatrix:
    """Compute a symmetric pairwise optimal-matching dissimilarity matrix.

    Args:
        sequences: Symbolic state sequences to compare pairwise.
        substitution_cost: Symmetric pairwise substitution
            costs keyed by source and target state.
        indel_cost: Positive insertion and deletion cost.

    Returns:
        Square float64 matrix whose `[i, j]` entry is the
        optimal-matching dissimilarity between sequence `i` and sequence `j`.

    Raises:
        TypeError: If any sequence contains a state that is not a non-empty string.
        ValueError: If no non-empty sequence is
            provided, `indel_cost` is not positive, a required substitution cost is
            missing, or a cost differs from its reverse direction.

    Notes:
        The implementation encodes sequences once and batches same-length targets to
        reduce repeated Python-loop overhead.
    """
    indel_cost = _validate_positive_cost(indel_cost, name="indel_cost")
    materialized = athenspop._sequences.materialize_sequences(sequences)
    encoded_sequences, cost_matrix = _encode_sequences(
        materialized, substitution_cost=substitution_cost
    )
    matrix = np.zeros((len(materialized), len(materialized)), dtype=np.float64)
    for row_index, first in enumerate(encoded_sequences):
        target_indices_by_length: dict[int, list[int]] = {}
        for target_index in range(row_index + 1, len(encoded_sequences)):
            target_indices_by_length.setdefault(
                len(encoded_sequences[target_index]), []
            ).append(target_index)
        for target_indices in target_indices_by_length.values():
            targets = cast(
                "EncodedTargetMatrix",
                np.asarray(
                    [
                        encoded_sequences[target_index]
                        for target_index in target_indices
                    ],
                    dtype=np.int64,
                ),
            )
            distances = _batch_optimal_matching_dissimilarities(
                first, targets, cost_matrix=cost_matrix, indel_cost=indel_cost
            )
            for target_index, distance in zip(
                target_indices, distances.tolist(), strict=True
            ):
                matrix[row_index, target_index] = distance
                matrix[target_index, row_index] = distance
    return matrix


def _lookup_substitution_cost(
    source: str,
    target: str,
    substitution_cost: Mapping[tuple[str, str], float],
) -> float:
    """Return zero for identical states or look up the explicit substitution cost."""
    if source == target:
        return 0.0
    try:
        return _validate_non_negative_cost(
            substitution_cost[(source, target)],
            name=f"substitution_cost[{source!r}, {target!r}]",
        )
    except KeyError as error:
        raise ValueError(
            f"The substitution cost for {source!r} -> {target!r} is missing."
        ) from error


def _encode_sequences(
    sequences: Sequence[Sequence[str]],
    *,
    substitution_cost: Mapping[tuple[str, str], float],
) -> tuple[tuple[tuple[int, ...], ...], CostMatrix]:
    """Encode sequences and build the corresponding dense cost matrix."""
    states = tuple(sorted({state for sequence in sequences for state in sequence}))
    _validate_symmetric_substitution_costs(states, substitution_cost)
    state_codes = {state: code for code, state in enumerate(states)}
    cost_matrix = np.zeros((len(states), len(states)), dtype=np.float64)
    for source in states:
        source_code = state_codes[source]
        for target in states:
            target_code = state_codes[target]
            cost_matrix[source_code, target_code] = _lookup_substitution_cost(
                source, target, substitution_cost
            )
    encoded_sequences = tuple(
        tuple(state_codes[state] for state in sequence) for sequence in sequences
    )
    return encoded_sequences, cast("CostMatrix", cost_matrix)


def _validate_symmetric_substitution_costs(
    states: Sequence[str], substitution_cost: Mapping[tuple[str, str], float]
) -> None:
    """Reject directed costs before building a symmetric dissimilarity matrix."""
    for source_index, source in enumerate(states):
        for target in states[source_index + 1 :]:
            forward_cost = _lookup_substitution_cost(source, target, substitution_cost)
            reverse_cost = _lookup_substitution_cost(target, source, substitution_cost)
            if not np.isclose(forward_cost, reverse_cost, rtol=1e-12, atol=1e-12):
                raise ValueError(
                    "`dissimilarity_matrix` requires symmetric substitution costs "
                    f"for clustering; got {forward_cost} for {source!r} -> "
                    f"{target!r} and {reverse_cost} for {target!r} -> {source!r}."
                )


def _validate_positive_cost(value: float, *, name: str) -> float:
    """Return a finite positive numeric cost."""
    if isinstance(value, bool) or not isinstance(
        value, int | float | np.integer | np.floating
    ):
        raise TypeError(f"`{name}` must be a finite positive number, got {value!r}.")

    cost = float(value)
    if not math.isfinite(cost) or cost <= 0.0:
        raise ValueError(f"`{name}` must be a finite positive number, got {value!r}.")

    return cost


def _validate_non_negative_cost(value: float, *, name: str) -> float:
    """Return a finite non-negative numeric cost."""
    if isinstance(value, bool) or not isinstance(
        value, int | float | np.integer | np.floating
    ):
        raise TypeError(
            f"`{name}` must be a finite non-negative number, got {value!r}."
        )

    cost = float(value)
    if not math.isfinite(cost) or cost < 0.0:
        raise ValueError(
            f"`{name}` must be a finite non-negative number, got {value!r}."
        )

    return cost


def _batch_optimal_matching_dissimilarities(
    first: Sequence[int],
    targets: EncodedTargetMatrix,
    *,
    cost_matrix: CostMatrix,
    indel_cost: float,
) -> DistanceVector:
    """Compute distances from one encoded sequence to equal-length targets."""
    batch_size = targets.shape[0]
    columns = targets.shape[1]
    previous = np.tile(
        np.arange(columns + 1, dtype=np.float64) * indel_cost,
        (batch_size, 1),
    )
    current = np.empty_like(previous)
    for row_index, source_code in enumerate(first, start=1):
        current[:, 0] = row_index * indel_cost
        for column_index in range(1, columns + 1):
            target_codes = targets[:, column_index - 1]
            delete_costs = previous[:, column_index] + indel_cost
            insert_costs = current[:, column_index - 1] + indel_cost
            substitute_costs = (
                previous[:, column_index - 1] + cost_matrix[source_code, target_codes]
            )
            current[:, column_index] = np.minimum(
                np.minimum(delete_costs, insert_costs), substitute_costs
            )
        previous, current = current, previous
    return cast("DistanceVector", previous[:, columns].copy())
