# Explore the released Athens diaries

What journeys did respondents report, and which purpose chains occurred most often? This workflow answers those questions directly from the processed Athens tables before showing how the same chains can feed an exploratory sequence hierarchy.

The release contains 1,347 reported trips from 513 respondents. It contains purpose, mode, broad departure windows, and standardized demographic fields, but no routes, distances, travel durations, or geographic crosswalk. Purpose order is therefore the strongest self-contained signal for this example.

The executable analysis is [`examples/analyze_athens.py`](https://github.com/lotentua/athenspop/blob/v2/examples/analyze_athens.py).

## 1. Load purpose chains

The loader reads all three CSV files and passes them through {py:meth}`athenspop.model.survey.SurveyDataset.from_dataframes`. It then extracts destination purposes in validated trip order.

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: load_purpose_chains
```

The result contains one tuple per respondent. A two-trip commute, for example, appears as `("work", "home")`.

## 2. Count exact patterns

Before introducing a distance metric or cluster model, count the chains exactly:

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: chain_frequency_table
```

The 513 respondents reported 144 distinct chains. The most frequent was work followed by home, reported by 100 respondents. Work followed by work was second with 42.

| Purpose chain | Respondents |
| --- | ---: |
| `work → home` | 100 |
| `work → work` | 42 |
| `recreation → home` | 24 |
| `recreation → recreation` | 17 |
| `other → home` | 15 |
| `education → home` | 14 |
| `work → home → recreation` | 14 |
| `work → recreation` | 13 |
| `work → home → recreation → home` | 10 |
| `work → work → home` | 10 |
| `work → work → recreation` | 10 |
| `work → market` | 9 |

```{figure} ../_static/athens-chain-frequencies.svg
:alt: Horizontal bars rank the twelve most frequent reported purpose chains. Work then home has 100 respondents, work then work has 42, and all remaining displayed chains have 24 or fewer.

The twelve most common reported purpose chains. Counts describe released records only; no weighting or trip completion is applied.
```

The sharp drop after the first two chains is visible without clustering. This is why the workflow begins with exact counts: a simple summary should answer the simple question before a more flexible method is introduced.

## 3. Compare chains approximately

Exact counts treat `("work", "home")` and `("work", "recreation", "home")` as unrelated labels. Optimal matching can instead compare their ordered states.

The example assigns zero cost to equal purposes and unit cost to every unequal pair:

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: unit_substitution_cost
```

It then calls {py:func}`athenspop.sequence.distance.dissimilarity_matrix`, builds an {py:func}`athenspop.clustering.hierarchical.average_linkage` hierarchy, and requests a caller-selected cut:

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: illustrative_cluster_labels
```

Unit costs are useful for demonstrating the mechanics, but they say that every purpose substitution matters equally. A substantive study may need costs informed by activity type, transition frequency, duration, or another explicit theory. Likewise, `n_clusters` is a value to investigate, not an estimate supplied by this workflow. [Sequences and clustering](../concepts/sequences.md) explains both choices and links to activity-travel sequence research.

## What the released data can support

The tables support record-level descriptions of reported trip order, modes, broad departure periods, and available demographics. They do not support route, distance, precise travel-time, or population-level claims.

Several details matter when interpreting the chains:

- 203 of 513 chains do not return to their first origin;
- 373 movements have the same synthetic origin and destination label;
- departure times represent one-hour windows rather than exact seconds;
- recruitment used broadcasting channels rather than probability sampling; and
- optional demographics are missing for some respondents.

These are characteristics of the released records, not defects that the package should silently repair.

## Sources and next steps

Andrinopoulou and Tzouras describe the 2022 survey, recruitment, and source analysis in [Applying spectral clustering to decode mobility patterns in Athens, Greece](https://doi.org/10.3390/app15073419). The [dataset README](https://github.com/lotentua/athenspop/blob/v2/data/athens/README.md) documents the released columns, privacy transformation, missing values, and integrity hashes.

For methodological context, Song and colleagues apply interval-based state sequences and weighted alignment to activity-travel diaries in [Visualizing, clustering, and characterizing activity-trip sequences](https://doi.org/10.1016/j.trc.2021.103007).

Run the workflow from the repository root:

```console
python examples/analyze_athens.py
```
