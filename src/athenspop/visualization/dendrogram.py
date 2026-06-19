"""Cut dendrogram visualizations with temporal state-distribution nodes."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

import pandas as pd
from scipy.cluster.hierarchy import ClusterNode, to_tree

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from os import PathLike

    from athenspop.clustering import LinkageMatrix

type _NodeHeapEntry = tuple[float, int, ClusterNode]
type _DisplayNodeHeapEntry = tuple[float, int, "_DisplayNode"]

_DEFAULT_STATE_COLORS: Final[tuple[str, ...]] = (
    "#7FC97F",
    "#BEAED4",
    "#FDC086",
    "#FFFF99",
    "#386CB0",
    "#F0027F",
    "#BF5B17",
    "#666666",
    "#1B9E77",
    "#D95F02",
    "#7570B3",
    "#E7298A",
    "#66A61E",
    "#E6AB02",
    "#A6761D",
    "#A6CEE3",
)
_DEFAULT_NAMED_STATE_COLORS: Final[dict[str, str]] = {
    "education": "#7FC97F",
    "work": "#BEAED4",
    "market": "#FDC086",
    "recreation": "#FFFF99",
    "service": "#386CB0",
    "home": "#F0027F",
    "other": "#BF5B17",
    "trip_car": "#7FC97F",
    "trip_motorcycle": "#BEAED4",
    "trip_taxi": "#FDC086",
    "trip_bus": "#FFFF99",
    "trip_train": "#386CB0",
    "trip_bicycle": "#F0027F",
    "trip_escooter": "#BF5B17",
    "trip_walk": "#666666",
}
_SVG_FONT: Final[str] = "Arial, sans-serif"
_EMPTY_PANEL_FILL: Final[str] = "#FFFFFF"
_PANEL_STROKE: Final[str] = "#111111"
_EDGE_STROKE: Final[str] = "#8A8A8A"
_TEXT_FILL: Final[str] = "#111111"


@dataclass(frozen=True, slots=True)
class CutDendrogramNode:
    """One displayed node in a dendrogram cut at a requested number of clusters.

    Attributes:
        members: Original observation indices contained in the displayed node.
        height: Raw linkage height for the represented SciPy tree node.
        normalized_height: `height` divided by the root linkage height, with zero roots reported as zero.
        order: Horizontal order used by the cut-tree renderer, where displayed leaves occupy consecutive integer positions and internal nodes are centered over their children.
        depth: Vertical split-order depth, where the root has depth zero and later displayed splits receive larger depths.
        is_leaf: Whether this displayed node is a cut cluster or singleton leaf rather than an expanded internal split.
        leaf_label: One-based cut-cluster label for displayed leaves, or `None` for expanded internal nodes.
        left: Left displayed child when the node is expanded.
        right: Right displayed child when the node is expanded.
    """

    members: tuple[int, ...]
    height: float
    normalized_height: float
    order: float
    depth: int
    is_leaf: bool
    leaf_label: int | None
    left: CutDendrogramNode | None
    right: CutDendrogramNode | None


@dataclass(frozen=True, slots=True)
class TemporalDendrogramStyle:
    """Configuration for SVG dendrogram distribution rendering.

    Attributes:
        title: Figure title written at the top-left of the SVG.
        mode_prefix: State prefix used to separate travel-mode states from activity-purpose states.
        state_colors: Optional explicit color mapping keyed by raw state name.
        state_labels: Optional explicit display-label mapping keyed by raw state name.
        leaf_spacing: Horizontal distance in SVG units between neighboring cut leaves.
        node_width: Width in SVG units of each temporal distribution panel.
        panel_height: Height in SVG units of each purpose or mode panel.
        panel_gap: Vertical gap in SVG units between the travel-mode panel and the activity-purpose panel.
        label_height: Reserved height in SVG units above each node panel for node annotations.
        depth_spacing: Vertical distance in SVG units between split-order levels.
        margin_x: Horizontal page margin in SVG units.
        margin_top: Top page margin in SVG units.
        legend_margin_top: Gap in SVG units between the deepest node and the legend.
    """

    title: str = "Cut dendrogram with temporal state distributions"
    mode_prefix: str = "trip_"
    state_colors: Mapping[str, str] | None = None
    state_labels: Mapping[str, str] | None = None
    leaf_spacing: int = 132
    node_width: int = 104
    panel_height: int = 24
    panel_gap: int = 4
    label_height: int = 44
    depth_spacing: int = 120
    margin_x: int = 36
    margin_top: int = 36
    legend_margin_top: int = 48


@dataclass(slots=True)
class _DisplayNode:
    """Mutable construction node used before freezing a public `CutDendrogramNode`."""

    linkage_node: ClusterNode
    is_leaf: bool
    left: _DisplayNode | None = None
    right: _DisplayNode | None = None
    order: float = 0.0
    depth: int = 0


@dataclass(frozen=True, slots=True)
class _PanelSpec:
    """Panel placement and state selection for one temporal distribution panel."""

    states: tuple[str, ...]
    x: float
    y: float
    css_class: str


def cluster_time_distribution(sequences: Sequence[Sequence[str]], labels: Sequence[int]) -> pd.DataFrame:
    """Return temporal state shares by cluster and sequence time bin.

    Args:
        sequences: Equal-length state sequences aligned with `labels`.
        labels: Positive integer cluster labels aligned with `sequences`.

    Returns:
        Dataframe with `cluster`, `bin_index`, `state`, `count`, and `share` columns.

    Raises:
        ValueError: If `sequences` and `labels` have different lengths, or if the sequences are not equal length.
    """
    materialized_sequences = _materialize_sequences(sequences)
    label_tuple = tuple(int(label) for label in labels)
    if len(materialized_sequences) != len(label_tuple):
        raise ValueError(f"`sequences` and `labels` must have the same length, got {len(materialized_sequences)} and {len(label_tuple)}.")
    counts: dict[tuple[int, int, str], int] = {}
    totals: dict[tuple[int, int], int] = {}
    for sequence, label in zip(materialized_sequences, label_tuple, strict=True):
        for bin_index, state in enumerate(sequence):
            counts[(label, bin_index, state)] = counts.get((label, bin_index, state), 0) + 1
            totals[(label, bin_index)] = totals.get((label, bin_index), 0) + 1
    return pd.DataFrame(
        [
            {
                "cluster": cluster,
                "bin_index": bin_index,
                "state": state,
                "count": count,
                "share": count / totals[(cluster, bin_index)],
            }
            for (cluster, bin_index, state), count in sorted(counts.items())
        ],
        columns=["cluster", "bin_index", "state", "count", "share"],
    )


def cut_dendrogram_tree(linkage_matrix: LinkageMatrix, *, n_clusters: int) -> CutDendrogramNode:
    """Return the displayed hierarchy after cutting a linkage tree to `n_clusters` leaves.

    The cut is constructed top-down by repeatedly splitting the currently displayed node with the largest linkage height until the requested number of displayed leaves is reached. This gives an explicit tree of the nodes that should be drawn, instead of returning full-dendrogram geometry.

    Args:
        linkage_matrix: SciPy linkage matrix.
        n_clusters: Requested number of displayed clusters.

    Returns:
        Root node of the displayed cut dendrogram.

    Raises:
        ValueError: If `n_clusters` is not positive or if `linkage_matrix` is empty.
    """
    if n_clusters <= 0:
        raise ValueError(f"`n_clusters` must be positive, got {n_clusters}.")
    if linkage_matrix.shape[0] == 0:
        raise ValueError("A cut dendrogram requires a linkage matrix with at least one merge.")
    root = cast("ClusterNode", to_tree(linkage_matrix))
    target_clusters = min(n_clusters, int(linkage_matrix.shape[0]) + 1)
    cut_node_ids = _cut_node_ids(root, target_clusters)
    display_root = _build_display_tree(root, cut_node_ids)
    _assign_orders(display_root, next_order=0)
    _assign_depths(display_root)
    root_height = float(root.dist)
    return _freeze_display_tree(display_root, root_height=root_height, next_leaf_label=1)[0]


def cut_dendrogram_distribution_svg(
    linkage_matrix: LinkageMatrix,
    sequences: Sequence[Sequence[str]],
    *,
    n_clusters: int,
    style: TemporalDendrogramStyle | None = None,
) -> str:
    """Render a cut dendrogram whose nodes contain temporal purpose and mode distributions.

    Args:
        linkage_matrix: SciPy linkage matrix defining the observation hierarchy.
        sequences: Equal-length state sequences aligned with the observations used to compute `linkage_matrix`.
        n_clusters: Number of displayed cut clusters.
        style: Optional renderer configuration.

    Returns:
        Complete SVG document text.

    Raises:
        ValueError: If the sequence count does not match the linkage observation count.
    """
    resolved_style = TemporalDendrogramStyle() if style is None else style
    materialized_sequences = _materialize_sequences(sequences)
    expected_sequence_count = int(linkage_matrix.shape[0]) + 1
    if len(materialized_sequences) != expected_sequence_count:
        raise ValueError(f"`sequences` must contain {expected_sequence_count} rows for this linkage matrix, got {len(materialized_sequences)}.")
    tree = cut_dendrogram_tree(linkage_matrix, n_clusters=n_clusters)
    return _render_cut_tree_svg(tree, materialized_sequences, resolved_style)


def write_cut_dendrogram_distribution_svg(
    linkage_matrix: LinkageMatrix,
    sequences: Sequence[Sequence[str]],
    path: str | PathLike[str],
    *,
    n_clusters: int,
    style: TemporalDendrogramStyle | None = None,
) -> None:
    """Write a cut dendrogram temporal-distribution SVG file.

    Args:
        linkage_matrix: SciPy linkage matrix defining the observation hierarchy.
        sequences: Equal-length state sequences aligned with the observations used to compute `linkage_matrix`.
        path: Destination SVG path.
        n_clusters: Number of displayed cut clusters.
        style: Optional renderer configuration.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cut_dendrogram_distribution_svg(linkage_matrix, sequences, n_clusters=n_clusters, style=style), encoding="utf-8")


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


