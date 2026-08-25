# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Temporal state-distribution visualization with Matplotlib."""

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Final

import matplotlib.axes
import matplotlib.figure
import matplotlib.legend
import matplotlib.patches
import matplotlib.pyplot as plt
import matplotlib.text

import athenspop._sequences
import athenspop.clustering.hierarchical

#: Horizontal margin around the embedded dendrogram.
_HORIZONTAL_MARGIN: Final[float] = 0.04
#: Vertical gap between text, legends, and the embedded tree.
_VERTICAL_MARGIN: Final[float] = 0.02
#: Largest fraction of the figure width occupied by one node panel.
_MAX_NODE_WIDTH: Final[float] = 0.20
#: Largest fraction of the figure height occupied by one two-panel node.
_MAX_NODE_HEIGHT: Final[float] = 0.14
#: Figure-width budget divided among displayed leaves for node panels.
_NODE_WIDTH_BUDGET: Final[float] = 0.82
#: Share of available tree height divided among split-order levels.
_NODE_HEIGHT_BUDGET: Final[float] = 0.75
#: Vertical gap between the two distribution axes in one node.
_PANEL_GAP: Final[float] = 0.004


@dataclasses.dataclass(frozen=True, slots=True)
class TemporalDendrogramPlotStyle:
    """Display settings for a temporal cut dendrogram.

    Attributes:
        title:
            Optional figure title.
        state_groups:
            Optional two-item mapping from panel titles to included state names.
            The first group is drawn above the second group.
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
    """Plot a cut hierarchy whose nodes contain temporal state distributions.

    Args:
        linkage_matrix:
            SciPy hierarchy over the supplied observations.
        sequences:
            Equal-length state sequences aligned with the hierarchy.
        n_clusters:
            Number of displayed cut clusters.
        style:
            Optional title, two state groups, colors, and labels.

    Returns:
        A Matplotlib figure containing one embedded tree and two distribution axes
        for every displayed node.

    Raises:
        ValueError:
            If sequence counts or lengths disagree with the hierarchy, or a
            state group contains an absent state.

    Notes:
        No files are written. Dimensions, typography, default colors, tree-line
        width, and unspecified styling inherit from Matplotlib configuration. Node
        positions and unit-width bar geometry follow the visual contract.
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

    tree = athenspop.clustering.hierarchical.cut_dendrogram_tree(
        linkage_matrix, n_clusters=n_clusters
    )
    groups = _state_groups(materialized_sequences, resolved_style.state_groups)
    nodes = _display_nodes(tree)
    leaves = _display_leaves(tree)
    maximum_depth = max(node.depth for node in nodes)

    figure_object = plt.figure()
    title_artist = (
        None
        if resolved_style.title is None
        else figure_object.suptitle(resolved_style.title)
    )
    context = _PlotContext(
        figure=figure_object,
        sequences=materialized_sequences,
        groups=groups,
        colors=_state_color_map(materialized_sequences, resolved_style),
        labels=_state_label_map(materialized_sequences, resolved_style),
    )
    legends = _draw_legends(context)
    tree_bottom, tree_top = _tree_vertical_bounds(
        figure_object,
        legends,
        title_artist=title_artist,
    )
    tree_axes = figure_object.add_axes(
        (0.0, 0.0, 1.0, 1.0), label="dendrogram-tree", zorder=0
    )
    _draw_tree(
        tree_axes,
        tree,
        leaf_count=len(leaves),
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    _draw_node_distribution_panels(
        context,
        nodes,
        leaf_count=len(leaves),
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    return figure_object


def _draw_tree(
    axes_object: matplotlib.axes.Axes,
    root: athenspop.clustering.hierarchical.CutDendrogramNode,
    *,
    leaf_count: int,
    maximum_depth: int,
    tree_bottom: float,
    tree_top: float,
) -> None:
    """Draw one split-order tree behind all embedded node panels."""
    tree_color = str(plt.rcParams["grid.color"])
    _draw_tree_edges(
        axes_object,
        root,
        color=tree_color,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    axes_object.set_xlim(0.0, 1.0)
    axes_object.set_ylim(0.0, 1.0)
    axes_object.set_axis_off()


def _draw_tree_edges(
    axes_object: matplotlib.axes.Axes,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    *,
    color: str,
    leaf_count: int,
    maximum_depth: int,
    tree_bottom: float,
    tree_top: float,
) -> None:
    """Connect one panel to its two children with neutral orthogonal branches."""
    if node.is_leaf:
        return
    left = _required_child(node.left)
    right = _required_child(node.right)
    parent_rectangle = _node_rectangle(
        node,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    left_rectangle = _node_rectangle(
        left,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    right_rectangle = _node_rectangle(
        right,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    parent_x = parent_rectangle[0] + parent_rectangle[2] / 2.0
    parent_bottom = parent_rectangle[1]
    left_x = left_rectangle[0] + left_rectangle[2] / 2.0
    right_x = right_rectangle[0] + right_rectangle[2] / 2.0
    child_top = left_rectangle[1] + left_rectangle[3]
    branch_y = (parent_bottom + child_top) / 2.0
    axes_object.plot(
        (parent_x, parent_x),
        (parent_bottom, branch_y),
        color=color,
    )
    axes_object.plot(
        (left_x, right_x),
        (branch_y, branch_y),
        color=color,
    )
    axes_object.plot(
        (left_x, left_x),
        (branch_y, child_top),
        color=color,
    )
    axes_object.plot(
        (right_x, right_x),
        (branch_y, child_top),
        color=color,
    )
    _draw_tree_edges(
        axes_object,
        left,
        color=color,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )
    _draw_tree_edges(
        axes_object,
        right,
        color=color,
        leaf_count=leaf_count,
        maximum_depth=maximum_depth,
        tree_bottom=tree_bottom,
        tree_top=tree_top,
    )


def _draw_node_distribution_panels(
    context: _PlotContext,
    nodes: tuple[athenspop.clustering.hierarchical.CutDendrogramNode, ...],
    *,
    leaf_count: int,
    maximum_depth: int,
    tree_bottom: float,
    tree_top: float,
) -> None:
    """Draw a two-by-one state-distribution panel at every displayed node."""
    for node_index, node in enumerate(nodes):
        left, bottom, width, height = _node_rectangle(
            node,
            leaf_count=leaf_count,
            maximum_depth=maximum_depth,
            tree_bottom=tree_bottom,
            tree_top=tree_top,
        )
        axes_height = (height - _PANEL_GAP) / 2.0
        for group_index, (_, states) in enumerate(context.groups):
            axes_bottom = bottom + (1 - group_index) * (axes_height + _PANEL_GAP)
            axes_object = context.figure.add_axes(
                (left, axes_bottom, width, axes_height),
                label=f"dendrogram-node-{node_index}-group-{group_index}",
                zorder=1,
            )
            _draw_state_bars(axes_object, context, node, states)
            if group_index == 0:
                axes_object.text(
                    0.0,
                    1.02,
                    _node_title(node),
                    ha="left",
                    va="bottom",
                    transform=axes_object.transAxes,
                )


def _node_rectangle(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    *,
    leaf_count: int,
    maximum_depth: int,
    tree_bottom: float,
    tree_top: float,
) -> tuple[float, float, float, float]:
    """Return one node-panel rectangle in normalized figure coordinates."""
    width = min(_MAX_NODE_WIDTH, _NODE_WIDTH_BUDGET / leaf_count)
    available_height = tree_top - tree_bottom
    height = min(
        _MAX_NODE_HEIGHT,
        _NODE_HEIGHT_BUDGET * available_height / (maximum_depth + 1),
    )
    if leaf_count == 1:
        left = 0.5 - width / 2.0
    else:
        horizontal_span = 1.0 - 2.0 * _HORIZONTAL_MARGIN - width
        left = _HORIZONTAL_MARGIN + horizontal_span * node.order / (leaf_count - 1)
    top_center = tree_top - height / 2.0
    bottom_center = tree_bottom + height / 2.0
    if maximum_depth == 0:
        center = (top_center + bottom_center) / 2.0
    else:
        center = top_center - (
            (top_center - bottom_center) * node.depth / maximum_depth
        )
    return left, center - height / 2.0, width, height


def _node_title(
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
) -> str:
    """Return a compact cluster label and member count."""
    cluster_label = "" if node.leaf_label is None else f"C{node.leaf_label} · "
    return f"{cluster_label}n={len(node.members)}"


def _draw_state_bars(
    axes_object: matplotlib.axes.Axes,
    context: _PlotContext,
    node: athenspop.clustering.hierarchical.CutDendrogramNode,
    states: tuple[str, ...],
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
    axes_object.set_xticks([])
    axes_object.set_yticks([])
    for spine in axes_object.spines.values():
        spine.set_visible(True)


def _draw_legends(context: _PlotContext) -> tuple[matplotlib.legend.Legend, ...]:
    """Draw and return one figure-level legend for each distribution panel."""
    legends: list[matplotlib.legend.Legend] = []
    for legend_index, (group_title, states) in enumerate(reversed(context.groups)):
        handles = [
            matplotlib.patches.Patch(
                facecolor=context.colors[state], label=context.labels[state]
            )
            for state in states
        ]
        legends.append(
            context.figure.legend(
                handles=handles,
                title=group_title,
                loc="lower left" if legend_index == 0 else "lower right",
                bbox_to_anchor=(0.01 if legend_index == 0 else 0.99, 0.01),
            )
        )
    return tuple(legends)


def _tree_vertical_bounds(
    figure_object: matplotlib.figure.Figure,
    legends: tuple[matplotlib.legend.Legend, ...],
    *,
    title_artist: matplotlib.text.Text | None,
) -> tuple[float, float]:
    """Return tree bounds that clear the rendered legends and title."""
    renderer = figure_object.draw_without_rendering()
    inverse_transform = figure_object.transFigure.inverted()
    tree_bottom = (
        max(
            legend.get_window_extent(renderer).transformed(inverse_transform).y1
            for legend in legends
        )
        + _VERTICAL_MARGIN
    )
    label_height = float(plt.rcParams["font.size"]) / (
        72.0 * figure_object.get_figheight()
    )
    if title_artist is None:
        tree_top = 1.0 - label_height - _VERTICAL_MARGIN
    else:
        title_bottom = (
            title_artist.get_window_extent(renderer).transformed(inverse_transform).y0
        )
        tree_top = title_bottom - label_height - _VERTICAL_MARGIN
    return tree_bottom, tree_top


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
    """Return the two validated state groups rendered at every node."""
    states = _states(sequences)
    if requested_groups is None:
        travel_states = tuple(state for state in states if state.startswith("trip_"))
        activity_states = tuple(
            state for state in states if not state.startswith("trip_")
        )
        if not travel_states or not activity_states:
            raise ValueError(
                "`state_groups` must define exactly two groups when both activity "
                "and `trip_`-prefixed travel states cannot be inferred."
            )
        return (
            ("Travel states", travel_states),
            ("Activity states", activity_states),
        )
    if len(requested_groups) != 2:
        raise ValueError(
            "`state_groups` must contain exactly two groups when provided."
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
