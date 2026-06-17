#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from collections.abc import Iterable

from athenspop.core.imputation.samplers.empirical import EmpiricalDepartureTimeSampler
from athenspop.models.diaries import ConcreteTimeDiary
from athenspop.models.trips import ConcreteTrip, TripPurpose
from athenspop.utils.typing import TravelTimeFunction


def impute_return_trips(
    diaries: Iterable[ConcreteTimeDiary],
    allowed_end_states: Iterable[TripPurpose],
    travel_time: TravelTimeFunction,
    sampler: EmpiricalDepartureTimeSampler,
) -> tuple[ConcreteTimeDiary, ...]:
    result = []
    for diary in diaries:
        if _has_return_trip(diary, set(allowed_end_states)):
            result.append(diary)
            continue

        last_trip = diary.trips[-1]

        arrival_time = last_trip.time + travel_time(
            origin=last_trip.orig,
            destination=last_trip.dest,
            mode=last_trip.mode,
            departure=last_trip.time,
        )

        departure_time = sampler.sample(
            purpose=last_trip.purp, arrival_time=arrival_time
        )

        return_trip = ConcreteTrip(
            **last_trip.model_dump(exclude={"purp", "time"}),
            purp=TripPurpose.HOME,
            time=departure_time,
        )

        result.append(
            ConcreteTimeDiary(
                **diary.model_dump(exclude={"trips"}),
                trips=diary.trips + (return_trip,),
            )
        )

    return tuple(result)


def _has_return_trip(
    diary: ConcreteTimeDiary, allowed_purposes: set[TripPurpose]
) -> bool:
    last_trip = diary.trips[-1]

    allowed_purp = last_trip.purp in allowed_purposes
    returns_home = last_trip.dest == diary.home and last_trip.purp == TripPurpose.HOME

    return allowed_purp or returns_home