def _cut_node_ids(root: ClusterNode, target_clusters: int) -> set[int]:
    """Select displayed leaf node IDs by top-down largest-height splitting."""
    displayed_leaf_ids = {int(root.id)}
    heap: list[_NodeHeapEntry] = []
    if not root.is_leaf():
        heappush(heap, (-float(root.dist), int(root.id), root))
    while len(displayed_leaf_ids) < target_clusters and heap:
        _, _, node = heappop(heap)
        node_id = int(node.id)
        if node_id not in displayed_leaf_ids or node.is_leaf():
            continue
        displayed_leaf_ids.remove(node_id)
        left = _left_child(node)
        right = _right_child(node)
        displayed_leaf_ids.add(int(left.id))
        displayed_leaf_ids.add(int(right.id))
        if not left.is_leaf():
            heappush(heap, (-float(left.dist), int(left.id), left))
        if not right.is_leaf():
            heappush(heap, (-float(right.dist), int(right.id), right))
    return displayed_leaf_ids


def _build_display_tree(node: ClusterNode, cut_node_ids: set[int]) -> _DisplayNode:
    """Build the mutable displayed tree from selected cut-node IDs."""
    if int(node.id) in cut_node_ids or node.is_leaf():
        return _DisplayNode(linkage_node=node, is_leaf=True)
    left = _build_display_tree(_left_child(node), cut_node_ids)
    right = _build_display_tree(_right_child(node), cut_node_ids)
    return _DisplayNode(linkage_node=node, is_leaf=False, left=left, right=right)


