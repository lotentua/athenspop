# Method reference

This page records the package's computational definitions and their interpretation boundaries. Public API docstrings define argument-level behavior.

## Schedule realization

For each trip, $[E_i,L_i]$ is its own inclusive departure interval and $B_i$ is the latest departure retained by the reverse pass. Given a successor and known duration $\tau_i$,

$$
B_i=\min\left(L_i, B_{i+1}-m-\tau_i\right),
$$

with the applicable observation-horizon arrival target included in the same minimum. A deterministic FIFO travel-time function uses bisection to find the greatest departure whose arrival respects that target.

The forward pass sets $F_1=0$ and $F_i=a_{i-1}+m$, then draws an uncertain departure from

$$
\left[
\max(E_i,F_i),
\min(L_i,B_i,H_d)
\right]\cap\mathbb Z.
$$

Concrete departures are checked rather than redrawn. Each random draw is uniform only over the current locally admissible interval. The resulting diary distribution is induced by sequential conditional draws, not a uniform distribution over complete feasible schedules. When callable refinement is unavailable or disabled, a failed realization does not establish global diary infeasibility.

A fixed positive `travel_time_seconds` determines arrival directly. Otherwise, the scheduler evaluates a user-supplied `TravelTimeFunction(origin, destination, mode, departure_second)`. Callable refinement by bisection assumes deterministic first-in, first-out arrival behavior over the searched window. See [Scheduling](../concepts/scheduling.md) for the equations and policy boundaries.

## Episode discretization

Episodes use half-open time intervals. For a sequence bin $B$, the selected state is

$$
\operatorname*{arg\,max}_{s}\sum_{E:\,\operatorname{state}(E)=s}|E\cap B|.
$$

The sum permits several episodes with the same label to contribute within one bin. Ties are resolved by the earliest start among contributing episodes. This deterministic rule avoids dependence on container ordering, but it remains a representation choice rather than an empirical estimate.

## Optimal matching

The package implements the Wagner-Fischer recurrence stated in [Sequences and clustering](../concepts/sequences.md#optimal-matching-dissimilarity). `athenspop.sequence.distance.optimal_matching_dissimilarity` supports directed substitution mappings for one ordered comparison. `athenspop.sequence.distance.dissimilarity_matrix` additionally requires reverse costs to match within numerical tolerance because it constructs a symmetric matrix.

The implementation uses two dynamic-programming rows for one comparison. Matrix construction encodes states once and batches equal-length targets. The mathematical result remains the minimum edit cost. It is not divided by sequence length.

## Hierarchical clustering

`athenspop.clustering.hierarchical.average_linkage` delegates the hierarchy to `scipy.cluster.hierarchy.linkage` after validating a finite, symmetric, nonnegative matrix with a zero diagonal. Average linkage uses the mean of all cross-cluster pairwise dissimilarities. SciPy's linkage matrix records the merged child identifiers, merge height, and resulting observation count.

`flat_cluster_labels` constructs a top-down cut by splitting the currently displayed node with the largest merge height until the requested count is reached. Labels follow displayed leaf order and begin at one. A requested count cannot exceed the number of observations.

`cophenetic_correlation` is the Pearson correlation between the source condensed dissimilarities and the cophenetic distances implied by the hierarchy. It is undefined when either vector is constant or has fewer than two values. It measures how the hierarchy preserves pairwise dissimilarities. It does not select a cluster count.

## Complexity

For sequence lengths $n$ and $m$, one scalar optimal-matching comparison uses $O(nm)$ arithmetic and $O(m)$ dynamic-programming storage. Pairwise construction batches $B$ equal-length targets and uses $O(Bm)$ dynamic-programming working storage for that batch, in addition to the $O(N^2)$ output matrix for $N$ sequences. The complete matrix contains $N(N-1)/2$ comparisons. SciPy documents $O(N^2)$ time and memory for its average-linkage implementation [2]. These quadratic terms are the main scaling boundary for large diary collections.

## References

1. R. A. Wagner and M. J. Fischer present the recurrence in [The string-to-string correction problem](https://doi.org/10.1145/321796.321811), published in *Journal of the ACM*, 21(1), 168-173 (1974).
2. The SciPy community documents its linkage implementation in the [hierarchical clustering linkage reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html).
