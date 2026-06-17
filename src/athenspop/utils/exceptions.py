#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

############################################################
class ConfigError(Exception):
    pass


class StructureError(Exception):
    pass


############################################################


class BaseDiaryError(Exception):
    def __init__(self, message: str, *, uuid: int) -> None:
        """Base class for all diary processing errors.

        Args:
            uuid:
                The unique diary identifier.
        """
        self._uuid = uuid
        super().__init__(f"UUID {uuid}: {message}" if uuid else message)

    @property
    def uuid(self) -> int | None:
        """The unique diary identifier."""
        return self._uuid


class InvalidDiaryError(BaseDiaryError):
    """Raised when a diary fails to pass through a particular processing stage."""
