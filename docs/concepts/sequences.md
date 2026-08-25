# Sequences and clustering

Scheduled diaries can be represented as continuous episodes or fixed-interval symbolic sequences. The state vocabulary, observation window, interval width, edit costs, and cluster cut are analytical choices. They should be declared with the result because each choice can change the comparison.

## Episodes and intervals

`athenspop.sequence.episodes.episodes_from_diary` partitions an observation window into half-open activity and travel episodes $[s,e)$. The initial activity state covers the time before the first trip. Each trip contributes a travel state, and its destination purpose becomes the next activity state. The default travel label is `trip_{mode}`, which keeps movement labels distinct from activity labels.

`athenspop.sequence.episodes.discretize_episodes` assigns each fixed-width interval to the state with the greatest total overlap. If several states have equal overlap, the state whose first contributing episode begins earliest wins. The last interval may be shorter when the window duration is not divisible by the interval width.

Short intervals preserve more temporal detail and produce longer sequences. Long intervals reduce temporal resolution and computation. The package does not choose a resolution from the data.

## Optimal-matching dissimilarity

For sequences $x=(x_1,\ldots,x_n)$ and $y=(y_1,\ldots,y_m)$, `athenspop.sequence.distance.optimal_matching_dissimilarity` uses the Wagner-Fischer dynamic program. Let $D_{i,j}$ be the minimum edit cost between the first $i$ and $j$ states, let $g>0$ be the insertion/deletion cost, and let $c(x_i,y_j)\ge0$ be the substitution cost. The boundary conditions are

$$
D_{i,0}=ig, \qquad D_{0,j}=jg,
$$

and the recurrence is

$$
D_{i,j}=\min\begin{cases}
D_{i-1,j}+g,\\
D_{i,j-1}+g,\\
D_{i-1,j-1}+c(x_i,y_j).
\end{cases}
$$

The returned dissimilarity is $D_{n,m}$. Identical states have zero substitution cost. Pairwise matrices require symmetric costs because the output is a symmetric dissimilarity matrix. The implementation does not normalize by sequence length, so longer sequences can admit larger values under the same costs. The recurrence follows Wagner and Fischer's minimum-cost edit formulation [1].

## Average-linkage clustering

`athenspop.clustering.hierarchical.average_linkage` converts a validated square dissimilarity matrix to SciPy's condensed form and performs agglomerative average linkage. For clusters $U$ and $V$, the inter-cluster dissimilarity is

$$
d(U,V)=\frac{1}{|U||V|}\sum_{u\in U}\sum_{v\in V}d(u,v).
$$

At each step, the algorithm merges a pair with minimum current inter-cluster dissimilarity. SciPy documents that tied minima can be resolved differently from some other implementations [2]. `optimal_ordering=True` changes leaf order for display. It does not change cluster membership or merge heights.

`flat_cluster_labels` cuts the hierarchy to an analyst-specified number of displayed clusters. That number is not estimated as an optimum. `cophenetic_correlation` measures the correlation between source dissimilarities and the hierarchy's cophenetic distances when both vary, but a high value alone does not establish an interpretable or substantively useful cut.

## Summaries and visualization

`cluster_size_summary` counts observations. `cluster_state_distribution` counts all state tokens, so longer sequences contribute more tokens when sequence lengths differ. `cluster_time_distribution` requires equal-length sequences and reports within-cluster state shares at each bin.

`athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution` returns a Matplotlib figure. It inherits figure size, fonts, lines, and default colors from the active Matplotlib stylesheet. Optional style values are limited to a title and explicit state groups, colors, or labels. The caller owns display context, export format, and accessibility checks for any custom palette.

## References

1. R. A. Wagner and M. J. Fischer present the recurrence in [The string-to-string correction problem](https://doi.org/10.1145/321796.321811), published in *Journal of the ACM*, 21(1), 168-173 (1974).
2. The SciPy community documents its linkage implementation in the [hierarchical clustering linkage reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html).