def _assign_orders(node: _DisplayNode, *, next_order: int) -> int:
    """Assign left-to-right displayed leaf orders and centered internal orders."""
    if node.is_leaf:
        node.order = float(next_order)
        return next_order + 1
    left = _required_child(node.left)
    right = _required_child(node.right)
    next_after_left = _assign_orders(left, next_order=next_order)
    next_after_right = _assign_orders(right, next_order=next_after_left)
    node.order = (left.order + right.order) / 2.0
    return next_after_right


def _assign_depths(root: _DisplayNode) -> None:
    """Assign split-order depths to displayed nodes."""
    root.depth = 0
    heap: list[_DisplayNodeHeapEntry] = []
    if not root.is_leaf:
        heappush(heap, (-float(root.linkage_node.dist), int(root.linkage_node.id), root))
    next_depth = 0
    while heap:
        _, _, node = heappop(heap)
        next_depth += 1
        left = _required_child(node.left)
        right = _required_child(node.right)
        left.depth = next_depth
        right.depth = next_depth
        if not left.is_leaf:
            heappush(heap, (-float(left.linkage_node.dist), int(left.linkage_node.id), left))
        if not right.is_leaf:
            heappush(heap, (-float(right.linkage_node.dist), int(right.linkage_node.id), right))


def _freeze_display_tree(node: _DisplayNode, *, root_height: float, next_leaf_label: int) -> tuple[CutDendrogramNode, int]:
    """Convert a mutable display tree into immutable public nodes."""
    normalized_height = 0.0 if root_height <= 0 else float(node.linkage_node.dist) / root_height
    members = tuple(int(member) for member in node.linkage_node.pre_order())
    if node.is_leaf:
        return (
            CutDendrogramNode(
                members=members,
                height=float(node.linkage_node.dist),
                normalized_height=normalized_height,
                order=node.order,
                depth=node.depth,
                is_leaf=True,
                leaf_label=next_leaf_label,
                left=None,
                right=None,
            ),
            next_leaf_label + 1,
        )
    left, next_after_left = _freeze_display_tree(_required_child(node.left), root_height=root_height, next_leaf_label=next_leaf_label)
    right, next_after_right = _freeze_display_tree(_required_child(node.right), root_height=root_height, next_leaf_label=next_after_left)
    return (
        CutDendrogramNode(
            members=members,
            height=float(node.linkage_node.dist),
            normalized_height=normalized_height,
            order=node.order,
            depth=node.depth,
            is_leaf=False,
            leaf_label=None,
            left=left,
            right=right,
        ),
        next_after_right,
    )


