# Scheduling Method Note

This note compares the CSuM2026 example scheduler policy against ActivitySim-style probabilistic scheduling and records the generic scheduling boundary for `athenspop`.

## Athens Method

The paper starts from reported departure-time intervals, not exact observed departure timestamps. It samples one concrete departure time uniformly within each reported interval, subject to trip-chain feasibility and a 30-minute minimum activity duration. It uses travel-time lookup data to infer arrivals and activity durations, discards one fully infeasible diary, imputes return-home trips when the final purpose is neither `home` nor `recreation`, permits recreation to extend beyond the monitoring period, and crops diaries to the 24-hour observation window.

For the Athens example, this is the required method because the example target is reproduction of `CSuM2026.pdf`.

## ActivitySim Reference Pattern

ActivitySim's probabilistic trip scheduling assigns departure periods from lookup tables conditioned by behavioral context and trip order. It enforces feasibility by processing trips in constrained order, rerunning sampling up to a configured maximum number of iterations, and applying a configured fallback such as assigning the previous trip's choice or dropping a trip when no feasible schedule is found. ActivitySim also uses person time windows to track occupied and available periods.

The important idea for `athenspop` is not ActivitySim's API. The important ideas are explicit feasible alternatives, reproducible randomness, bounded retry behavior, diagnostics for infeasible schedules, and a sampler boundary that can later switch from uniform sampling to probability tables or logit choice.

## V1 Implementation Choice

- Implement a shared realization engine that accepts validated diary chains, a travel-time resolver, a random generator, and a sampler strategy.
- Implement uniform departure sampling first.
- Before sampling, refine each trip's latest feasible departure by walking the diary backward from later trips; fixed durations use direct subtraction, and deterministic callable travel times use a binary search for the latest departure whose computed arrival still leaves the configured minimum activity duration before the next trip.
- Use integer seconds throughout scheduling.
- Expose `schedule_once(dataset, *, seed=None, config=None)` for one concrete realization.
- Expose `generate_schedules(dataset, n, *, seed=None, config=None)` for repeated realizations through the same engine.
- Return diagnostics for infeasible diaries rather than silently dropping rows.
- Keep probability-table or logit scheduling deferred until after the generic uniform path and Athens example are correct and tested.

## Future-Compatible Seams

- A `DepartureSampler` strategy can later support uniform, probability-table, or logit samplers.
- A `FeasibilityPolicy` can later support richer time-window constraints without changing validated input objects.
- A `TravelTimeResolver` boundary can check stochastic and time-dependent travel-time callables at each scheduler call.
- Per-diary seed derivation can later mirror ActivitySim's reproducible random-stream idea while keeping the public API simple.

## V1 Acceptance Tests

- Concrete trips remain unchanged except for derived arrival when `travel_time_seconds` or `travel_time_function` supplies duration.
- Departure-window trips are realized to concrete integer seconds inside `[earliest_departure_second, latest_departure_second]`.
- Movement travel times are strictly positive integer seconds.
- The same seed produces the same schedule.
- Different generation draws may produce different schedules while preserving feasibility.
- Infeasible diaries are reported with reasons.
- Tests cover the 30-minute minimum activity duration, return-home imputation, the generic opt-in final-trip-after-window policy, and observation-window cropping.
