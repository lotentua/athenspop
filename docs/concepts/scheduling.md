# Scheduling

Scheduling realizes concrete departure and arrival seconds while preserving each validated diary's order and timing constraints. The operation is conditional on the supplied diary, policy, travel-time information, and random seed.

## Constraint system

For trip $i$, let $d_i$ be its departure second, $a_i$ its arrival second, $[e_i,l_i]$ an applicable inclusive departure window, $t_i(d_i)$ its positive travel time, $m$ the minimum activity duration, and $H$ the observation-window end. A feasible realization satisfies the applicable constraints

$$
e_i \le d_i \le l_i,
$$

$$
a_i = d_i + t_i(d_i),
$$

$$
d_i \ge a_{i-1} + m \quad \text{for } i > 1.
$$

By default, each departure and arrival must also satisfy $d_i \le H$ and $a_i \le H$. `allow_trips_after_observation_window` removes both horizon restrictions. `allow_final_trip_after_observation_window` permits only the final arrival to exceed $H$; the final departure must still occur by $H$.

Concrete departures remain fixed. Window departures are drawn uniformly from the integer seconds that remain after the previous-arrival, future-trip, and horizon bounds are applied.

```{figure} ../_static/scheduling-flow.svg
:alt: The flow diagram traces validated diaries through reverse feasibility bounds and forward departure realization to a scheduled dataset and diagnostics.

The scheduler derives future bounds before drawing departures, then returns successful diaries and diagnostics as separate parts of one result.
```

## Reverse bounds and forward realization

The scheduler first traverses a diary in reverse. It tightens each latest departure so that later fixed or bounded trips can still occur after the required activity duration. It then traverses forward. At each departure window, it intersects the reported window with the previous arrival, the reverse bound, and the horizon policy before drawing an integer second.

This procedure prevents an early unconstrained draw from making a later trip infeasible when a tighter bound can be derived. It does not sample uniformly from the joint set of all feasible diary schedules. Repeated results from `athenspop.generation.schedules.generate_schedules` are conditional realizations of the same records, not new respondents or population replicates.

## Travel-time functions

A travel-time function has the contract

```python
def travel_time(
    origin: str,
    destination: str,
    mode: str,
    departure_second: int,
) -> int:
    """Return a positive integer travel duration in seconds."""
```

The scheduler validates each returned value. The callable can be stored on `SurveyDataset` or passed to `athenspop.scheduling.engine.schedule_once`, where the explicit argument takes precedence.

The default `refine_callable_departure_windows=True` setting uses bisection to tighten a callable trip against a later arrival bound. This refinement requires a deterministic first-in, first-out callable over the searched window:

$$
d_1 \le d_2 \implies d_1 + t(d_1) \le d_2 + t(d_2).
$$

Disable refinement when that condition is not defensible. The scheduler will still evaluate the callable at the selected departure, but it cannot preclude every later-trip conflict before the draw.

## Results and failures

`athenspop.scheduling.engine.schedule_once` does not mutate the input. It returns `ScheduledSurveyDataset`, which contains:

- `dataset` contains only diaries scheduled successfully, with matching person and household metadata.
- `diagnostics` reports attempted and successful counts, infeasible diary identifiers, and structured issues.

The scheduler stops a diary at its first infeasibility. Inspect `diagnostics.has_errors` before treating the returned dataset as a complete realization of the input sample.
