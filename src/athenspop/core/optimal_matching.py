#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

import functools
import multiprocessing
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Final, Literal

import numpy as np
import pandas as pd
import weighted_levenshtein

from athenspop.models.diaries import SequencedDiary
from athenspop.utils.uncategorized import ArrayCheck, check_array

_ALPHABET_SIZE: Final[int] = 128
# Since all sequences have a constant length, indels must be performed in pairs so as to not alter it.
# Hence, it follows that:
# $
#   C_{\text{indel}} \le 2 * \max{C_{\text{sub}}}
# $
# for indels to be considered by the Wagner–Fischer algorithm.
_MAX_SUBSTITUTION_COST: Final[float] = 2


@dataclass
class AppendedData:
    time_windows: dict[str, tuple[int, int]] | None
    separator: str = "_"


def compute_diary_distances(
    diaries: Iterable[SequencedDiary],
    sequence_start_hour: int,
    sampling_rate_minutes: int,
    appended_data: AppendedData | None = None,
    symmetrize_transition_matrix: bool | Literal["auto"] = "auto",
    indel_cost: float = 1,
) -> np.ndarray[tuple[Any, Any], np.dtype[float]]:
    if symmetrize_transition_matrix == "auto":
        if appended_data:
            if appended_data.time_windows:
                symmetrize_transition_matrix = False
        else:
            symmetrize_transition_matrix = True

    sequences = extract_sequences(diaries)

    if appended_data:
        if appended_data.time_windows:
            sequences = append_time_windows(
                sequences,
                sequence_start_hour,
                sampling_rate_minutes,
                appended_data.time_windows,
                appended_data.separator,
            )
        # TODO: move mode appendage to here

    encoded_sequences, alphabet = encode(sequences)

    transition_matrix = compute_transition_matrix(
        encoded_sequences, alphabet, symmetrize=symmetrize_transition_matrix
    )
    subst_costs = compute_substitution_costs(transition_matrix, alphabet)
    indel_costs = compute_indel_costs(alphabet, indel_cost=indel_cost)

    return compute_distance_matrix(
        encoded_sequences, indel_costs=indel_costs, substitution_costs=subst_costs
    )


def extract_sequences(
    diaries: Iterable[SequencedDiary],
) -> np.ndarray[tuple[Any, Any], np.dtype[np.str_]]:
    return np.asarray([diary.sequence for diary in diaries])


def append_time_windows(
    sequences: np.ndarray[tuple[Any, Any], np.dtype[np.str_]],
    # TODO: Does it make sense for the start time and sampling rate to be decimals?
    sequence_start_hours: int,
    sampling_rate_minutes: int,
    time_windows: dict[str, tuple[int, int]],
    separator: str,
) -> np.ndarray[tuple[Any, Any], np.dtype[np.str_]]:
    suffixes = _compute_time_window_suffixes(
        sequences, sequence_start_hours, sampling_rate_minutes, time_windows, separator
    )

    # This method is available only in NumPy 2.0+.
    return np.strings.add(sequences, suffixes)


