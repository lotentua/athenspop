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

Concrete departures remain fixed. Window departures are drawn uniformly from the integer seconds that remain after the previous-arrival, successor, and horizon bounds are applied.

```{figure} ../_static/scheduling-flow.svg
:alt: Two interval diagrams show a reverse pass tightening latest departures from right to left and a forward pass raising earliest departures from left to right.

Reverse and forward scheduling passes for a two-trip diary. Shaded interval segments are removed by propagated constraints; points mark one valid realization.
```

## Reverse bounds and forward realization

Let $E_i$ and $L_i$ denote trip $i$'s own inclusive departure bounds. A fixed departure has $E_i=L_i$. A reported window supplies both values, with $L_i$ capped by $H$ unless the policy permits every trip to exceed the observation window.

The reverse pass visits trips from $n$ to $1$ and computes a latest admissible departure $B_i$. It begins with $B_i=L_i$. When a successor exists, the current trip must arrive by

$$
C_i = B_{i+1} - m.
$$

The observation horizon contributes another arrival target when the current uncertain trip must arrive by $H$. When both targets apply, $C_i$ is their minimum. For a known duration $\tau_i$,

$$
B_i = \min\left(L_i, C_i - \tau_i\right).
$$

For a deterministic FIFO travel-time function with arrival function $A_i(d)=d+t_i(d)$, bisection instead finds the greatest integer $d\in[E_i,L_i]$ satisfying

$$
A_i(d) \le C_i.
$$

That value caps $B_i$. A bound below $E_i$ leaves an empty interval, which the forward pass reports as infeasible.

The forward pass visits trips from $1$ to $n$. Its lower bound comes from the preceding realized arrival:

$$
F_1=0,
\qquad
F_i=a_{i-1}+m \quad \text{for } i>1.
$$

For an uncertain departure, the scheduler draws uniformly over the inclusive integers

$$
d_i \sim \operatorname{Uniform}_{\mathbb Z}
\left[
\max(E_i,F_i),
\min(L_i,B_i,H_d)
\right],
$$

where $H_d$ is omitted only when departures after the observation window are allowed. It then evaluates $a_i=d_i+t_i(d_i)$ and uses that realized arrival to raise the next trip's lower bound. A fixed departure is accepted only when it lies between the applicable forward and reverse bounds.

The figure uses $H=140$, $m=10$, and two 20-second trips with windows $[0,100]$ and $[90,120]$. The reverse pass gives $B_2=120$ and tightens $B_1$ to $90$. The illustrated forward draw chooses $d_1=80$, so $a_1=100$ raises the second lower bound from $90$ to $110$.

This procedure prevents an early unconstrained draw from making a later trip infeasible when the scheduler can derive a tighter bound. It does not sample uniformly from the joint set of all feasible diary schedules. Repeated results from `athenspop.generation.schedules.generate_schedules` are conditional realizations of the same records, not new respondents or population replicates.

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

Disable refinement when that condition is not defensible. The scheduler will still evaluate the callable at the selected departure, but its reverse bound may then be only partially tightened. A failed draw in that mode does not prove that no other departure could produce a feasible diary.

## Results and failures

`athenspop.scheduling.engine.schedule_once` does not mutate the input. It returns `ScheduledSurveyDataset`, which contains:

- `dataset` contains only diaries scheduled successfully, with matching person and household metadata.
- `diagnostics` reports attempted and successful counts, infeasible diary identifiers, and structured issues.

The scheduler stops a diary at its first infeasibility. Inspect `diagnostics.has_errors` before treating the returned dataset as a complete realization of the input sample.
