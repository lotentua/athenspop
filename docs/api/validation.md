# Validation API

Validation collects schema, key, join, timing, and diary-chain diagnostics before model construction. Errors prevent normalized tables. Warnings preserve a usable result while identifying a material data-quality condition.

```{eval-rst}
.. automodule:: athenspop.validation.schema
   :members: NormalizedTables, ValidationResult, validate_dataframes

.. automodule:: athenspop.validation.report
   :members: ValidationError, ValidationIssue, ValidationReport
```
