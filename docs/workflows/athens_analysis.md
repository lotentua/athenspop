# Explore the released Athens diaries

This workflow describes exact purpose-chain frequencies in the released processed Athens tables. It then shows how an analyst can compose optimal matching and average linkage as an explicitly exploratory extension. The executable source is [`examples/analyze_athens.py`](https://github.com/lotentua/athenspop/blob/v2/examples/analyze_athens.py).

The release contains 1,347 reported trips from 513 respondents. It contains no routes, distances, or travel durations. The analysis therefore uses reported purpose order and does not require a routing product.

## 1. Load validated purpose chains

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: load_purpose_chains
```

The three CSV files pass through the same dataframe validation boundary as user data. The returned sequence for each respondent contains destination-purpose labels in reported trip order.

## 2. Count exact chains

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: chain_frequency_table
```

The 513 respondents produce 144 distinct ordered purpose chains. The twelve most frequent chains are:

| Purpose chain | Respondents |
| --- | ---: |
| `work -> home` | 100 |
| `work -> work` | 42 |
| `recreation -> home` | 24 |
| `recreation -> recreation` | 17 |
| `other -> home` | 15 |
| `education -> home` | 14 |
| `work -> home -> recreation` | 14 |
| `work -> recreation` | 13 |
| `work -> home -> recreation -> home` | 10 |
| `work -> work -> home` | 10 |
| `work -> work -> recreation` | 10 |
| `work -> market` | 9 |

```{figure} ../_static/athens-chain-frequencies.svg
:alt: Horizontal bars show the twelve most frequent reported purpose chains. Work followed by home has 100 respondents, and work followed by work has 42. Every other displayed count is 24 or fewer.

The figure shows the exact frequencies of the twelve most common reported purpose chains among 513 released respondent records. No weighting or trip completion is applied.
```

These are record-level descriptions, not estimates for the Athens population. Recruitment used broadcasting channels rather than probability sampling, demographic fields were optional, and younger respondents are overrepresented. The source study describes the 2022 survey and its limitations [1].

## 3. Add an exploratory hierarchy

The example builds a complete symmetric unit substitution matrix for the observed states. Insertions and deletions also retain their default unit cost.

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: unit_substitution_cost
```

It then computes unnormalized optimal-matching dissimilarities and cuts an average-linkage hierarchy at a caller-supplied cluster count.

```{literalinclude} ../../examples/analyze_athens.py
:language: python
:pyobject: illustrative_cluster_labels
```

The function name and argument make the inferential boundary explicit. `n_clusters` is a display choice, not an estimated optimum or evidence of latent traveler types. Unit costs also encode a strong assumption: every unequal purpose substitution has the same consequence. A substantive analysis should justify both the cost structure and its cluster-selection procedure before interpreting groups.

## Data limitations

The released chains include only reported trips. They are not completed daily schedules: 203 of 513 chains do not end at their first origin. Synthetic zone labels have no public geographic crosswalk, 373 movements retain the same origin and destination label, and clock-hour responses are represented as one-hour departure windows. These properties support order-based exploratory analysis but do not identify distance, route, precise departure, or travel duration.

## Reference

1. E. Andrinopoulou and P. G. Tzouras report the study in [Applying spectral clustering to decode mobility patterns in Athens, Greece](https://doi.org/10.3390/app15073419), published in *Applied Sciences*, 15(7), 3419 (2025).
