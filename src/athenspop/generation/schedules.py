"""Generate repeated stochastic realizations from one validated survey dataset."""

from random import Random

from athenspop.model import SurveyDataset
from athenspop.scheduling import (
    ScheduledSurveyDataset,
    SchedulingConfig,
    TravelTimeFn,
    schedule_once,
)


def generate_schedules(
    dataset: SurveyDataset,
    n: int,
    *,
    seed: int | None = None,
    config: SchedulingConfig | None = None,
    travel_time_fn: TravelTimeFn | None = None,
) -> tuple[ScheduledSurveyDataset, ...]:
    """Generate repeated stochastic schedules from one trusted dataset.

    Args:
        dataset: Trusted survey dataset produced by validation/model loading.
        n: Number of independent scheduling realizations to produce.
        seed: Optional seed used to derive one repeatable child seed per realization.
        config: Optional scheduling policy shared by all realizations.
        travel_time_fn: Optional callable returning positive integer travel seconds for trips whose duration is not already concrete.

    Returns:
        Tuple of scheduled survey datasets, one per requested realization.

    Raises:
        ValueError: If `n` is negative.

    Notes:
        This helper is deliberately thin; it uses the same scheduler internals as `schedule_once` so repeated generation and one-off range realization share behavior.
    """
    if n < 0:
        raise ValueError(f"`n` must be non-negative, got {n}.")
    rng = Random(seed)
    return tuple(
        schedule_once(
            dataset,
            seed=rng.randrange(0, 2**63),
            config=config,
            travel_time_fn=travel_time_fn,
        )
        for _ in range(n)
    )
