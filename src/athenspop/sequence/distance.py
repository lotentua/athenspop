"""Optimal-matching dissimilarities for symbolic state sequences."""

from collections.abc import Sequence
from typing import cast

import numpy as np

type DissimilarityMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type CostMatrix = np.ndarray[tuple[int, int], np.dtype[np.float64]]
type EncodedTargetMatrix = np.ndarray[tuple[int, int], np.dtype[np.int64]]
type DistanceVector = np.ndarray[tuple[int], np.dtype[np.float64]]


def optimal_matching_dissimilarity(
    first: Sequence[str],
    second: Sequence[str],
    *,
    substitution_cost: dict[tuple[str, str], float],
    indel_cost: float = 1.0,
) -> float:
    """Compute generalized Wagner-Fischer optimal-matching dissimilarity for two sequences.

    Args:
        first: First symbolic state sequence.
        second: Second symbolic state sequence.
        substitution_cost: Pairwise substitution costs keyed by `(source_state, target_state)`.
        indel_cost: Positive insertion/deletion cost.

    Returns:
        Optimal-matching dissimilarity between the two sequences.

    Raises:
        ValueError: If `indel_cost` is not positive or a required substitution cost is missing.
    """
    if indel_cost <= 0:
        raise ValueError(f"`indel_cost` must be positive, got {indel_cost}.")
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
            substitute_cost = previous[column_index - 1] + _lookup_substitution_cost(source, target, substitution_cost)
            current[column_index] = min(delete_cost, insert_cost, substitute_cost)
        previous = current
    return previous[-1]


def dissimilarity_matrix(
    sequences: Sequence[Sequence[str]],
    *,
    substitution_cost: dict[tuple[str, str], float],
    indel_cost: float = 1.0,
) -> DissimilarityMatrix:
    """Compute a symmetric pairwise optimal-matching dissimilarity matrix.

    Args:
        sequences: Symbolic state sequences to compare pairwise.
        substitution_cost: Pairwise substitution costs keyed by `(source_state, target_state)`.
        indel_cost: Positive insertion/deletion cost.

    Returns:
        Square float64 matrix whose `[i, j]` entry is the optimal-matching dissimilarity between sequence `i` and sequence `j`.

    Raises:
        ValueError: If `indel_cost` is not positive or a required substitution cost is missing.

    Notes:
        Sequences are encoded once and same-length targets are batched to reduce repeated Python-loop overhead.
    """
    if indel_cost <= 0:
        raise ValueError(f"`indel_cost` must be positive, got {indel_cost}.")
    materialized = tuple(tuple(sequence) for sequence in sequences)
    encoded_sequences, cost_matrix = _encode_sequences(materialized, substitution_cost=substitution_cost)
    matrix = np.zeros((len(materialized), len(materialized)), dtype=np.float64)
    for row_index, first in enumerate(encoded_sequences):
        target_indices_by_length: dict[int, list[int]] = {}
        for target_index in range(row_index + 1, len(encoded_sequences)):
            target_indices_by_length.setdefault(len(encoded_sequences[target_index]), []).append(target_index)
        for target_indices in target_indices_by_length.values():
            targets = cast(
                "EncodedTargetMatrix",
                np.asarray(
                    [encoded_sequences[target_index] for target_index in target_indices],
                    dtype=np.int64,
                ),
            )
            distances = _batch_optimal_matching_dissimilarities(first, targets, cost_matrix=cost_matrix, indel_cost=indel_cost)
            for target_index, distance in zip(target_indices, distances.tolist(), strict=True):
                matrix[row_index, target_index] = distance
                matrix[target_index, row_index] = distance
    return matrix


def _lookup_substitution_cost(source: str, target: str, substitution_cost: dict[tuple[str, str], float]) -> float:
    """Return zero for identical states or look up the explicit asymmetric substitution cost."""
    if source == target:
        return 0.0
    try:
        return substitution_cost[(source, target)]
    except KeyError as error:
        raise ValueError(f"Missing substitution cost for {source!r} -> {target!r}.") from error


def _encode_sequences(
    sequences: Sequence[Sequence[str]],
    *,
    substitution_cost: dict[tuple[str, str], float],
) -> tuple[tuple[tuple[int, ...], ...], CostMatrix]:
    """Encode string sequences as integer codes and build the corresponding dense substitution-cost matrix."""
    states = tuple(sorted({state for sequence in sequences for state in sequence}))
    state_codes = {state: code for code, state in enumerate(states)}
    cost_matrix = np.zeros((len(states), len(states)), dtype=np.float64)
    for source in states:
        source_code = state_codes[source]
        for target in states:
            target_code = state_codes[target]
            cost_matrix[source_code, target_code] = _lookup_substitution_cost(source, target, substitution_cost)
    encoded_sequences = tuple(tuple(state_codes[state] for state in sequence) for sequence in sequences)
    return encoded_sequences, cast("CostMatrix", cost_matrix)


def _batch_optimal_matching_dissimilarities(
    first: Sequence[int],
    targets: EncodedTargetMatrix,
    *,
    cost_matrix: CostMatrix,
    indel_cost: float,
) -> DistanceVector:
    """Compute optimal-matching distances from one encoded source sequence to a batch of equal-length targets."""
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
            substitute_costs = previous[:, column_index - 1] + cost_matrix[source_code, target_codes]
            current[:, column_index] = np.minimum(np.minimum(delete_costs, insert_costs), substitute_costs)
        previous, current = current, previous
    return cast("DistanceVector", previous[:, columns].copy())
