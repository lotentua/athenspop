#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.


from pydantic import BaseModel, ConfigDict


class BaseDataModel(BaseModel):
    """Base data model."""

    model_config = ConfigDict(
        frozen=True, allow_inf_nan=False, use_attribute_docstrings=True
    )
