"""Generic episode construction and fixed-interval state sequencing."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from athenspop.model import Diary

SECONDS_PER_HOUR: Final[int] = 3600
DEFAULT_WINDOW_SECONDS: Final[int] = 24 * SECONDS_PER_HOUR
DEFAULT_INTERVAL_SECONDS: Final[int] = 900


@dataclass(frozen=True, slots=True)
class Episode:
    """Continuous activity or travel interval in integer seconds from the diary origin.

    Attributes:
        state: Activity label or travel state label for the interval.
        start_second: Inclusive interval start in seconds from the diary time origin.
        end_second: Exclusive interval end in seconds from the diary time origin.
    """

    state: str
    start_second: int
    end_second: int


def overlap_duration(episode: Episode, interval_start_second: int, interval_end_second: int) -> int:
    """Return the integer-second overlap between one episode and one interval.

    Args:
        episode: Continuous activity or travel episode.
        interval_start_second: Inclusive interval start in seconds.
        interval_end_second: Exclusive interval end in seconds.

    Returns:
        Non-negative overlap duration in integer seconds.
    """
    return max(
        0,
        min(episode.end_second, interval_end_second) - max(episode.start_second, interval_start_second),
    )


def discretize_episodes(
    episodes: Sequence[Episode],
    *,
    window_start_second: int = 0,
    window_end_second: int = DEFAULT_WINDOW_SECONDS,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> tuple[str, ...]:
    """Assign each fixed-width interval to the state with maximum overlap duration.

    Args:
        episodes: Continuous episodes that partition the requested observation window.
        window_start_second: Inclusive observation-window start in seconds.
        window_end_second: Exclusive observation-window end in seconds.
        interval_seconds: Width of each sequence bin in integer seconds.

    Returns:
        Tuple of state labels, one label per fixed-width interval.

    Raises:
        ValueError: If `interval_seconds` is not positive or an interval has no overlapping episode.
    """
    if interval_seconds <= 0:
        raise ValueError(f"`interval_seconds` must be positive, got {interval_seconds}.")
    labels: list[str] = []
    interval_start = window_start_second
    while interval_start < window_end_second:
        interval_end = min(interval_start + interval_seconds, window_end_second)
        labels.append(_state_for_interval(episodes, interval_start, interval_end))
        interval_start = interval_end
    return tuple(labels)


def episodes_from_diary(
    diary: Diary,
    *,
    initial_activity_state: str = "home",
    window_start_second: int = 0,
    window_end_second: int = DEFAULT_WINDOW_SECONDS,
) -> tuple[Episode, ...]:
    """Build continuous activity and travel episodes from one scheduled diary.

    Args:
        diary: Scheduled diary whose trips all have concrete departure and arrival seconds.
        initial_activity_state: State assigned before the first observed trip departure.
        window_start_second: Inclusive observation-window start in seconds.
        window_end_second: Exclusive observation-window end in seconds.

    Returns:
        Continuous episodes cropped to the observation window and covering it exactly.

    Raises:
        ValueError: If the observation window is invalid, a trip is unscheduled, trips overlap, or the produced episodes do not partition the window.
    """
    if window_start_second < 0 or window_end_second <= window_start_second:
        raise ValueError("The observation window must have non-negative start and positive duration.")
    episodes: list[Episode] = []
    current_second = window_start_second
    current_activity_state = initial_activity_state
    for trip in diary.trips:
        departure_second = trip.departure_second
        arrival_second = trip.arrival_second
        if departure_second is None or arrival_second is None:
            raise ValueError(f"Trip {trip.trip_id!r} is not scheduled; both departure and arrival seconds are required.")
        if arrival_second <= departure_second:
            raise ValueError(f"Trip {trip.trip_id!r} arrives at {arrival_second}, which must be after departure {departure_second}.")
        if arrival_second <= window_start_second:
            current_activity_state = trip.purpose
            continue
        overlaps_window_start = current_second == window_start_second and departure_second < window_start_second < arrival_second
        if departure_second < current_second and not overlaps_window_start:
            raise ValueError(f"Trip {trip.trip_id!r} departs at {departure_second}, before the previous episode ends at {current_second}.")
        if current_second >= window_end_second:
            break
        if departure_second >= window_end_second:
            break
        if departure_second > current_second:
            episodes.append(
                Episode(
                    state=current_activity_state,
                    start_second=current_second,
                    end_second=departure_second,
                )
            )
        travel_start_second = max(departure_second, window_start_second)
        travel_end_second = min(arrival_second, window_end_second)
        episodes.append(
            Episode(
                state=f"trip_{trip.mode}",
                start_second=travel_start_second,
                end_second=travel_end_second,
            )
        )
        current_second = travel_end_second
        if arrival_second > window_end_second:
            break
        current_activity_state = trip.purpose
    if current_second < window_end_second:
        episodes.append(
            Episode(
                state=current_activity_state,
                start_second=current_second,
                end_second=window_end_second,
            )
        )
    _verify_episode_partition(
        episodes,
        window_start_second=window_start_second,
        window_end_second=window_end_second,
    )
    return tuple(episodes)


def state_sequence_from_diary(
    diary: Diary,
    *,
    initial_activity_state: str = "home",
    window_end_second: int = DEFAULT_WINDOW_SECONDS,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> tuple[str, ...]:
    """Convert one scheduled diary into fixed-interval activity and trip states.

    Args:
        diary: Scheduled diary whose trips all have concrete departure and arrival seconds.
        initial_activity_state: State assigned before the first observed trip departure.
        window_end_second: Exclusive observation-window end in seconds.
        interval_seconds: Width of each sequence bin in integer seconds.

    Returns:
        Tuple of fixed-interval state labels suitable for sequence dissimilarity calculations.
    """
    episodes = episodes_from_diary(
        diary,
        initial_activity_state=initial_activity_state,
        window_end_second=window_end_second,
    )
    return discretize_episodes(episodes, window_end_second=window_end_second, interval_seconds=interval_seconds)


def _state_for_interval(episodes: Sequence[Episode], interval_start_second: int, interval_end_second: int) -> str:
    """Choose the state with greatest overlap in one interval, breaking ties by earliest episode start."""
    overlap_by_state: dict[str, int] = {}
    earliest_start_by_state: dict[str, int] = {}
    for episode in episodes:
        overlap = overlap_duration(episode, interval_start_second, interval_end_second)
        if overlap == 0:
            continue
        overlap_by_state[episode.state] = overlap_by_state.get(episode.state, 0) + overlap
        earliest_start_by_state[episode.state] = min(
            earliest_start_by_state.get(episode.state, episode.start_second),
            episode.start_second,
        )
    if not overlap_by_state:
        raise ValueError(f"No episode overlaps interval [{interval_start_second}, {interval_end_second}).")
    max_overlap = max(overlap_by_state.values())
    candidate_states = [state for state, overlap in overlap_by_state.items() if overlap == max_overlap]
    return min(candidate_states, key=lambda state: earliest_start_by_state[state])


def _verify_episode_partition(
    episodes: Sequence[Episode],
    *,
    window_start_second: int,
    window_end_second: int,
) -> None:
    """Verify that episodes exactly partition the requested observation window without gaps or overlaps."""
    expected_start = window_start_second
    for episode in episodes:
        if episode.start_second != expected_start:
            raise ValueError(f"Episodes do not partition the observation window; expected start {expected_start}, got {episode.start_second}.")
        if episode.end_second <= episode.start_second:
            raise ValueError(f"Episode {episode.state!r} has non-positive duration.")
        expected_start = episode.end_second
    if expected_start != window_end_second:
        raise ValueError(f"Episodes do not end at the observation window boundary; expected {window_end_second}, got {expected_start}.")
