# Scheduling And Generation

Scheduling turns validated trips into concrete departure and arrival seconds.

Use `schedule_once(...)` when the task is one feasible realization, such as converting departure windows to actual times.

```python
from athenspop import SchedulingConfig, schedule_once

scheduled = schedule_once(dataset, seed=42, config=SchedulingConfig(min_activity_duration_seconds=1800))
```

Use `generate_schedules(...)` when the task is repeated stochastic realization from the same validated input.

```python
from athenspop import generate_schedules

runs = generate_schedules(dataset, 5, seed=42)
```

The scheduler samples uniformly over explicit feasible departure intervals.
It keeps probability-table and logit scheduling out of the public API until those methods are implemented as generic behavior.

Travel-time callables must return strictly positive integer seconds.
Seeded reproducibility is guaranteed only when user travel-time callables are deterministic with respect to their inputs and stable external data.