def _render_cut_tree_svg(tree: CutDendrogramNode, sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramStyle) -> str:
    """Render an immutable cut tree to SVG."""
    nodes = _display_nodes(tree)
    leaves = tuple(node for node in nodes if node.is_leaf)
    max_depth = max(node.depth for node in nodes)
    node_height = style.label_height + (style.panel_height * 2) + style.panel_gap
    width = max(720, int(style.margin_x * 2 + style.node_width + (len(leaves) - 1) * style.leaf_spacing))
    legend_lines = _legend_lines(sequences, style, y_start=style.margin_top + max_depth * style.depth_spacing + node_height + style.legend_margin_top)
    height = style.margin_top + max_depth * style.depth_spacing + node_height + style.legend_margin_top + max(90, len(legend_lines) * 18)
    colors = _state_color_map(_states(sequences), style)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(style.title)}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF" />',
        f'<text x="{style.margin_x}" y="24" font-family="{_SVG_FONT}" font-size="18" fill="{_TEXT_FILL}">{escape(style.title)}</text>',
    ]
    lines.extend(_edge_lines(tree, style))
    for node in nodes:
        lines.extend(_node_lines(node, sequences, style, colors))
    lines.extend(legend_lines)
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _edge_lines(node: CutDendrogramNode, style: TemporalDendrogramStyle) -> tuple[str, ...]:
    """Return SVG edge lines for a displayed cut tree."""
    if node.is_leaf:
        return ()
    left = _required_public_child(node.left)
    right = _required_public_child(node.right)
    lines = [
        _edge_line(node, left, style),
        _edge_line(node, right, style),
    ]
    lines.extend(_edge_lines(left, style))
    lines.extend(_edge_lines(right, style))
    return tuple(lines)


def _edge_line(parent: CutDendrogramNode, child: CutDendrogramNode, style: TemporalDendrogramStyle) -> str:
    """Return one orthogonal SVG edge between two displayed nodes."""
    parent_x, parent_y = _node_anchor_bottom(parent, style)
    child_x, child_y = _node_anchor_top(child, style)
    mid_y = parent_y + (child_y - parent_y) * 0.42
    points = f"{parent_x:.2f},{parent_y:.2f} {parent_x:.2f},{mid_y:.2f} {child_x:.2f},{mid_y:.2f} {child_x:.2f},{child_y:.2f}"
    return f'<polyline points="{points}" fill="none" stroke="{_EDGE_STROKE}" stroke-width="1.5" />'


def _node_lines(node: CutDendrogramNode, sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramStyle, colors: Mapping[str, str]) -> tuple[str, ...]:
    """Return SVG lines for one displayed node."""
    x, y = _node_top_left(node, style)
    mode_states, purpose_states = _state_groups(sequences, style.mode_prefix)
    mode_y = y + style.label_height
    purpose_y = mode_y + style.panel_height + style.panel_gap
    lines = [
        *(_node_label_lines(node, x, y)),
        *_panel_lines(node, sequences, _PanelSpec(states=mode_states, x=x, y=mode_y, css_class="travel-mode-panel"), style, colors),
        *_panel_lines(node, sequences, _PanelSpec(states=purpose_states, x=x, y=purpose_y, css_class="activity-purpose-panel"), style, colors),
    ]
    return tuple(lines)


