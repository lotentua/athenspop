# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Temporal state-distribution visualization with Matplotlib."""

import dataclasses
from collections.abc import Mapping, Sequence

import matplotlib.axes
import matplotlib.figure
import matplotlib.gridspec
import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib.ticker

import athenspop._sequences
import athenspop.clustering.hierarchical


@dataclasses.dataclass(frozen=True, slots=True)
class TemporalDendrogramPlotStyle:
    """Display settings for a temporal cut dendrogram.

    Attributes:
        title:
            Optional figure title.
        state_groups:
            Optional panel-title mapping to included state names.
        state_colors:
            Optional color mapping keyed by raw state name.
        state_labels:
            Optional display-label mapping keyed by raw state name.
    """

    title: str | None = None
    state_groups: Mapping[str, Sequence[str]] | None = None
    state_colors: Mapping[str, str] | None = None
    state_labels: Mapping[str, str] | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class _PlotContext:
    """Shared inputs for one dendrogram figure."""

    figure: matplotlib.figure.Figure
    sequences: tuple[tuple[str, ...], ...]
    groups: tuple[tuple[str, tuple[str, ...]], ...]
    colors: Mapping[str, str]
    labels: Mapping[str, str]


def plot_cut_dendrogram_state_distribution(
    linkage_matrix: athenspop.clustering.hierarchical.LinkageMatrix,
    sequences: Sequence[Sequence[str]],
    *,
    n_clusters: int,
    style: TemporalDendrogramPlotStyle | None = None,
) -> matplotlib.figure.Figure:
    """Plot a cut hierarchy with temporal state shares for every cut cluster.

    Args:
        linkage_matrix:
            SciPy hierarchy over the supplied observations.
        sequences:
            Equal-length state sequences aligned with the hierarchy.
        n_clusters:
            Number of displayed cut clusters.
        style:
            Optional title, state groups, colors, and labels.

    Returns:
        A Matplotlib figure with a quantitative tree axis and state-share panels.

    Raises:
        ValueError:
            If sequence counts or lengths disagree with the hierarchy, or a
            state group contains an absent state.

    Notes:
        No files are written. Dimensions, typography, default colors, tree-line
        width, and unspecified styling inherit from Matplotlib configuration.
        Quantitative axes and bar geometry follow the visual contract.
    """
    resolved_style = TemporalDendrogramPlotStyle() if style is None else style
    materialized_sequences = athenspop._sequences.materialize_equal_length_sequences(
        sequences
    )
    expected_sequence_count = int(linkage_matrix.shape[0]) + 1
    if len(materialized_sequences) != expected_sequence_count:
        raise ValueError(
            f"`sequences` must contain {expected_sequence_count} rows for this "
            f"linkage matrix, got {len(materialized_sequences)}."
        )

    groups = _state_groups(materialized_sequences, resolved_style.state_groups)
    tree = athenspop.clustering.hierarchical.cut_dendrogram_tree(
        linkage_matrix, n_clusters=n_clusters
    )
    leaves = _display_leaves(tree)

    figure_object = plt.figure(layout="constrained")
    grid = figure_object.add_gridspec(
        1 + len(groups),
        len(leaves),
        height_ratios=(2.0,) + (1.0,) * len(groups),
    )
    tree_axes = figure_object.add_subplot(grid[0, :])
    if resolved_style.title is not None:
        figure_object.suptitle(resolved_style.title)
    _draw_tree(tree_axes, tree, leaves)

    context = _PlotContext(
        figure=figure_object,
        sequences=materialized_sequences,
        groups=groups,
        colors=_state_color_map(materialized_sequences, resolved_style),
        labels=_state_label_map(materialized_sequences, resolved_style),
    )
    _draw_distribution_grid(context, grid, leaves)
    _draw_legend(context)
    return figure_object


def _draw_tree(
    axes_object: matplotlib.axes.Axes,
    root: athenspop.clustering.hierarchical.CutDendrogramNode,
    leaves: tuple[athenspop.clustering.hierarchical.CutDendrogramNode, ...],
) -> None:
    """Draw the cut hierarchy on quantitative normalized-height coordinates."""
    tree_color = str(plt.rcParams["grid.color"])
    _draw_tree_edges(axes_object, root, color=tree_color)
    axes_object.set_xlim(-0.5, len(leaves) - 0.5)
    axes_object.set_ylim(0.0, 1.05)
    axes_object.set_xticks(
        [leaf.order for leaf in leaves],
        [f"Cluster {leaf.leaf_label}" for leaf in leaves],
    )
    axes_object.set_xlabel("Cut cluster")
    axes_object.set_ylabel("Normalized height", rotation=0, ha="right", va="center")


def _draw_tree_edges(
    axes_object: matplotlib.axes.Axes,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    *,
    color: str,
) -> None:
    """Draw one displayed subtree with a single neutral structural color."""
    if node.is_leaf:
        return
    left = _required_child(node.left)
    right = _required_child(node.right)
    axes_object.plot(
        (left.order, left.order),
        (left.normalized_height, node.normalized_height),
        color=color,
    )
    axes_object.plot(
        (right.order, right.order),
        (right.normalized_height, node.normalized_height),
        color=color,
    )
    axes_object.plot(
        (left.order, right.order),
        (node.normalized_height, node.normalized_height),
        color=color,
    )
    _draw_tree_edges(axes_object, left, color=color)
    _draw_tree_edges(axes_object, right, color=color)


