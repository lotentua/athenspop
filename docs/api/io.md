# Input conversion API

The input helpers convert civil clock values and dataframe columns into integer seconds from a chosen diary origin. Parsing CSV, database, or other storage formats remains the caller's responsibility.

See [Clock conversion](../reference/data_contract.md#clock-conversion) for the diary-origin and rollover rules.

```{eval-rst}
.. automodule:: athenspop.io.clock
   :members: ClockValue, clock_seconds_from_time_origin, convert_clock_columns
```
