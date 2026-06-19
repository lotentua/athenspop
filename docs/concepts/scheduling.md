# Scheduling

Scheduling fills in concrete departure and arrival seconds for trips whose input timing is incomplete but feasible.

The scheduler supports concrete trips, fixed travel times, travel-time callables, and departure windows. When a trip has a departure window, the scheduler first narrows the feasible interval against later trips and the configured minimum activity duration, then samples a concrete departure uniformly from the feasible integer seconds.

`schedule_once(...)` is for one realization. `generate_schedules(...)` repeats the same scheduler with controlled seeds so users can generate multiple feasible diaries from uncertain input.

Travel-time functions receive origin, destination, mode, and departure second, then return a strictly positive integer number of seconds. If a travel-time function depends on random state or mutable external data, reproducibility belongs to that callable.

Probability-table and logit scheduling are future generic extensions. They should reuse the same feasible-interval machinery and diagnostics rather than adding a second scheduling model.
