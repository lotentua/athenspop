# athenspop

`athenspop` is a small Python library for validating long-form household travel survey tables and working with complete daily mobility diaries.

The library has one plain path: read or build dataframes, validate the dataframe boundary, construct trusted diary objects, schedule feasible trip times when needed, build activity and travel sequences, compute sequence dissimilarities, and cluster diaries.
Public code and documentation describe those generic steps; dataset-specific workflows belong in examples.

```{toctree}
:maxdepth: 2
:caption: Examples

examples/index
```

```{toctree}
:maxdepth: 2
:caption: Concepts

concepts/data_model
concepts/validation
concepts/scheduling
concepts/sequences
concepts/clustering
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user_guide/quickstart
user_guide/input_tables
user_guide/validation_report
user_guide/scheduling_and_generation
user_guide/sequence_clustering
user_guide/glossary
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/index
```

```{toctree}
:maxdepth: 2
:caption: Development

development/code_style
development/testing
development/contributing
```