def _compute_time_window_suffixes(
    sequences: np.ndarray[tuple[Any, Any], np.dtype[np.str_]],
    sequence_start_hours: int,
    sampling_rate_minutes: int,
    time_windows: dict[str, tuple[int, int]],
    separator: str,
) -> np.ndarray[tuple[Any], np.dtype[np.str_]]:
    num_intervals = sequences.shape[1]

    suffixes: list[str] = [""] * num_intervals
    for i in range(num_intervals):
        curr_minutes = (sequence_start_hours * 60) + (i * sampling_rate_minutes)
        curr_hour = (curr_minutes // 60) % 24

        # Find the time window the current hour corresponds to.
        in_window = False
        for suffix, (start_hour, end_hour) in time_windows.items():
            if start_hour < end_hour:
                # Daytime Window
                if start_hour <= curr_hour < end_hour:
                    suffixes[i] = f"{separator}{suffix}"
                    in_window = True
                    break
            # Overnight Window
            elif curr_hour >= start_hour or curr_hour < end_hour:
                suffixes[i] = f"{separator}{suffix}"
                in_window = True
                break
        if not in_window:
            raise ValueError(
                f"The current hour: {curr_hour} does not correspond to any of the specified time windows: {time_windows}."
                f" "
                f"Hint: Ensure that the provided time windows span 24 hours."
            )

    return np.asarray(suffixes)


def encode(
    sequences: np.ndarray[tuple[Any, Any], np.dtype[np.str_]],
) -> tuple[np.ndarray[tuple[Any], np.dtype[np.str_]], list[str]]:
    # TODO: The alphabet should contain exactly 'len(TIME_WINDOWS) * (len(set(mappings.purpose.values())) + len(set(mappings.modes.values())))' elements.
    alphabet = np.unique(sequences)
    if len(alphabet) > 127:
        raise ValueError(
            f"The total number of unique activities: {len(alphabet)} exceeds 127."
        )

    encoder: dict[str, str] = {
        state: chr(
            i
            # The first ASCII character is the null terminator, which stops string parsing when read.
            # This means that literals in the form of "\x00foo" will not actually be parsed when cast to strings as they will be truncated to their first byte.
            # In particular, this block:
            #   const char* s = "\0foo";
            #   std::cout << std::string(s).length() << std::endl;
            # will output 0 when executed.
            # This behaviour is relevant because the optimal matching engine performs a very similar operation in Cython which leads to incorrect calculations.
            # Hence, we do not assign any state to the null terminator.
            + 1
        )
        for i, state in enumerate(alphabet)
    }

    return (
        np.asarray(
            [
                "".join([encoder[activity] for activity in sequence])
                for sequence in sequences
            ]
        ),
        # TODO: This list does not equal 'np.asarray(list(encoder.values())))'. -- Correct; 0--31 are non printable control characters and NumPy encodes them as char (i.e., 1-bit) values, whereas Python treats them as normal strings.
        list(encoder.values()),
    )


def compute_transition_matrix(
    encoded_sequences: np.ndarray[tuple[Any], np.dtype[np.str_]],
    encoded_alphabet: list[str],
    symmetrize: bool,
) -> np.ndarray[tuple[Any, Any], np.dtype[np.float64]]:
    src_activities, dst_activities = _gather_transitions(encoded_sequences)
    transition_counts = pd.crosstab(src_activities, dst_activities)

    # Ensure that the transition matrix is square.
    # This is not the case when one or more activities appear only in the beginning or end of each sequence (i.e., 'len(src_activities) != len(dst_activities)').
    transition_counts = transition_counts.reindex(
        index=encoded_alphabet, columns=encoded_alphabet, fill_value=0
    )
    transition_counts = transition_counts.to_numpy()
    assert check_array(
        transition_counts,
        ArrayCheck.HOLLOW | ArrayCheck.SQUARE,
        # ArrayCheck.SQUARE,
    )

    if symmetrize:
        # Measure the overall dissimilarity amongst activities, ignoring the corresponding transition direction.
        # This is generally the preferred approach in sequence analysis, but since we are working with time-encoded activities, the inverse of certain valid transitions is in fact impossible (e.g., Work_AM -> Work_PM v. Work_PM -> Work_AM).
        # Therefore, we do not symmetrize the transition contingency table to avoid assigning a pseudo-count to these activities.
        transition_counts += (
            transition_counts.T
        )  # It is not necessary to scale the output.
        assert check_array(transition_counts, ArrayCheck.SYMMETRIC)

    transition_matrix = transition_counts / transition_counts.sum(
        axis=1,
        # Reshape the output into a row vector.
        keepdims=True,
    )
    assert check_array(transition_matrix, ArrayCheck.TARGET_ROW_SUM, target=1)

    return transition_matrix


def compute_indel_costs(
    encoded_alphabet: list[str], indel_cost: float
) -> np.ndarray[tuple[Any], np.dtype[np.float64]]:
    state_indices = [ord(activity) for activity in encoded_alphabet]

    indel_costs = np.full(_ALPHABET_SIZE, indel_cost, dtype=np.float64)
    indel_costs[state_indices] = indel_cost
    assert check_array(indel_costs, ArrayCheck.TARGET_SIGN, target=1)

    return indel_costs


def compute_substitution_costs(
    transition_matrix: np.ndarray[tuple[Any, Any], np.dtype[np.float64]],
    encoded_alphabet: list[str],
) -> np.ndarray[tuple[Any, Any], np.dtype[np.float64]]:
    state_indices = [ord(activity) for activity in encoded_alphabet]

    dense_costs = (
        _MAX_SUBSTITUTION_COST
        # P(A|B)
        - transition_matrix
        # P(B|A)
        - transition_matrix.T
    )
    np.fill_diagonal(dense_costs, 0)
    assert check_array(
        dense_costs, ArrayCheck.DISTANCE_MATRIX | ArrayCheck.TARGET_SIGN, target=1
    )

    sparse_costs = np.full(
        (_ALPHABET_SIZE, _ALPHABET_SIZE), _MAX_SUBSTITUTION_COST, dtype=np.float64
    )
    sparse_costs[np.ix_(state_indices, state_indices)] = dense_costs
    np.fill_diagonal(sparse_costs, 0)
    assert check_array(
        sparse_costs, ArrayCheck.DISTANCE_MATRIX | ArrayCheck.TARGET_SIGN, target=1
    )

    return sparse_costs


def compute_distance_matrix(
    encoded_sequences: np.ndarray[tuple[Any], np.dtype[np.str_]],
    indel_costs: np.ndarray[tuple[Any,], np.dtype[np.float64]],
    substitution_costs: np.ndarray[tuple[Any, Any], np.dtype[np.float64]],
):
    # FIXME: This block used to work fine, but now is ~15-20x slower than before.
    # distance_matrix = sklearn.metrics.pairwise_distances(
    #     encoded_sequences,
    #     metric=functools.partial(
    #         weighted_levenshtein.levenshtein,
    #         insert_costs=indel_costs,
    #         delete_costs=indel_costs,
    #         substitute_costs=substitution_costs,
    #     ),
    #     n_jobs=-1,
    #     ensure_all_finite=True,
    # )
    distance_matrix = compute_distance_matrix_mp_unsafe(
        encoded_sequences=encoded_sequences,
        indel_costs=indel_costs,
        substitution_costs=substitution_costs,
    )

    assert check_array(
        distance_matrix, ArrayCheck.DISTANCE_MATRIX | ArrayCheck.TARGET_SIGN, target=1
    )

    return distance_matrix


# FIXME
def compute_distance_matrix_mp_unsafe(
    encoded_sequences: np.ndarray[tuple[Any], np.dtype[np.str_]],
    indel_costs: np.ndarray[tuple[Any], np.dtype[np.float64]],
    substitution_costs: np.ndarray[tuple[Any, Any], np.dtype[np.float64]],
) -> np.ndarray[tuple[Any, Any], np.dtype[np.float64]]:
    n = len(encoded_sequences)

    # 1. Initialize an empty matrix
    distance_matrix = np.zeros((n, n), dtype=np.float64)

    # 2. Identify strictly upper triangle indices (i < j)
    # This reduces calculations by 50% compared to sklearn's full pass
    rows, cols = np.triu_indices(n, k=1)

    # If no pairs (single diary), return zero matrix
    if len(rows) == 0:
        return distance_matrix

    # 3. Prepare chunks for multiprocessing
    # We zip indices together to pass to workers
    pair_indices = np.column_stack((rows, cols))

    # Determine chunk size. For 10k items, 100-500 is usually good to amortize IPC overhead.
    # Total pairs for N=1000 is ~500,000.
    n_cpus = multiprocessing.cpu_count()
    # Split indices into roughly equal chunks for each CPU
    chunks = np.array_split(pair_indices, n_cpus * 4)

    # 4. Define the worker partial
    # We pass the heavy cost matrices *once* via partial (or global context in some setups)
    worker = functools.partial(
        _levenshtein_worker,
        sequences=encoded_sequences,
        insert_costs=indel_costs,
        delete_costs=indel_costs,
        substitute_costs=substitution_costs,
    )

    # 5. Execute in parallel
    with multiprocessing.Pool(processes=n_cpus) as pool:
        # map returns a list of result arrays, one per chunk
        results = pool.map(worker, chunks)

    # 6. Reconstruct the matrix
    # Concatenate all chunk results back into a single 1D array of distances
    flat_distances = np.concatenate(results)

    # Assign to the upper triangle
    distance_matrix[rows, cols] = flat_distances

    # 7. Symmetrize (Upper + Lower)
    # Since diagonal is 0, M + M.T works perfectly to fill the lower triangle
    distance_matrix = distance_matrix + distance_matrix.T

    return distance_matrix


# FIXME
def _levenshtein_worker(
    chunk_indices: np.ndarray,
    sequences: np.ndarray,
    insert_costs: np.ndarray,
    delete_costs: np.ndarray,
    substitute_costs: np.ndarray,
) -> np.ndarray:
    """Worker function executed in separate processes.
    Receives a chunk of (i, j) indices and computes the distance.
    """
    n_pairs = len(chunk_indices)
    results = np.empty(n_pairs, dtype=np.float64)

    # Cache the C-function to avoid attribute lookup in loop
    lev_func = weighted_levenshtein.levenshtein

    for k in range(n_pairs):
        i, j = chunk_indices[k]
        # positional arguments: str1, str2, followed by kwargs
        results[k] = lev_func(
            sequences[i],
            sequences[j],
            insert_costs=insert_costs,
            delete_costs=delete_costs,
            substitute_costs=substitute_costs,
        )

    return results


def _gather_transitions(
    encoded_sequences: np.ndarray[tuple[Any], np.dtype[np.str_]],
) -> tuple[list[str], list[str]]:
    src_states, dst_states = [], []
    for sequence in encoded_sequences:
        for src_state, dst_state in zip(sequence, sequence[1:]):
            if src_state == dst_state:
                continue
            src_states.append(src_state)
            dst_states.append(dst_state)

    return src_states, dst_states
