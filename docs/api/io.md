# Input conversion API

Input helpers convert civil clock values and dataframe columns to integer seconds from a selected diary time origin. File parsing remains with pandas or the caller's storage layer.

```{eval-rst}
.. automodule:: athenspop.io.clock
   :members: ClockValue, clock_seconds_from_time_origin, convert_clock_columns
```
