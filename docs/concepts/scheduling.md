# Scheduling departure windows

A reported departure window says when a trip may begin, not when it did begin. Choosing a time independently for every trip can produce an impossible day: an early trip may arrive too late for a later fixed departure, or a late draw may leave less than the required activity time between trips.

{py:func}`athenspop.scheduling.engine.schedule_once` avoids that problem by looking ahead before it draws any uncertain departure. It first works backward to discover how late each trip may leave, then works forward to choose departures and calculate arrivals.

## The constraints in everyday terms

Scheduling respects four constraints:

- a concrete departure stays fixed, while a departure window remains inclusive at both ends;
- arrival equals departure plus a positive travel duration;
- each trip starts after the preceding trip has arrived and the minimum activity duration has elapsed; and
- departures and arrivals stay inside the observation window unless the scheduling policy explicitly permits an exception.

These rules come from the validated diary and {py:class}`athenspop.scheduling.engine.SchedulingConfig`. The scheduler does not add missing trips, change trip order, or infer a travel time when neither a fixed duration nor a travel-time function is available.

## Why scheduling needs a backward pass

Consider two 20-second trips. The first may depart between second 0 and second 100. The second may depart between second 90 and second 120. At least 10 seconds of activity must separate the first arrival from the second departure.

The second trip can leave as late as second 120. Working backward, the first trip must therefore arrive by second 110, which means it must depart by second 90. Its reported window ended at second 100, but only the range from 0 through 90 can lead to a feasible continuation.

```{figure} ../_static/scheduling-flow.svg
:alt: The backward panel removes departures after second 90 from the first trip's reported window. The forward panel removes departures before second 110 from the second trip's reported window after the first arrival is known.

Hatched intervals cannot lead to a feasible continuation. The backward pass removes the late end of the first window; the forward pass removes the early end of the second window before choosing departures.
```

This look-ahead is the main reason for the two-pass design. Without it, a valid but late first draw could make the second trip fail even though an earlier first departure would have produced a feasible diary.

## What happens in each pass

The reverse pass starts at the last trip. For each trip, it combines the trip's own latest departure with any limit imposed by the observation window and the next trip. When duration is fixed, the calculation subtracts the travel duration and minimum activity duration from the next latest departure. When duration depends on departure time, the scheduler can search the window for the latest departure that still arrives in time.

The forward pass starts at the first trip. It raises the current earliest departure when the preceding realized arrival and minimum activity duration require a later start. It then draws an integer second from the remaining interval, calculates arrival, and carries that arrival into the next trip.

A fixed departure is checked against the same forward and reverse limits but is never redrawn. If an interval becomes empty, the diary is infeasible under the supplied inputs and policy.

The [method reference](../reference/methods.md#schedule-realization) gives the exact recurrence for readers implementing or auditing the algorithm.

## Time-dependent travel times

A travel-time function receives the origin, destination, mode, and candidate departure second, then returns a positive integer duration:

```python
def travel_time(
    origin: str,
    destination: str,
    mode: str,
    departure_second: int,
) -> int:
    """Return a positive travel duration in seconds."""
```

Store the function on {py:class}`athenspop.model.survey.SurveyDataset` when it belongs to the dataset, or pass it directly to {py:func}`athenspop.scheduling.engine.schedule_once` for one call. The explicit argument takes precedence.

By default, the reverse pass uses bisection to tighten windows with time-dependent durations. This search assumes deterministic first-in, first-out behavior: leaving later may produce the same arrival time or a later one, but never an earlier arrival. This is the standard FIFO property for time-dependent transportation networks; Brian Dean's report [Shortest Paths in FIFO Time-Dependent Networks](https://people.csail.mit.edu/bdean/tdsp.pdf) gives a broader treatment.

Disable callable refinement with `refine_callable_departure_windows=False` when the function does not satisfy that property. The scheduler will still evaluate the function at each selected departure. It simply cannot rule out every future conflict in advance, so one failed draw does not prove that all departures in the original window would fail.

## Reproducibility and repeated schedules

Window departures are uniform over the integer interval that remains when their turn is reached. They are not sampled uniformly from the set of complete feasible diaries. Earlier draws change the intervals available to later trips.

Pass a seed to {py:func}`athenspop.scheduling.engine.schedule_once` for a reproducible realization. Use {py:func}`athenspop.generation.schedules.generate_schedules` to create several seeded realizations of the same validated records. Those outputs explore timing uncertainty in the supplied diaries; they are not additional respondents or population replicates.

## Read the result before continuing

Scheduling never mutates its input. The returned {py:class}`athenspop.scheduling.engine.ScheduledSurveyDataset` separates successful diaries from {py:class}`athenspop.scheduling.engine.SchedulingDiagnostics`.

```python
result = athenspop.scheduling.engine.schedule_once(dataset, seed=2026)

if result.diagnostics.has_errors:
    for issue in result.diagnostics.issues:
        print(
            issue.household_id,
            issue.person_id,
            issue.trip_id,
            issue.code,
            issue.message,
        )
else:
    continue_analysis(result.dataset)
```

The scheduler stops each diary at its first infeasibility. Check the diagnostics before treating the scheduled dataset as a complete realization of the input sample.
