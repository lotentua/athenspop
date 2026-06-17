#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.
import json
import time
from typing import Final

import numpy as np
import pandas as pd

from athenspop.core.activity_sequencing import ActivitySequencer
from athenspop.core.imputation.imputation import impute_return_trips
from athenspop.core.imputation.samplers.empirical import EmpiricalDepartureTimeSampler
from athenspop.core.optimal_matching import AppendedData, compute_diary_distances
from athenspop.core.scheduling.refiners.twopass import TwoPassDepartureWindowRefiner
from athenspop.core.scheduling.samplers.uniform import UniformScheduleSampler
from athenspop.core.scheduling.scheduling import DiaryScheduler
from athenspop.io.api import read_survey
from athenspop.io.schema import WindowedSurveySchema, load_schema
from athenspop.models.diaries import SequencedDiary
from athenspop.models.trips import TripPurpose
from examples.v1 import mappings
from examples.v1.travel_time import TravelTimeCalculator

if __name__ == "__main__":
    survey = pd.read_csv("res/survey/preprocessed.csv")
    config: WindowedSurveySchema = load_schema("res/config.toml")

    for trip_index in range(1, 6):
        survey[f"purp{trip_index}"] = survey[f"purp{trip_index}"].map(mappings.purpose)
        survey[f"mode{trip_index}"] = survey[f"mode{trip_index}"].map(mappings.modes)

    unscheduled_diaries = read_survey(survey, config)

    print(len(unscheduled_diaries.success))
    print(len(unscheduled_diaries.failures))

    routing = np.load("res/travel_time/routing.npz")

    with open("res/travel_time/zone_encoder.json") as f:
        zone_encoder = json.load(f)

    bit_generator = np.random.default_rng(seed=0)
    travel_time = TravelTimeCalculator(
        driving_matrix=routing["driving_matrix"],
        transit_matrix=routing["transit_matrix"],
        zonal_lengths=routing["zonal_lengths"],
        zone_encoder=zone_encoder,
    ).calculate

    scheduler = DiaryScheduler(
        window_refiner=TwoPassDepartureWindowRefiner(travel_time=travel_time),
        schedule_sampler=UniformScheduleSampler(
            travel_time=travel_time, generator=bit_generator
        ),
    )

    scheduled_diaries = scheduler.schedule(
        unscheduled_diaries.success, min_activity_duration=0.5
    )

    sampler = EmpiricalDepartureTimeSampler(
        scheduled_diaries.successes, min_activity_duration=0.5, rng=bit_generator
    )

    imputed_diaries = impute_return_trips(
        scheduled_diaries.successes,
        allowed_end_states=[TripPurpose.RECREATION],
        travel_time=travel_time,
        sampler=sampler,
    )

    sequencer = ActivitySequencer(travel_time_fn=travel_time)
    sequenced_diaries = sequencer.compile_sequence(
        imputed_diaries, start_time=4, sampling_rate=15 / 60
    )
    np.save(
        "state_sequences.npy",
        np.asarray([diary.sequence for diary in sequenced_diaries.successes]),
    )
    TIME_WINDOWS: Final[dict[str, tuple[int, int]]] = {  # AM Peak
        "AMP": (7, 10),  # Daytime Off-Peak
        "MID": (10, 16),  # PM Peak
        "PMP": (16, 19),  # Nighttime Off-Peak
        "NHT": (19, 7),
    }

    merged_diaries = []
    for diary in sequenced_diaries.successes:
        sequence = []
        for activity in diary.sequence:
            sequence.append(
                # Trip Purposes
                activity.replace("education", "rigid")
                .replace("work", "rigid")
                .replace("market", "flexible")
                .replace("recreation", "flexible")
                .replace("service", "flexible")
                .replace("other", "flexible")
                # Trip Modes
                .replace("taxi", "car")
                .replace("bicycle", "micromobility")
                .replace("escooter", "micromobility")
            )
        merged_diaries.append(
            SequencedDiary(**diary.model_dump(exclude={"sequence"}), sequence=sequence)
        )

    activities = set()
    for diary in merged_diaries:
        for activity in diary.sequence:
            if activity not in activities:
                print(activity)
                activities.add(activity)

    t0 = time.perf_counter_ns()
    distance_matrix = compute_diary_distances(
        merged_diaries,
        # TODO: embed this info in the diaries so that the user cannot make a mistake
        sequence_start_hour=4,
        sampling_rate_minutes=15,
        appended_data=AppendedData(time_windows=TIME_WINDOWS),
    )
    print((time.perf_counter_ns() - t0) * 1e-6)

    np.save("distance_matrix.npy", distance_matrix)

    _ = 0
