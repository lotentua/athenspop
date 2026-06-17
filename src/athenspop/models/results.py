#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from athenspop.models.diaries import (
    BaseDiary,
    ConcreteTimeDiary,
    InvalidDiary,
    SequencedDiary,
)

# TODO: Disallow InvalidDiary.
SuccessT_co = TypeVar("SuccessT_co", bound=BaseDiary, covariant=True)
"""Type variable for a diary which successfully passed through a particular processing stage."""


class BaseDiaryResult(BaseModel, Generic[SuccessT_co]):
    """Base class for all diary processing results.

    This class provides an abstraction for returning and propagating processing errors, separating diaries which successfully passed through a particular stage from those which failed.

    Attributes:
        successes:
            The diaries which successfully passed through the stage.
        failures:
            The diaries which failed to pass through the stage.
    """

    model_config = ConfigDict(frozen=True)

    successes: tuple[SuccessT_co, ...]
    failures: tuple[InvalidDiary, ...]

    ############################################################
    def to_dict(
        self, *, drop_demographics: bool = False, drop_failures: bool = False
    ) -> dict[str, Any]:
        """Convert the result to a dictionary.

        Args:
            drop_demographics:
                If True, exclude demographic attributes from the output.
            drop_failures:
                If True, exclude failed diaries from the output.

        Returns:
            A dictionary representation of the result.
        """
        exclude = {}

        if drop_demographics:
            option = {"__all__": {"demographics"}}
            exclude["successes"] = option
            exclude["failures"] = option

        if drop_failures:
            exclude["failures"] = ...

        return self.model_dump(exclude=exclude if exclude else None)


class DiarySchedulingResult(BaseDiaryResult[ConcreteTimeDiary]):
    """Result of scheduling windowed diaries to concrete times."""


class ActivitySequencingResult(BaseDiaryResult[SequencedDiary]):
    """Result of converting trip chains to activity sequences."""


############################################################
