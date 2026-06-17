#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from pydantic import NonNegativeFloat

from athenspop.models.base import ImmutableNumericBaseModel


class Activity(ImmutableNumericBaseModel):
    start_time: NonNegativeFloat
    end_time: NonNegativeFloat
    purpose: str
