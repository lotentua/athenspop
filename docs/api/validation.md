# Validation API

Validation checks schema, keys, joins, timing combinations, and diary continuity before model construction. It collects independent issues so an interface can present more than the first error.

Errors prevent normalized tables. Warnings preserve a usable result while identifying a condition that may affect analysis. See [Inspect problems before building a model](../concepts/data_model.md#inspect-problems-before-building-a-model) for a complete example.

```{eval-rst}
.. automodule:: athenspop.validation.schema
   :members: IntegerSecondValue, NormalizedTables, ScalarValue,
             ValidationResult, validate_dataframes

.. automodule:: athenspop.validation.report
   :members: Severity, ValidationError, ValidationIssue, ValidationReport
```
