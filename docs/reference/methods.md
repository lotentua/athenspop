# Method reference

This page records the computational definitions behind scheduling, episode discretization, optimal matching, and clustering. The concept guides explain when and why to use them; the API pages document signatures and return types.

## Schedule realization

For trip `i`, let `[E_i, L_i]` be its own inclusive departure interval, `m` the minimum activity duration, and `B_i` the latest departure retained by the reverse pass.

The reverse pass visits trips from last to first. When a successor exists, the current trip must arrive by `B_{i+1} - m`. An applicable observation horizon supplies another arrival limit; the scheduler uses the earlier limit as `C_i`. For a known duration `\tau_i`:

$$
B_i = \min\left(L_i, C_i - \tau_i\right).
$$

Without a successor or applicable arrival horizon, `B_i=L_i`. For a deterministic FIFO travel-time function, bisection finds the greatest integer departure in `[E_i,L_i]` whose resulting arrival does not exceed `C_i`.

The forward pass visits trips from first to last. Its propagated lower limit is zero for the first trip and the preceding realized arrival plus `m` thereafter. An uncertain departure is drawn uniformly from the inclusive integers

$$
\left[
\max(E_i,F_i),
\min(L_i,B_i,H_d)
\right],
$$

where `H_d` is included when the policy restricts departures to the observation window. Concrete departures are checked against the same interval and remain fixed.

Each draw is uniform only over the interval available at that step. The procedure does not sample uniformly from the joint set of complete feasible schedules. If callable refinement is disabled, one failed realization does not establish that every departure in the original window would fail.

See [Scheduling departure windows](../concepts/scheduling.md) for the two-pass explanation and figure, and {py:func}`athenspop.scheduling.engine.schedule_once` for the public operation.

## Episode discretization

{py:func}`athenspop.sequence.episodes.episodes_from_diary` produces half-open activity and travel episodes over the requested observation window.

For each fixed-width bin, {py:func}`athenspop.sequence.episodes.discretize_episodes` totals the overlap contributed by every episode of each state. The state with the greatest total overlap wins. A tie goes to the state whose first contributing episode begins earliest. The final bin may be shorter than the requested width.

## Optimal matching

For sequences `x=(x_1,\ldots,x_n)` and `y=(y_1,\ldots,y_m)`, let `D_{i,j}` be the minimum cost of transforming the first `i` and `j` states. Let `g` be the positive insertion and deletion cost, and `c(x_i,y_j)` the nonnegative substitution cost.

The boundary values are `D_{i,0}=ig` and `D_{0,j}=jg`. The recurrence is

$$
D_{i,j}=\min\begin{cases}
D_{i-1,j}+g,\\
D_{i,j-1}+g,\\
D_{i-1,j-1}+c(x_i,y_j).
\end{cases}
$$

{py:func}`athenspop.sequence.distance.optimal_matching_dissimilarity` returns `D_{n,m}`. One comparison may use directed substitution costs. {py:func}`athenspop.sequence.distance.dissimilarity_matrix` requires symmetric forward and reverse costs because it constructs a symmetric matrix. Results are not divided by sequence length.

The implementation stores two dynamic-programming rows for a scalar comparison and batches equal-length targets during matrix construction.

## Average-linkage hierarchy

{py:func}`athenspop.clustering.hierarchical.average_linkage` validates a finite, symmetric, nonnegative dissimilarity matrix with a zero diagonal, converts it to SciPy's condensed form, and calls [`scipy.cluster.hierarchy.linkage`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html) with average linkage.

The distance between two clusters is the arithmetic mean of all pairwise dissimilarities with one observation in each cluster. SciPy records both merged child identifiers, the merge height, and the resulting observation count in each linkage row.

{py:func}`athenspop.clustering.hierarchical.flat_cluster_labels` constructs a top-down cut by repeatedly splitting the displayed node with the greatest merge height. Labels follow displayed leaf order and begin at one.

{py:func}`athenspop.clustering.hierarchical.cophenetic_correlation` computes the Pearson correlation between source dissimilarities and the cophenetic distances implied by the hierarchy. It returns an undefined result when either vector is constant or fewer than two values are available.

## Scaling boundaries

| Operation | Time | Additional working memory |
| --- | --- | --- |
| One optimal-matching comparison of lengths `n` and `m` | `O(nm)` | `O(m)` |
| Pairwise matrix for `N` sequences | `N(N-1)/2` comparisons | `O(N^2)` output plus batch workspace |
| SciPy average linkage for `N` observations | `O(N^2)` | `O(N^2)` |

The pairwise matrix and linkage hierarchy are therefore the main scaling limits for large collections.

## Sources

- R. A. Wagner and M. J. Fischer, [The string-to-string correction problem](https://doi.org/10.1145/321796.321811), `Journal of the ACM` 21(1), 168–173 (1974).
- A. Abbott and A. Tsay, [Sequence Analysis and Optimal Matching Methods in Sociology](https://doi.org/10.1177/0049124100029001001), `Sociological Methods & Research` 29(1), 3–33 (2000).
- Y. Song and colleagues, [Visualizing, clustering, and characterizing activity-trip sequences via weighted sequence alignment and functional data analysis](https://doi.org/10.1016/j.trc.2021.103007), `Transportation Research Part C` 126, 103007 (2021).
- B. C. Dean, [Shortest Paths in FIFO Time-Dependent Networks: Theory and Algorithms](https://people.csail.mit.edu/bdean/tdsp.pdf), technical report.
- SciPy, [Hierarchical clustering linkage reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html).
