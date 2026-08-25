# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module visualizes temporal state distributions with Matplotlib."""

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Final

import matplotlib.axes
import matplotlib.figure
import matplotlib.patches
import matplotlib.pyplot as plt

import athenspop._sequences
import athenspop.clustering.hierarchical

#: This value controls horizontal spacing between adjacent leaf nodes.
_LEAF_SPACING: Final[float] = 1.35
#: This value controls the width assigned to each node panel.
_NODE_WIDTH: Final[float] = 1.0
#: This value controls the height of one state-distribution panel.
_PANEL_HEIGHT: Final[float] = 0.26
#: This value controls the vertical gap between state-distribution panels.
_PANEL_GAP: Final[float] = 0.08
#: This value reserves vertical space for a node label.
_LABEL_HEIGHT: Final[float] = 0.44
#: This value controls vertical spacing between adjacent tree depths.
_DEPTH_SPACING: Final[float] = 1.25
#: This value controls the horizontal margin around the plotted tree.
_MARGIN_X: Final[float] = 0.35
#: This value controls the top margin above the plotted tree.
_MARGIN_TOP: Final[float] = 0.25


@dataclasses.dataclass(frozen=True, slots=True)
class TemporalDendrogramPlotStyle:
    """This class defines display settings for a temporal cut dendrogram.

    Attributes:
        title: This value is the optional figure title.
        state_groups: This optional mapping associates each panel title with the state
            names included in that panel.
        state_colors: This optional explicit color mapping is keyed by raw state name.
        state_labels: This optional display-label mapping is keyed by raw state name.
    """

    title: str | None = None
    state_groups: Mapping[str, Sequence[str]] | None = None
    state_colors: Mapping[str, str] | None = None
    state_labels: Mapping[str, str] | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class _PlotContext:
    """This class stores shared drawing inputs for one dendrogram figure."""

    axes: matplotlib.axes.Axes
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
    """Plot a cut dendrogram whose displayed nodes contain temporal state distributions.

    Args:
        linkage_matrix: This SciPy linkage matrix defines the hierarchy over the
            supplied observations.
        sequences: These equal-length state sequences align with the observations
            used to compute `linkage_matrix`.
        n_clusters: This value is the number of displayed cut clusters.
        style: These optional display settings include state grouping and labels.

    Returns:
        The function returns a Matplotlib figure containing one generic
        cut-dendrogram axis.

    Raises:
        ValueError: The function raises this error if the sequence and linkage counts
            differ, the sequences are not equal length, or a state group names an
            absent state.

    Notes:
        The function returns a figure and never writes files.
        Callers own survey-specific state grouping, colors, labels, and figure export.
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
    nodes = _display_nodes(tree)
    leaves = tuple(node for node in nodes if node.is_leaf)
    max_depth = max(node.depth for node in nodes)
    node_height = (
        _LABEL_HEIGHT
        + len(groups) * _PANEL_HEIGHT
        + max(0, len(groups) - 1) * _PANEL_GAP
    )
    width_units = _MARGIN_X * 2 + _NODE_WIDTH + max(0, len(leaves) - 1) * _LEAF_SPACING
    height_units = _MARGIN_TOP * 2 + node_height + max_depth * _DEPTH_SPACING

    figure_object, axes_object = plt.subplots(layout="constrained")
    if resolved_style.title is not None:
        axes_object.set_title(resolved_style.title)
    axes_object.set_xlim(0.0, width_units)
    axes_object.set_ylim(height_units, 0.0)
    axes_object.axis("off")

    colors = _state_color_map(materialized_sequences, resolved_style)
    labels = _state_label_map(materialized_sequences, resolved_style)
    context = _PlotContext(
        axes=axes_object,
        sequences=materialized_sequences,
        groups=groups,
        colors=colors,
        labels=labels,
    )

    _draw_edges(axes_object, tree, resolved_style)
    for node in nodes:
        _draw_node(context, node)

    _draw_legend(context)
    return figure_object


def _draw_edges(
    axes_object: matplotlib.axes.Axes,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    style: TemporalDendrogramPlotStyle,
) -> None:
    """Draw orthogonal edges for one displayed subtree."""
    if node.is_leaf:
        return
    left = _required_child(node.left)
    right = _required_child(node.right)
    _draw_edge(axes_object, node, left, style)
    _draw_edge(axes_object, node, right, style)
    _draw_edges(axes_object, left, style)
    _draw_edges(axes_object, right, style)


def _draw_edge(
    axes_object: matplotlib.axes.Axes,
    parent: athenspop.clustering.hierarchical.CutDendrogramNode,
    child: athenspop.clustering.hierarchical.CutDendrogramNode,
    style: TemporalDendrogramPlotStyle,
) -> None:
    """Draw one orthogonal edge between displayed nodes."""
    parent_x, parent_y = _node_anchor_bottom(parent, style)
    child_x, child_y = _node_anchor_top(child)
    middle_y = parent_y + (child_y - parent_y) * 0.42
    axes_object.plot(
        (parent_x, parent_x, child_x, child_x),
        (parent_y, middle_y, middle_y, child_y),
    )


def _draw_node(
    context: _PlotContext,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> None:
    """Draw labels and temporal panels for one displayed node."""
    x, y = _node_top_left(node)
    observation_label = "observation" if len(node.members) == 1 else "observations"
    text_lines = [
        f"The normalized height is {node.normalized_height:.2f}.",
        f"This node contains {len(node.members)} {observation_label}.",
    ]
    if node.leaf_label is not None:
        text_lines.insert(0, f"This node is cluster {node.leaf_label}.")
    context.axes.text(x, y, "\n".join(text_lines), ha="left", va="top")

    panel_y = y + _LABEL_HEIGHT
    for title, states in context.groups:
        _draw_panel(context, node, states, x=x, y=panel_y)
        context.axes.text(
            x + _NODE_WIDTH + 0.04,
            panel_y + _PANEL_HEIGHT / 2.0,
            title,
            ha="left",
            va="center",
        )
        panel_y += _PANEL_HEIGHT + _PANEL_GAP


def _draw_panel(
    context: _PlotContext,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    states: tuple[str, ...],
    *,
    x: float,
    y: float,
) -> None:
    """Draw one stacked temporal state distribution panel."""
    context.axes.add_patch(
        matplotlib.patches.Rectangle(
            (x, y),
            _NODE_WIDTH,
            _PANEL_HEIGHT,
            facecolor="none",
        )
    )
    bin_count = len(context.sequences[0])
    bin_width = _NODE_WIDTH / bin_count
    shares = _state_shares(node, context.sequences, states)
    for bin_index in range(bin_count):
        bar_x = x + bin_index * bin_width
        bar_top = y + _PANEL_HEIGHT
        for state in states:
            share = shares.get((bin_index, state), 0.0)
            if share <= 0.0:
                continue
            bar_height = share * _PANEL_HEIGHT
            bar_top -= bar_height
            context.axes.add_patch(
                matplotlib.patches.Rectangle(
                    (bar_x, bar_top),
                    bin_width,
                    bar_height,
                    facecolor=context.colors[state],
                    edgecolor="none",
                )
            )


def _draw_legend(context: _PlotContext) -> None:
    """Draw a figure-level state legend using Matplotlib layout."""
    states = tuple(state for _, group in context.groups for state in group)
    handles = [
        matplotlib.patches.Patch(
            facecolor=context.colors[state], label=context.labels[state]
        )
        for state in states
    ]
    context.axes.figure.legend(
        handles=handles,
        loc="outside lower center",
        ncols=min(4, len(handles)),
    )


def _state_shares(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    sequences: tuple[tuple[str, ...], ...],
    states: tuple[str, ...],
) -> dict[tuple[int, str], float]:
    """Return within-node state shares by time bin."""
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
        return (("This panel shows all states.", states),)
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
    """Return a complete state color mapping."""
    explicit_colors = {} if style.state_colors is None else dict(style.state_colors)
    style_colors = plt.rcParams["axes.prop_cycle"].by_key().get("color") or ["C0"]
    return {
        state: explicit_colors.get(state, style_colors[index % len(style_colors)])
        for index, state in enumerate(_states(sequences))
    }


def _state_label_map(
    sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramPlotStyle
) -> dict[str, str]:
    """Return a complete state label mapping."""
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


def _node_top_left(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> tuple[float, float]:
    """Return top-left coordinates for one displayed node."""
    center_x = _MARGIN_X + _NODE_WIDTH / 2.0 + node.order * _LEAF_SPACING
    top_y = _MARGIN_TOP + node.depth * _DEPTH_SPACING
    return center_x - _NODE_WIDTH / 2.0, top_y


def _node_anchor_top(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> tuple[float, float]:
    """Return the top edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node)
    return x + _NODE_WIDTH / 2.0, y + _LABEL_HEIGHT


def _node_anchor_bottom(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    style: TemporalDendrogramPlotStyle,
) -> tuple[float, float]:
    """Return the bottom edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node)
    panel_count = 1 if style.state_groups is None else len(style.state_groups)
    return (
        x + _NODE_WIDTH / 2.0,
        y
        + _LABEL_HEIGHT
        + panel_count * _PANEL_HEIGHT
        + max(0, panel_count - 1) * _PANEL_GAP,
    )


def _required_child(
    node: athenspop.clustering.hierarchical.CutDendrogramNode | None,
) -> athenspop.clustering.hierarchical.CutDendrogramNode:
    """Return a required immutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node
