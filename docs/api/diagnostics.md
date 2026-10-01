# Diagnostic vocabulary

Validation and scheduling return structured issues rather than asking callers to parse exception text. Use {py:class}`athenspop.diagnostics.IssueCode` for program logic and tests. The accompanying message explains the particular row, trip, or constraint and may include values from the input.

Validation issues also use {py:class}`athenspop.diagnostics.IssueSeverity` to distinguish conditions that prevent a valid result from warnings that preserve a result but may affect its interpretation. Both enumerations inherit from `str`, so their values remain easy to serialize and display.

```{eval-rst}
.. automodule:: athenspop.diagnostics
   :members: IssueCode, IssueSeverity
```
