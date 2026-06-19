"""Matplotlib cut-dendrogram visualization for temporal state distributions."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from athenspop.clustering import CutDendrogramNode, LinkageMatrix, cut_dendrogram_tree

_DEFAULT_COLORS: tuple[str, ...] = (
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
    "#1B9E77",
    "#D95F02",
    "#7570B3",
    "#E7298A",
    "#66A61E",
    "#E6AB02",
)


@dataclass(frozen=True, slots=True)
class TemporalDendrogramPlotStyle:
    """Display settings for a cut dendrogram with temporal state panels.

    Attributes:
        title:
            Figure title.
        state_groups:
            Optional mapping from panel title to state names included in that panel.
        state_colors:
            Optional explicit color mapping keyed by raw state name.
        state_labels:
            Optional display-label mapping keyed by raw state name.
        leaf_spacing:
            Horizontal distance between displayed cut leaves.
        node_width:
            Width of each temporal panel in axis units.
        panel_height:
            Height of each temporal panel in axis units.
        panel_gap:
            Vertical gap between stacked temporal panels.
        label_height:
            Reserved height above each node for text labels.
        depth_spacing:
            Vertical distance between displayed tree depths.
        margin_x:
            Horizontal axis margin.
        margin_top:
            Vertical margin above the root node.
    """

    title: str = "Cut dendrogram with temporal state distributions"
    state_groups: Mapping[str, Sequence[str]] | None = None
    state_colors: Mapping[str, str] | None = None
    state_labels: Mapping[str, str] | None = None
    leaf_spacing: float = 1.35
    node_width: float = 1.0
    panel_height: float = 0.26
    panel_gap: float = 0.08
    label_height: float = 0.44
    depth_spacing: float = 1.25
    margin_x: float = 0.35
    margin_top: float = 0.25


@dataclass(frozen=True, slots=True)
class _PlotContext:
    """Shared drawing inputs for one temporal dendrogram figure."""

    axes: Axes
    sequences: tuple[tuple[str, ...], ...]
    groups: tuple[tuple[str, tuple[str, ...]], ...]
    colors: Mapping[str, str]
    labels: Mapping[str, str]
    style: TemporalDendrogramPlotStyle


def plot_cut_dendrogram_state_distribution(
    linkage_matrix: LinkageMatrix,
    sequences: Sequence[Sequence[str]],
    *,
    n_clusters: int,
    style: TemporalDendrogramPlotStyle | None = None,
) -> Figure:
    """Plot a cut dendrogram whose displayed nodes contain temporal state distributions.

    Args:
        linkage_matrix:
            SciPy linkage matrix defining the hierarchy over the supplied observations.
        sequences:
            Equal-length state sequences aligned with the observations used to compute `linkage_matrix`.
        n_clusters:
            Number of displayed cut clusters.
        style:
            Optional display settings, including optional state grouping and labels.

    Returns:
        Matplotlib figure containing one axis with a generic cut-dendrogram visualization.

    Raises:
        ValueError:
            If the sequence count does not match the linkage observation count, if sequences are not equal length, or if a state group names a state that does not appear in `sequences`.

    Notes:
        The function returns a figure and never writes files.
        Callers own survey-specific state grouping, colors, labels, and figure export.
    """
    resolved_style = TemporalDendrogramPlotStyle() if style is None else style
    materialized_sequences = _materialize_sequences(sequences)
    expected_sequence_count = int(linkage_matrix.shape[0]) + 1
    if len(materialized_sequences) != expected_sequence_count:
        raise ValueError(f"`sequences` must contain {expected_sequence_count} rows for this linkage matrix, got {len(materialized_sequences)}.")

    groups = _state_groups(materialized_sequences, resolved_style.state_groups)
    tree = cut_dendrogram_tree(linkage_matrix, n_clusters=n_clusters)
    nodes = _display_nodes(tree)
    leaves = tuple(node for node in nodes if node.is_leaf)
    max_depth = max(node.depth for node in nodes)
    node_height = resolved_style.label_height + len(groups) * resolved_style.panel_height + max(0, len(groups) - 1) * resolved_style.panel_gap
    width_units = resolved_style.margin_x * 2 + resolved_style.node_width + max(0, len(leaves) - 1) * resolved_style.leaf_spacing
    height_units = resolved_style.margin_top * 2 + node_height + max_depth * resolved_style.depth_spacing

    figure_width = max(6.0, width_units * 1.35)
    figure_height = max(4.0, height_units * 1.35)
    figure, axes = plt.subplots(figsize=(figure_width, figure_height))
    axes.set_title(resolved_style.title, loc="left")
    axes.set_xlim(0.0, width_units)
    axes.set_ylim(height_units, 0.0)
    axes.axis("off")

    colors = _state_color_map(materialized_sequences, resolved_style)
    labels = _state_label_map(materialized_sequences, resolved_style)
    context = _PlotContext(
        axes=axes,
        sequences=materialized_sequences,
        groups=groups,
        colors=colors,
        labels=labels,
        style=resolved_style,
    )

    _draw_edges(axes, tree, resolved_style)
    for node in nodes:
        _draw_node(context, node)

    _draw_legend(context, width_units=width_units, height_units=height_units)
    figure.tight_layout()
    return figure


def _draw_edges(axes: Axes, node: CutDendrogramNode, style: TemporalDendrogramPlotStyle) -> None:
    """Draw orthogonal edges for one displayed subtree."""
    if node.is_leaf:
        return
    left = _required_child(node.left)
    right = _required_child(node.right)
    _draw_edge(axes, node, left, style)
    _draw_edge(axes, node, right, style)
    _draw_edges(axes, left, style)
    _draw_edges(axes, right, style)


def _draw_edge(axes: Axes, parent: CutDendrogramNode, child: CutDendrogramNode, style: TemporalDendrogramPlotStyle) -> None:
    """Draw one orthogonal edge between displayed nodes."""
    parent_x, parent_y = _node_anchor_bottom(parent, style)
    child_x, child_y = _node_anchor_top(child, style)
    middle_y = parent_y + (child_y - parent_y) * 0.42
    axes.plot((parent_x, parent_x, child_x, child_x), (parent_y, middle_y, middle_y, child_y), color="#707070", linewidth=1.0)


def _draw_node(
    context: _PlotContext,
    node: CutDendrogramNode,
) -> None:
    """Draw labels and temporal panels for one displayed node."""
    x, y = _node_top_left(node, context.style)
    text_lines = [f"height {node.normalized_height:.2f}", f"n {len(node.members)}"]
    if node.leaf_label is not None:
        text_lines.insert(0, f"cluster {node.leaf_label}")
    for line_index, text in enumerate(text_lines):
        context.axes.text(x, y + 0.12 + line_index * 0.14, text, fontsize=7, ha="left", va="center")

    panel_y = y + context.style.label_height
    for title, states in context.groups:
        _draw_panel(context, node, states, x=x, y=panel_y)
        context.axes.text(x + context.style.node_width + 0.04, panel_y + context.style.panel_height / 2.0, title, fontsize=6, ha="left", va="center")
        panel_y += context.style.panel_height + context.style.panel_gap


def _draw_panel(
    context: _PlotContext,
    node: CutDendrogramNode,
    states: tuple[str, ...],
    *,
    x: float,
    y: float,
) -> None:
    """Draw one stacked temporal state distribution panel."""
    context.axes.add_patch(Rectangle((x, y), context.style.node_width, context.style.panel_height, facecolor="#FFFFFF", edgecolor="#202020", linewidth=0.6))
    if not states:
        return
    bin_count = len(context.sequences[0])
    bin_width = context.style.node_width / bin_count
    shares = _state_shares(node, context.sequences, states)
    for bin_index in range(bin_count):
        bar_x = x + bin_index * bin_width
        bar_top = y + context.style.panel_height
        for state in states:
            share = shares.get((bin_index, state), 0.0)
            if share <= 0.0:
                continue
            bar_height = share * context.style.panel_height
            bar_top -= bar_height
            context.axes.add_patch(Rectangle((bar_x, bar_top), bin_width, bar_height, facecolor=context.colors[state], edgecolor="none"))


def _draw_legend(
    context: _PlotContext,
    *,
    width_units: float,
    height_units: float,
) -> None:
    """Draw a compact state legend inside the lower figure margin."""
    legend_x = 0.15
    legend_y = height_units - 0.28
    entry_index = 0
    for _, states in context.groups:
        for state in states:
            x = legend_x + (entry_index % 4) * (width_units / 4.0)
            y = legend_y + (entry_index // 4) * 0.18
            context.axes.add_patch(Rectangle((x, y - 0.07), 0.1, 0.1, facecolor=context.colors[state], edgecolor="none"))
            context.axes.text(x + 0.13, y, context.labels[state], fontsize=6, ha="left", va="center")
            entry_index += 1


def _state_shares(node: CutDendrogramNode, sequences: tuple[tuple[str, ...], ...], states: tuple[str, ...]) -> dict[tuple[int, str], float]:
    """Return within-node state shares by time bin."""
    state_set = set(states)
    counts: dict[tuple[int, str], int] = {}
    for member in node.members:
        for bin_index, state in enumerate(sequences[member]):
            if state in state_set:
                counts[(bin_index, state)] = counts.get((bin_index, state), 0) + 1
    denominator = len(node.members)
    return {key: count / denominator for key, count in counts.items()}


def _materialize_sequences(sequences: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    """Materialize and validate equal-length state sequences."""
    materialized = tuple(tuple(str(state) for state in sequence) for sequence in sequences)
    if not materialized:
        raise ValueError("At least one state sequence is required.")
    sequence_length = len(materialized[0])
    for sequence in materialized:
        if len(sequence) != sequence_length:
            raise ValueError("All state sequences must have the same length.")
    return materialized


def _state_groups(
    sequences: tuple[tuple[str, ...], ...],
    requested_groups: Mapping[str, Sequence[str]] | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return validated state groups for panel rendering."""
    states = _states(sequences)
    if requested_groups is None:
        return (("States", states),)
    state_set = set(states)
    groups: list[tuple[str, tuple[str, ...]]] = []
    for title, group_states in requested_groups.items():
        materialized_group = tuple(str(state) for state in group_states)
        unknown = sorted(set(materialized_group) - state_set)
        if unknown:
            raise ValueError(f"State group {title!r} contains unknown state(s): {', '.join(unknown)}.")
        groups.append((str(title), materialized_group))
    return tuple(groups)


