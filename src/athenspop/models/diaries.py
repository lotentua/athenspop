#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

from typing import Any

from athenspop.models.base import ImmutableNumericBaseModel
from athenspop.models.trips import ConcreteTrip, WindowedTrip


class BaseDiary(ImmutableNumericBaseModel):
    """Base class for all diary types.

    A diary represents a complete record of a particular person's activities and trips over a specified time period.

    Attributes:
        uuid:
            The unique diary identifier.
        home:
            The unique home identifier.
        attrs:
            Household- and person-level attributes (e.g., demographics).
    """

    # TODO: Narrow down integer types.
    uuid: int
    home: int
    attrs: dict[str, Any]


class ConcreteTimeDiary(BaseDiary):
    """A diary with concrete trips departure times.

    Attributes:
        trips:
            The ordered trip sequence.

    See Also:
        WindowedTimeDiary
    """

    trips: tuple[ConcreteTrip, ...]


class WindowedTimeDiary(BaseDiary):
    """A diary with variable trip departure times.

    Attributes:
        trips:
            The ordered trip sequence.

    See Also:
        ConcreteTimeDiary
    """

    trips: tuple[WindowedTrip, ...]


class SequencedDiary(ConcreteTimeDiary):
    """A diary with an activity sequence derived from trips.

    Attributes:
        sequence:
            The sequence of activity labels between trips.
    """

    sequence: tuple[str, ...]


# TODO: Make this generic.
class InvalidDiary(BaseDiary):
    """A diary which failed to pass through a particular processing stage.

    Attributes:
        reason:
            The corresponding error message.
    """

    reason: str
