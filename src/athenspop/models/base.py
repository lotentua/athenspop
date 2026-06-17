#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.
from pydantic import BaseModel, ConfigDict


class ImmutableNumericBaseModel(BaseModel):
    """Base class for creating immutable Pydantic models with non-nullable numeric fields."""

    model_config = ConfigDict(
        frozen=True, allow_inf_nan=False, use_attribute_docstrings=True
    )
