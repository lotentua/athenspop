# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Explore and cluster reported purpose chains from the public Athens tables."""

import pathlib
from collections.abc import Mapping, Sequence
from typing import Final

import matplotlib.figure
import matplotlib.pyplot as plt
import pandas as pd

import athenspop.clustering.hierarchical
import athenspop.model.survey
import athenspop.sequence.distance

#: Default directory for the released Athens CSV tables.
DEFAULT_DATA_DIRECTORY: Final[pathlib.Path] = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "athens"
)


def load_purpose_chains(
    data_directory: pathlib.Path = DEFAULT_DATA_DIRECTORY,
) -> tuple[tuple[str, ...], ...]:
    """Load the public tables and return one reported purpose chain per respondent.

    Args:
        data_directory:
            Directory containing `trips.csv`, `persons.csv`, and `households.csv`.

    Returns:
        Purpose sequences in validated trip-chain order.
    """
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        pd.read_csv(data_directory / "trips.csv"),
        persons=pd.read_csv(data_directory / "persons.csv"),
        households=pd.read_csv(data_directory / "households.csv"),
    )
    return tuple(
        tuple(trip.purpose for trip in diary.trips) for diary in dataset.diaries
    )


def unit_substitution_cost(
    chains: Sequence[Sequence[str]],
) -> Mapping[tuple[str, str], float]:
    """Return symmetric unit substitution costs for all observed states.

    Args:
        chains: Symbolic purpose chains that define the cost-mapping states.

    Returns:
        Zero diagonal and unit off-diagonal costs.
    """
    states = {state for chain in chains for state in chain}
    return {
        (source, target): 0.0 if source == target else 1.0
        for source in states
        for target in states
    }


def chain_frequency_table(
    chains: Sequence[Sequence[str]],
) -> pd.DataFrame:
    """Summarize exact reported purpose-chain frequencies.

    Args:
        chains: Purpose chains counted without imputation or completion.

    Returns:
        Frequencies sorted by decreasing count and then by chain label.
    """
    labels = pd.Series(
        (" -> ".join(chain) for chain in chains),
        dtype="string",
        name="purpose_chain",
    )
    frequencies = (
        labels.value_counts()
        .rename_axis("purpose_chain")
        .reset_index(name="respondents")
    )
    return frequencies.sort_values(
        ["respondents", "purpose_chain"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)


def illustrative_cluster_labels(
    chains: Sequence[Sequence[str]], *, n_clusters: int
) -> tuple[int, ...]:
    """Return an explicitly illustrative average-linkage cut of purpose chains.

    Args:
        chains: Reported purpose chains compared by unnormalized optimal matching.
        n_clusters: Analyst-selected display cut, not an estimated optimum.

    Returns:
        One positive cluster label per input chain.
    """
    distances = athenspop.sequence.distance.dissimilarity_matrix(
        chains, substitution_cost=unit_substitution_cost(chains)
    )
    linkage_matrix = athenspop.clustering.hierarchical.average_linkage(distances)
    labels = athenspop.clustering.hierarchical.flat_cluster_labels(
        linkage_matrix, n_clusters=n_clusters
    )
    return tuple(int(label) for label in labels)


def plot_chain_frequencies(
    frequencies: pd.DataFrame, *, limit: int = 12
) -> matplotlib.figure.Figure:
    """Plot the most frequent exact purpose chains using the active stylesheet.

    Args:
        frequencies:
            Table returned by `chain_frequency_table`.
        limit: Maximum rows to display.

    Returns:
        Matplotlib figure using the active stylesheet.
    """
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("`limit` must be an integer.")
    if limit <= 0:
        raise ValueError("`limit` must be positive.")
    displayed = frequencies.head(limit).sort_values("respondents", kind="stable")
    figure_object, axes_object = plt.subplots(layout="constrained")
    axes_object.barh(displayed["purpose_chain"], displayed["respondents"])
    axes_object.set_xlabel("Respondents")
    axes_object.set_ylabel("Purpose chain")
    return figure_object


def main() -> None:
    """Print the primary frequency result and display its minimally styled plot."""
    chains = load_purpose_chains()
    frequencies = chain_frequency_table(chains)
    print(frequencies.head(12).to_string(index=False))
    plot_chain_frequencies(frequencies)
    plt.show()


if __name__ == "__main__":
    main()