def _node_label_lines(node: CutDendrogramNode, x: float, y: float) -> tuple[str, ...]:
    """Return compact node annotations."""
    lines: list[str] = []
    if node.leaf_label is not None:
        lines.append(f'<text x="{x:.2f}" y="{y + 12:.2f}" font-family="{_SVG_FONT}" font-size="12" fill="{_TEXT_FILL}">ID: {node.leaf_label}</text>')
        offset = 26
    else:
        offset = 14
    lines.append(f'<text x="{x:.2f}" y="{y + offset:.2f}" font-family="{_SVG_FONT}" font-size="12" fill="{_TEXT_FILL}">H: {node.normalized_height:.2f}</text>')
    lines.append(f'<text x="{x:.2f}" y="{y + offset + 14:.2f}" font-family="{_SVG_FONT}" font-size="12" fill="{_TEXT_FILL}">Size: {len(node.members)}</text>')
    return tuple(lines)


def _panel_lines(
    node: CutDendrogramNode,
    sequences: tuple[tuple[str, ...], ...],
    spec: _PanelSpec,
    style: TemporalDendrogramStyle,
    colors: Mapping[str, str],
) -> tuple[str, ...]:
    """Return one stacked temporal distribution panel."""
    lines = [
        f'<rect class="{spec.css_class}" x="{spec.x:.2f}" y="{spec.y:.2f}" width="{style.node_width}" height="{style.panel_height}" fill="{_EMPTY_PANEL_FILL}" stroke="{_PANEL_STROKE}" stroke-width="0.8" />'
    ]
    if not spec.states:
        return tuple(lines)
    bin_count = len(sequences[0])
    bin_width = style.node_width / bin_count
    shares = _state_shares(node, sequences, spec.states)
    for bin_index in range(bin_count):
        bar_x = spec.x + bin_index * bin_width
        bar_bottom = spec.y + style.panel_height
        for state in spec.states:
            share = shares.get((bin_index, state), 0.0)
            if share <= 0:
                continue
            bar_height = share * style.panel_height
            bar_bottom -= bar_height
            lines.append(
                f'<rect class="{spec.css_class}-state" x="{bar_x:.2f}" y="{bar_bottom:.2f}" width="{bin_width + 0.02:.2f}" height="{bar_height:.2f}" fill="{colors[state]}" />'
            )
    return tuple(lines)


def _state_shares(node: CutDendrogramNode, sequences: tuple[tuple[str, ...], ...], states: tuple[str, ...]) -> dict[tuple[int, str], float]:
    """Return shares for selected states within a node by time bin."""
    state_set = set(states)
    counts: dict[tuple[int, str], int] = {}
    for member in node.members:
        for bin_index, state in enumerate(sequences[member]):
            if state in state_set:
                counts[(bin_index, state)] = counts.get((bin_index, state), 0) + 1
    denominator = len(node.members)
    return {key: count / denominator for key, count in counts.items()}


def _legend_lines(sequences: tuple[tuple[str, ...], ...], style: TemporalDendrogramStyle, *, y_start: int) -> tuple[str, ...]:
    """Return grouped activity and travel-mode legend lines."""
    states = _states(sequences)
    mode_states, purpose_states = _state_groups(sequences, style.mode_prefix)
    colors = _state_color_map(states, style)
    label_map = _state_label_map(states, style)
    lines: list[str] = []
    x_positions = (style.margin_x, style.margin_x + 210)
    for title, group_states, x_start in (("Activity Purpose", purpose_states, x_positions[0]), ("Travel Mode", mode_states, x_positions[1])):
        lines.append(f'<text x="{x_start}" y="{y_start}" font-family="{_SVG_FONT}" font-size="14" fill="{_TEXT_FILL}">{escape(title)}</text>')
        for row_index, state in enumerate(group_states, start=1):
            y = y_start + row_index * 18
            lines.append(f'<rect x="{x_start}" y="{y - 12}" width="14" height="14" fill="{colors[state]}" />')
            lines.append(f'<text x="{x_start + 20}" y="{y}" font-family="{_SVG_FONT}" font-size="13" fill="{_TEXT_FILL}">{escape(label_map[state])}</text>')
    return tuple(lines)


