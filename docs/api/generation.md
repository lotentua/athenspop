# Generation API

Generation repeats {py:func}`athenspop.scheduling.engine.schedule_once` with reproducibly derived seeds. Every output is another conditional realization of the same records, travel times, and policy.

These results explore timing uncertainty. They are not independent respondents or population replicates. See [Reproducibility and repeated schedules](../concepts/scheduling.md#reproducibility-and-repeated-schedules).

```{eval-rst}
.. automodule:: athenspop.generation.schedules
   :members: generate_schedules
```
