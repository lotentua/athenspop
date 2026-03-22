#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2026 National Technical University of Athens
#  This software is licensed under the MIT License.

"""Base data model for the long scheduling pipeline."""

from pydantic import BaseModel, ConfigDict


class BaseDataModel(BaseModel):
    """Immutable Pydantic base model with strict numeric handling.

    All models in the ``long`` pipeline inherit from this class.
    Instances are frozen after construction and reject ``inf``/``NaN``
    values in numeric fields.
    """

    model_config = ConfigDict(
        frozen=True, allow_inf_nan=False, use_attribute_docstrings=True
    )
