# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Validate sequences for analysis and visualization internals."""

import collections.abc


def materialize_equal_length_sequences(
    sequences: collections.abc.Sequence[collections.abc.Sequence[str]],
) -> tuple[tuple[str, ...], ...]:
    """Materialize and validate non-empty equal-length state sequences."""
    materialized = materialize_sequences(sequences)
    sequence_length = len(materialized[0])
    if any(len(sequence) != sequence_length for sequence in materialized):
        raise ValueError("All state sequences must have the same length.")
    return materialized


def materialize_sequences(
    sequences: collections.abc.Sequence[collections.abc.Sequence[str]],
) -> tuple[tuple[str, ...], ...]:
    """Materialize and validate non-empty symbolic state sequences."""
    materialized = tuple(tuple(sequence) for sequence in sequences)
    if not materialized:
        raise ValueError("At least one state sequence is required.")
    for sequence in materialized:
        if not sequence:
            raise ValueError("State sequences must contain at least one state.")
        if any(not isinstance(state, str) or not state.strip() for state in sequence):
            raise TypeError("Every sequence state must be a non-empty string.")
    return materialized