def _states(sequences: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    """Return sorted unique states from materialized sequences."""
    return tuple(sorted({state for sequence in sequences for state in sequence}))


def _state_color_map(sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramPlotStyle) -> dict[str, str]:
    """Return a complete state color mapping."""
    explicit_colors = {} if style.state_colors is None else dict(style.state_colors)
    return {state: explicit_colors.get(state, _DEFAULT_COLORS[index % len(_DEFAULT_COLORS)]) for index, state in enumerate(_states(sequences))}


def _state_label_map(sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramPlotStyle) -> dict[str, str]:
    """Return a complete state label mapping."""
    explicit_labels = {} if style.state_labels is None else dict(style.state_labels)
    return {state: explicit_labels.get(state, state.replace("_", " ").title()) for state in _states(sequences)}


def _display_nodes(root: CutDendrogramNode) -> tuple[CutDendrogramNode, ...]:
    """Return displayed nodes in parent-before-child order."""
    nodes = [root]
    if root.left is not None:
        nodes.extend(_display_nodes(root.left))
    if root.right is not None:
        nodes.extend(_display_nodes(root.right))
    return tuple(nodes)


def _node_top_left(node: CutDendrogramNode, style: TemporalDendrogramPlotStyle) -> tuple[float, float]:
    """Return top-left coordinates for one displayed node."""
    center_x = style.margin_x + style.node_width / 2.0 + node.order * style.leaf_spacing
    top_y = style.margin_top + node.depth * style.depth_spacing
    return center_x - style.node_width / 2.0, top_y


def _node_anchor_top(node: CutDendrogramNode, style: TemporalDendrogramPlotStyle) -> tuple[float, float]:
    """Return the top edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node, style)
    return x + style.node_width / 2.0, y + style.label_height


def _node_anchor_bottom(node: CutDendrogramNode, style: TemporalDendrogramPlotStyle) -> tuple[float, float]:
    """Return the bottom edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node, style)
    panel_count = 1 if style.state_groups is None else len(style.state_groups)
    return x + style.node_width / 2.0, y + style.label_height + panel_count * style.panel_height + max(0, panel_count - 1) * style.panel_gap


def _required_child(node: CutDendrogramNode | None) -> CutDendrogramNode:
    """Return a required immutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node
