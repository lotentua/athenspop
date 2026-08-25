# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Generate repeated stochastic realizations from one validated survey dataset."""

import random

import athenspop.model.survey
import athenspop.scheduling.engine
import athenspop.types


def generate_schedules(
    dataset: athenspop.model.survey.SurveyDataset,
    n: int,
    *,
    seed: int | None = None,
    config: athenspop.scheduling.engine.SchedulingConfig | None = None,
    travel_time_function: athenspop.types.TravelTimeFunction | None = None,
) -> tuple[athenspop.scheduling.engine.ScheduledSurveyDataset, ...]:
    """Generate repeated stochastic schedules from one trusted dataset.

    Args:
        dataset: This trusted survey dataset was produced by validation or model
            loading.
        n: This value specifies the number of conditional scheduling realizations to
            produce.
        seed: This optional seed derives one repeatable child seed per realization.
        config: This optional scheduling policy applies to all realizations.
        travel_time_function: This optional callable returns positive integer travel
            seconds for trips whose duration is not already concrete.

    Returns:
        The function returns one scheduled survey dataset per requested realization.

    Raises:
        TypeError: The function raises this error if `n` is not an integer.
        ValueError: The function raises this error if `n` is negative.

    Notes:
        Each result uses a child seed derived from the configured pseudorandom
        generator and remains conditional on the same input diaries and policies.
        Results are not independent respondents, population replicates, posterior
        samples, or uniform draws from the joint set of feasible schedules.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("`n` must be an integer.")
    if n < 0:
        raise ValueError(f"`n` must be non-negative, got {n}.")
    rng = random.Random(seed)
    return tuple(
        athenspop.scheduling.engine.schedule_once(
            dataset,
            seed=rng.randrange(0, 2**63),
            config=config,
            travel_time_function=travel_time_function,
        )
        for _ in range(n)
    )