def _states(sequences: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    """Return sorted unique states from materialized sequences."""
    return tuple(sorted({state for sequence in sequences for state in sequence}))


def _state_groups(sequences: tuple[tuple[str, ...], ...], mode_prefix: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split all sequence states into travel modes and activity purposes."""
    states = _states(sequences)
    mode_states = tuple(state for state in states if _state_without_period(state).startswith(mode_prefix))
    purpose_states = tuple(state for state in states if state not in set(mode_states))
    return mode_states, purpose_states


def _state_color_map(states: tuple[str, ...], style: TemporalDendrogramStyle) -> dict[str, str]:
    """Return a complete state color mapping."""
    explicit_colors = {} if style.state_colors is None else dict(style.state_colors)
    colors: dict[str, str] = {}
    for index, state in enumerate(states):
        normalized = _state_without_period(state).lower()
        colors[state] = explicit_colors.get(
            state, explicit_colors.get(normalized, _DEFAULT_NAMED_STATE_COLORS.get(normalized, _DEFAULT_STATE_COLORS[index % len(_DEFAULT_STATE_COLORS)]))
        )
    return colors


def _state_label_map(states: tuple[str, ...], style: TemporalDendrogramStyle) -> dict[str, str]:
    """Return a complete state label mapping."""
    explicit_labels = {} if style.state_labels is None else dict(style.state_labels)
    labels: dict[str, str] = {}
    for state in states:
        labels[state] = explicit_labels.get(state, explicit_labels.get(_state_without_period(state), _default_state_label(state, style.mode_prefix)))
    return labels


def _default_state_label(state: str, mode_prefix: str) -> str:
    """Return a readable label for a raw sequence state."""
    base_state = _state_without_period(state)
    if base_state.startswith(mode_prefix):
        base_state = base_state.removeprefix(mode_prefix)
    return base_state.replace("_", " ").title()


def _state_without_period(state: str) -> str:
    """Remove an optional period suffix such as `@p1` from a sequence state."""
    return state.split("@", maxsplit=1)[0]


def _display_nodes(root: CutDendrogramNode) -> tuple[CutDendrogramNode, ...]:
    """Return displayed nodes in parent-before-child order."""
    nodes = [root]
    if root.left is not None:
        nodes.extend(_display_nodes(root.left))
    if root.right is not None:
        nodes.extend(_display_nodes(root.right))
    return tuple(nodes)


def _node_top_left(node: CutDendrogramNode, style: TemporalDendrogramStyle) -> tuple[float, float]:
    """Return top-left coordinates for one displayed node."""
    center_x = style.margin_x + style.node_width / 2.0 + node.order * style.leaf_spacing
    top_y = style.margin_top + node.depth * style.depth_spacing
    return center_x - style.node_width / 2.0, top_y


def _node_anchor_top(node: CutDendrogramNode, style: TemporalDendrogramStyle) -> tuple[float, float]:
    """Return the top edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node, style)
    return x + style.node_width / 2.0, y + style.label_height


def _node_anchor_bottom(node: CutDendrogramNode, style: TemporalDendrogramStyle) -> tuple[float, float]:
    """Return the bottom edge anchor for a displayed node's panels."""
    x, y = _node_top_left(node, style)
    return x + style.node_width / 2.0, y + style.label_height + style.panel_height * 2 + style.panel_gap


def _left_child(node: ClusterNode) -> ClusterNode:
    """Return a non-null left child from a SciPy cluster node."""
    left = node.get_left()
    if left is None:
        raise ValueError("Expected a non-leaf SciPy cluster node to have a left child.")
    return cast("ClusterNode", left)


def _right_child(node: ClusterNode) -> ClusterNode:
    """Return a non-null right child from a SciPy cluster node."""
    right = node.get_right()
    if right is None:
        raise ValueError("Expected a non-leaf SciPy cluster node to have a right child.")
    return cast("ClusterNode", right)


def _required_child(node: _DisplayNode | None) -> _DisplayNode:
    """Return a required mutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node


def _required_public_child(node: CutDendrogramNode | None) -> CutDendrogramNode:
    """Return a required immutable displayed child."""
    if node is None:
        raise ValueError("Expanded displayed dendrogram nodes must have both children.")
    return node
