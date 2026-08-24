"""Shared sequence validation helpers for analysis and visualization internals."""

from collections.abc import Sequence


def materialize_equal_length_sequences(
    sequences: Sequence[Sequence[str]],
) -> tuple[tuple[str, ...], ...]:
    """Materialize and validate non-empty equal-length state sequences."""
    materialized = tuple(
        tuple(str(state) for state in sequence) for sequence in sequences
    )
    if not materialized:
        raise ValueError("At least one state sequence is required.")

    sequence_length = len(materialized[0])
    for sequence in materialized:
        if len(sequence) != sequence_length:
            raise ValueError("All state sequences must have the same length.")

    return materialized
