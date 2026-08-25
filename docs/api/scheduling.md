# Scheduling API

Scheduling turns validated departure information into concrete trips without mutating the input dataset. The result keeps successful diaries and structured infeasibility diagnostics separate.

Read [Scheduling departure windows](../concepts/scheduling.md) for the two-pass algorithm, time-dependent travel-time assumptions, and interpretation of repeated draws.

```{eval-rst}
.. automodule:: athenspop.scheduling.engine
   :members: ScheduledSurveyDataset, SchedulingConfig, SchedulingDiagnostics,
      SchedulingIssue, schedule_once
```
