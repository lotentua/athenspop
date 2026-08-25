# Sequences and clustering

A scheduled diary says exactly when activities and trips occur. Sequence analysis offers a different view: it turns the day into an ordered series of symbolic states so that timing patterns can be compared across diaries.

That conversion is useful, but it is not neutral. The observation window, interval width, state vocabulary, edit costs, and cluster cut all influence the result. `athenspop` keeps those choices as function arguments so an analysis can report and vary them.

## From a schedule to episodes

{py:func}`athenspop.sequence.episodes.episodes_from_diary` divides the observation window into continuous activity and travel episodes. The state before the first trip is supplied by the caller. Every trip contributes a travel episode, and its destination purpose becomes the next activity.

For a home-to-work bus trip, a simple state history might look like:

```text
home | trip_bus | work | trip_bus | home
```

Activity and travel labels remain distinct because the default travel label begins with `trip_`. A caller can provide another labeling function when mode, occupancy, or a coarser movement category better suits the analysis.

Episodes use half-open intervals: a state includes its start time and excludes its end time. Adjacent episodes therefore meet at one boundary without overlapping.

## Choosing a temporal resolution

Most distance and clustering operations work on equal-width sequence bins rather than continuous episodes. {py:func}`athenspop.sequence.episodes.discretize_episodes` assigns each bin to the state that occupies the largest share of that interval. If two states occupy equal time, the state that begins first wins.

A 15-minute interval can preserve a short trip that a one-hour interval may absorb into the surrounding activity. Shorter intervals retain more temporal detail and create longer sequences; longer intervals are cheaper to compare and emphasize broad daily structure.

There is no universally correct interval. Choose it in relation to the precision of the source times and the behavior the analysis needs to distinguish. Song and colleagues demonstrate this representation for activity-travel data and examine sensitivity to sampling intervals and cost schemes in [Visualizing, clustering, and characterizing activity-trip sequences](https://doi.org/10.1016/j.trc.2021.103007).

{py:func}`athenspop.sequence.episodes.state_sequence_from_diary` combines episode construction and discretization for the common case.

## Comparing two sequences

Optimal matching asks for the cheapest way to transform one sequence into another using three operations:

- insert a state;
- delete a state; or
- substitute one state for another.

The insertion and deletion cost controls how readily the comparison shifts events in time. Substitution costs express which state differences matter. Treating `work` and `education` as closer than `work` and `trip_car`, for example, requires a smaller substitution cost for the first pair.

{py:func}`athenspop.sequence.distance.optimal_matching_dissimilarity` returns the minimum total edit cost. {py:func}`athenspop.sequence.distance.dissimilarity_matrix` applies the comparison to every pair and requires symmetric substitution costs because its output is a symmetric matrix.

The package does not estimate the costs or normalize the result by sequence length. Those choices change the meaning of distance and should be justified by the analysis. Abbott and Tsay's review, [Sequence Analysis and Optimal Matching Methods in Sociology](https://doi.org/10.1177/0049124100029001001), discusses coding, cost setting, temporality, and interpretation. The exact dynamic-programming recurrence appears in the [method reference](../reference/methods.md#optimal-matching).

## From distances to a hierarchy

{py:func}`athenspop.clustering.hierarchical.average_linkage` begins with one cluster per diary. At every step, it joins the two clusters with the smallest mean pairwise dissimilarity between their members. The process continues until all observations belong to one hierarchy.

Average linkage creates the hierarchy; it does not decide where to cut it. {py:func}`athenspop.clustering.hierarchical.flat_cluster_labels` and {py:func}`athenspop.clustering.hierarchical.cut_dendrogram_tree` use a cluster count supplied by the analyst. A useful analysis treats that count as a decision to examine, not as a population fact.

{py:func}`athenspop.clustering.hierarchical.cophenetic_correlation` measures how closely the tree's cophenetic distances preserve the input dissimilarities. It can reveal a poorly fitting hierarchy, but it does not select a cluster count or establish that the clusters are meaningful.

SciPy's [linkage documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html) describes the underlying linkage matrix, tie behavior, and computational characteristics.

## Summarizing and visualizing a cut

The clustering module provides three complementary summaries:

- {py:func}`athenspop.clustering.hierarchical.cluster_size_summary` counts observations in each cluster;
- {py:func}`athenspop.clustering.hierarchical.cluster_state_distribution` counts state tokens; and
- {py:func}`athenspop.clustering.hierarchical.cluster_time_distribution` reports state shares at each aligned sequence bin.

{py:func}`athenspop.visualization.dendrogram.plot_cut_dendrogram_state_distribution` combines a normalized-height cut tree with the temporal state shares of its displayed clusters. It fixes the quantitative axes and unit-width bar geometry, while dimensions, typography, default colors, tree-line width, and other presentation choices follow the active Matplotlib configuration.

The [synthetic workflow](../workflows/compose_schedule.md) shows the complete composition. The [Athens workflow](../workflows/athens_analysis.md) demonstrates a deliberately exploratory use of purpose chains and explains why unit costs and a chosen cluster count are only a starting point.

## Further reading

- Wagner and Fischer define the minimum-cost string edit recurrence in [The string-to-string correction problem](https://doi.org/10.1145/321796.321811).
- Abbott and Tsay review optimal matching as a method for social sequence analysis in [Sequence Analysis and Optimal Matching Methods in Sociology](https://doi.org/10.1177/0049124100029001001).
- Song and colleagues apply interval-based state sequences and weighted alignment to activity-travel diaries in [Visualizing, clustering, and characterizing activity-trip sequences](https://doi.org/10.1016/j.trc.2021.103007).
- The SciPy documentation specifies the package behavior used for [hierarchical linkage](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html).
