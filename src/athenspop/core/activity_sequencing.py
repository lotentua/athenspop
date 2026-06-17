#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

import math
from collections.abc import Iterable
from typing import Final

import loguru
import numpy as np

from athenspop.models.activities import Activity
from athenspop.models.diaries import ConcreteTimeDiary, InvalidDiary, SequencedDiary
from athenspop.models.results import ActivitySequencingResult
from athenspop.models.trips import TripPurpose
from athenspop.utils.typing import TravelTimeFunction

_END_OF_TIMELINE: Final[float] = np.finfo(np.float64).max


class ActivitySequencer:
    def __init__(self, travel_time_fn: TravelTimeFunction) -> None:
        self._travel_time_fn = travel_time_fn

    def compile_sequence(
        self,
        diaries: Iterable[ConcreteTimeDiary],
        *,
        start_time: float,
        sampling_rate: float,
        encode_trip_mode: bool = True,
    ) -> ActivitySequencingResult:
        success: list[SequencedDiary] = []
        failures: list[InvalidDiary] = []
        for diary in diaries:
            try:
                timeline = self._compile_timeline(
                    diary, encode_trip_mode=encode_trip_mode
                )
                sequence = self._discretize_timeline(
                    timeline,
                    pid=diary.uuid,
                    start_time=start_time,
                    sampling_rate=sampling_rate,
                )
                success.append(SequencedDiary(**diary.model_dump(), sequence=sequence))
            except RuntimeError as e:
                reason = str(e)
                loguru.logger.warning(reason)

                failures.append(InvalidDiary(**diary.model_dump(), reason=reason))

        return ActivitySequencingResult(
            successes=tuple(success), failures=tuple(failures)
        )

    def _compile_timeline(
        self, diary: ConcreteTimeDiary, *, encode_trip_mode: bool
    ) -> tuple[Activity, ...]:
        timeline: list[Activity] = []

        # The timeline begins at the respondent's home zone.
        activity_start_time = 0
        activity_purpose = TripPurpose.HOME
        for index, trip in enumerate(diary.trips):
            trip_departure_time = trip.time
            if trip_departure_time > activity_start_time:
                timeline.append(
                    Activity(
                        start_time=activity_start_time,
                        end_time=trip_departure_time,
                        purpose=activity_purpose,
                    )
                )
            elif index != 0:
                # TODO: Is this a valid assumption?
                # The first activity may be a trip.
                loguru.logger.warning(
                    f"PID {diary.uuid}: Trip Index {index}: The preceding activity has no duration."
                )

            trip_travel_time = self._travel_time_fn(
                origin=trip.orig,
                destination=trip.dest,
                mode=trip.mode,
                departure=trip_departure_time,
            )

            trip_arrival_time = trip_departure_time + trip_travel_time

            timeline.append(
                Activity(
                    start_time=trip_departure_time,
                    end_time=trip_arrival_time,
                    purpose="trip" if not encode_trip_mode else f"trip_{trip.mode}",
                )
            )

            activity_start_time = trip_arrival_time
            activity_purpose = trip.purp

        timeline.append(
            Activity(
                start_time=activity_start_time,
                end_time=_END_OF_TIMELINE,
                purpose=activity_purpose,
            )
        )

        return tuple(timeline)

    #     return self._merge_consecutive_activities(timeline)
    #
    # @staticmethod
    # def _merge_consecutive_activities(timeline: list[Activity]) -> Timeline:
    #     """Merges consecutive activities with the same purpose."""
    #     if not timeline:
    #         return tuple()
    #
    #     merged: list[Activity] = []
    #     for purpose, group in itertools.groupby(timeline, key=lambda act: act.purpose):
    #         activity_group = list(group)
    #         start_time = activity_group[0].start_time
    #         end_time = activity_group[-1].end_time
    #         merged.append(Activity(start_time, end_time, purpose))
    #     return tuple(merged)

    def _discretize_timeline(
        self,
        timeline: tuple[Activity, ...],
        pid: int,
        start_time: float,
        sampling_rate: float,
    ) -> list[str]:
        sequence: list[str] = []

        # TODO: Check formula; should we floor or round?
        num_slots = math.ceil(24 // sampling_rate)
        for slot in range(num_slots):
            slot_start_time = start_time + sampling_rate * slot
            slot_end_time = slot_start_time + sampling_rate

            overlaps: dict[str, float] = {}
            for activity in timeline:
                overlap_start_time = max(slot_start_time, activity.start_time)
                overlap_end_time = min(slot_end_time, activity.end_time)

                if overlap_end_time > overlap_start_time:
                    overlap_duration = overlap_end_time - overlap_start_time
                    overlaps[activity.purpose] = (
                        overlaps.get(activity.purpose, 0) + overlap_duration
                    )
                else:
                    # FIXME
                    # loguru.logger.warning("???")
                    # TODO: What happens here? Is this bad?
                    pass

            if not overlaps:
                # FIXME
                raise RuntimeError(f"No overlaps found for {pid}.")

            modal_activity = max(overlaps, key=overlaps.get)
            # # Robustly find the modal activity with explicit tie-breaking.
            # # 1. Find the maximum duration.
            # max_duration = max(overlaps.values())
            # # 2. Get all activities with that duration.
            # candidates = [
            #     purpose for purpose, dur in overlaps.items() if dur == max_duration
            # ]
            # # 3. Apply tie-breaking rules:
            # #    - If only one candidate, choose it.
            # #    - If multiple, prioritize non-trip activities.
            # #    - If still tied, sort alphabetically for determinism.
            # if len(candidates) == 1:
            #     modal_activity = candidates[0]
            # else:
            #     non_trip_candidates = [c for c in candidates if not c.startswith("Trip_")]
            #     if len(non_trip_candidates) == 1:
            #         modal_activity = non_trip_candidates[0]
            #     elif len(non_trip_candidates) > 1:
            #         modal_activity = sorted(non_trip_candidates)[0]
            #     else: # All candidates are trips
            #         modal_activity = sorted(candidates)[0]

            sequence.append(modal_activity)

        return sequence
