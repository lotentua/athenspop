#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


import json

import numpy as np
import pandas as pd

from athenspop.long.parsing import FlexibleTripColumnSpec, parse_flexible
from athenspop.long.scheduling.refinement import refine_departure_windows
from athenspop.long.scheduling.sampling import sample_departures
from examples.v1.travel_time import TravelTimeCalculator

trips = pd.read_csv(r"C:\Documents\athenspop\examples\v1\res\survey\long\trips.csv")

routing = np.load(r"C:\Documents\athenspop\examples\v1\res\travel_time\routing.npz")

with open(r"C:\Documents\athenspop\examples\v1\res\travel_time\zone_encoder.json") as f:
    zone_encoder = json.load(f)

travel_time_fn = TravelTimeCalculator(
    driving_matrix=routing["driving_matrix"],
    transit_matrix=routing["transit_matrix"],
    zonal_lengths=routing["zonal_lengths"],
    zone_encoder=zone_encoder,
).calculate

spec = FlexibleTripColumnSpec(
    pid="pid",
    ozone="ozone",
    dzone="dzone",
    purp="purp",
    mode="mode",
    earliest_departure="min_time",
    latest_departure="max_time",
)

scheduling_results = parse_flexible(
    trips,
    spec=spec,
    travel_time_fn=travel_time_fn,
    min_act_duration=0.5,
    refiner=refine_departure_windows,
    sampler=sample_departures,
    rng=np.random.default_rng(seed=0),
)

_ = 0