def _draw_distribution_grid(
    context: _PlotContext,
    grid: matplotlib.gridspec.GridSpec,
    leaves: tuple[athenspop.clustering.hierarchical.CutDendrogramNode, ...],
) -> None:
    """Draw aligned state-share axes for every cut cluster."""
    last_group_index = len(context.groups) - 1
    for column, node in enumerate(leaves):
        for group_index, (group_title, states) in enumerate(context.groups):
            axes_object = context.figure.add_subplot(grid[1 + group_index, column])
            _draw_state_bars(
                axes_object,
                context,
                node,
                states,
                group_title=group_title,
            )
            if column != 0:
                axes_object.tick_params(labelleft=False)
                axes_object.set_ylabel("")
            if group_index != last_group_index:
                axes_object.tick_params(labelbottom=False)
            else:
                axes_object.set_xlabel("Sequence bin")


def _draw_state_bars(
    axes_object: matplotlib.axes.Axes,
    context: _PlotContext,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    states: tuple[str, ...],
    *,
    group_title: str,
) -> None:
    """Draw unit-width stacked bars for one node and state group."""
    bin_count = len(context.sequences[0])
    shares = _state_shares(node, context.sequences, states)
    bottoms = [0.0] * bin_count
    for state in states:
        heights = [
            shares.get((bin_index, state), 0.0) for bin_index in range(bin_count)
        ]
        axes_object.bar(
            range(bin_count),
            heights,
            width=1.0,
            align="center",
            bottom=bottoms,
            color=context.colors[state],
            linewidth=0.0,
        )
        bottoms = [
            bottom + height for bottom, height in zip(bottoms, heights, strict=True)
        ]
    axes_object.set_xlim(-0.5, bin_count - 0.5)
    axes_object.set_ylim(0.0, 1.0)
    tick_step = max(1, (bin_count + 3) // 4)
    axes_object.set_xticks(range(0, bin_count, tick_step))
    axes_object.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.5))
    axes_object.set_ylabel(group_title, rotation=0, ha="right", va="center")
    for spine in axes_object.spines.values():
        spine.set_visible(True)


def _draw_legend(context: _PlotContext) -> None:
    """Draw one figure-level legend for all grouped states."""
    states = tuple(
        dict.fromkeys(state for _, group in context.groups for state in group)
    )
    handles = [
        matplotlib.patches.Patch(
            facecolor=context.colors[state], label=context.labels[state]
        )
        for state in states
    ]
    context.figure.legend(
        handles=handles,
        loc="outside lower center",
        ncols=min(3, len(handles)),
    )


def _state_shares(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    sequences: tuple[tuple[str, ...], ...],
    states: tuple[str, ...],
) -> dict[tuple[int, str], float]:
    """Return within-node state shares by sequence bin."""
    state_set = set(states)
    counts: dict[tuple[int, str], int] = {}
    for member in node.members:
        for bin_index, state in enumerate(sequences[member]):
            if state in state_set:
                counts[(bin_index, state)] = counts.get((bin_index, state), 0) + 1
    denominator = len(node.members)
    return {key: count / denominator for key, count in counts.items()}


def _state_groups(
    sequences: tuple[tuple[str, ...], ...],
    requested_groups: Mapping[str, Sequence[str]] | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return validated state groups for panel rendering."""
    states = _states(sequences)
    if requested_groups is None:
        return (("All states", states),)
    if not requested_groups:
        raise ValueError(
            "`state_groups` must contain at least one group when provided."
        )

    state_set = set(states)
    groups: list[tuple[str, tuple[str, ...]]] = []
    for title, group_states in requested_groups.items():
        if not isinstance(title, str) or not title.strip():
            raise TypeError("Every state-group title must be a non-empty string.")
        materialized_group = tuple(group_states)
        if not materialized_group:
            raise ValueError(f"State group {title!r} must contain at least one state.")
        if any(
            not isinstance(state, str) or not state.strip()
            for state in materialized_group
        ):
            raise TypeError("Every grouped state must be a non-empty string.")
        unknown = sorted(set(materialized_group) - state_set)
        if unknown:
            raise ValueError(
                f"State group {title!r} contains unknown state(s): "
                f"{', '.join(unknown)}."
            )
        groups.append((title, materialized_group))
    return tuple(groups)


def _states(sequences: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    """Return sorted unique states from materialized sequences."""
    return tuple(sorted({state for sequence in sequences for state in sequence}))


def _state_color_map(
    sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramPlotStyle
) -> dict[str, str]:
    """Return a complete state-color mapping."""
    explicit_colors = {} if style.state_colors is None else dict(style.state_colors)
    style_colors = plt.rcParams["axes.prop_cycle"].by_key().get("color") or ["C0"]
    return {
        state: explicit_colors.get(state, style_colors[index % len(style_colors)])
        for index, state in enumerate(_states(sequences))
    }


def _state_label_map(
    sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramPlotStyle
) -> dict[str, str]:
    """Return a complete state-label mapping."""
    explicit_labels = {} if style.state_labels is None else dict(style.state_labels)
    return {state: explicit_labels.get(state, state) for state in _states(sequences)}


def _display_nodes(
    root: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> tuple[athenspop.clustering.hierarchical.CutDendrogramNode, ...]:
    """Return displayed nodes in parent-before-child order."""
    nodes = [root]
    if root.left is not None:
        nodes.extend(_display_nodes(root.left))
    if root.right is not None:
        nodes.extend(_display_nodes(root.right))
    return tuple(nodes)


def _display_leaves(
    root: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> tuple[athenspop.clustering.hierarchical.CutDendrogramNode, ...]:
    """Return displayed cut leaves in plotting order."""
    return tuple(
        sorted(
            (node for node in _display_nodes(root) if node.is_leaf),
            key=lambda node: node.order,
        )
    )


def _required_child(
    node: athenspop.clustering.hierarchical.CutDendrogramNode | None,
) -> athenspop.clustering.hierarchical.CutDendrogramNode:
    """Return a required displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node
