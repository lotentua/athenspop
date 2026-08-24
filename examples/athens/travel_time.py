"""Deterministic CSuM2026 travel-time resolver for the Athens example."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, cast

import numpy as np

from athenspop.time_units import SECONDS_PER_HOUR

type Matrix3D = np.ndarray[tuple[int, int, int], np.dtype[np.float64]]
type Vector1D = np.ndarray[tuple[int], np.dtype[np.float64]]
type MissingSamplePolicy = Literal["finite_mean", "strict"]

DEFAULT_TIME_ORIGIN_CLOCK_HOUR: Final[int] = 4
DEFAULT_SAMPLE_PERIOD_HOURS: Final[int] = 2
DEFAULT_TRAVEL_TIME_DIR: Final[Path] = (
    Path(__file__).resolve().parent / "data" / "travel_time"
)
DEFAULT_ROUTING_PATH: Final[Path] = DEFAULT_TRAVEL_TIME_DIR / "routing.npz"
DEFAULT_ZONE_ENCODER_PATH: Final[Path] = DEFAULT_TRAVEL_TIME_DIR / "zone_encoder.json"

_DRIVING_MODES: Final[frozenset[str]] = frozenset({"car", "motorcycle", "taxi"})
_TRANSIT_MODES: Final[frozenset[str]] = frozenset({"bus", "train"})
_MODE_SPEED_KM_PER_HOUR: Final[dict[str, float]] = {
    "bicycle": 15.0,
    "bus": 35.0,
    "car": 40.0,
    "escooter": 15.0,
    "motorcycle": 40.0,
    "taxi": 40.0,
    "train": 35.0,
    "walk": 5.0,
}


@dataclass(frozen=True, slots=True)
class AthensTravelTimeResolver:
    """Resolve canonical trip travel times from the paper routing matrices."""

    driving_matrix_hours: Matrix3D
    transit_matrix_hours: Matrix3D
    zonal_lengths_km: Vector1D
    zone_encoder: Mapping[str, int]
    time_origin_clock_hour: int = DEFAULT_TIME_ORIGIN_CLOCK_HOUR
    missing_sample_policy: MissingSamplePolicy = "finite_mean"

    def __post_init__(self) -> None:
        """Reject inconsistent routing resources at the construction boundary."""
        if self.driving_matrix_hours.shape != self.transit_matrix_hours.shape:
            raise ValueError("Driving and transit matrices must have the same shape.")
        sample_count, origin_count, destination_count = self.driving_matrix_hours.shape
        if sample_count == 0 or origin_count != destination_count:
            raise ValueError("Routing matrices must contain square zone samples.")
        if self.zonal_lengths_km.shape != (origin_count,):
            raise ValueError(
                "Zonal lengths must contain one value per routing-matrix zone."
            )
        if not np.isfinite(self.zonal_lengths_km).all() or np.any(
            self.zonal_lengths_km <= 0
        ):
            raise ValueError("Zonal lengths must be positive finite values.")
        positions = tuple(self.zone_encoder.values())
        if len(set(positions)) != len(positions) or any(
            isinstance(position, bool)
            or not isinstance(position, int)
            or not 0 <= position < origin_count
            for position in positions
        ):
            raise ValueError(
                "Zone encoder positions must be unique routing-matrix indices."
            )
        if self.missing_sample_policy not in {"finite_mean", "strict"}:
            raise ValueError(
                f"Unsupported missing-sample policy {self.missing_sample_policy!r}."
            )

    @classmethod
    def from_files(
        cls,
        *,
        routing_path: Path = DEFAULT_ROUTING_PATH,
        zone_encoder_path: Path = DEFAULT_ZONE_ENCODER_PATH,
        time_origin_clock_hour: int = DEFAULT_TIME_ORIGIN_CLOCK_HOUR,
        missing_sample_policy: MissingSamplePolicy = "finite_mean",
    ) -> AthensTravelTimeResolver:
        "Load routing matrices and zone encoding from the Athens example data files."
        with np.load(routing_path) as routing:
            driving_matrix = np.asarray(routing["driving_matrix"], dtype=np.float64)
            transit_matrix = np.asarray(routing["transit_matrix"], dtype=np.float64)
            zonal_lengths = np.asarray(routing["zonal_lengths"], dtype=np.float64)
        zone_encoder = _load_zone_encoder(zone_encoder_path)
        return cls(
            driving_matrix_hours=_as_matrix3d(driving_matrix, "driving_matrix"),
            transit_matrix_hours=_as_matrix3d(transit_matrix, "transit_matrix"),
            zonal_lengths_km=_as_vector1d(zonal_lengths, "zonal_lengths"),
            zone_encoder=zone_encoder,
            time_origin_clock_hour=time_origin_clock_hour,
            missing_sample_policy=missing_sample_policy,
        )

    def __call__(
        self, origin: str, destination: str, mode: str, departure_second: int
    ) -> int:
        """Return a strictly positive integer travel time in seconds."""
        canonical_mode = _canonical_mode(mode)
        if origin == destination:
            travel_hours = self._intrazonal_hours(origin, canonical_mode)
        else:
            travel_hours = self._interzonal_hours(
                origin, destination, canonical_mode, departure_second
            )
        if not np.isfinite(travel_hours) or travel_hours <= 0:
            raise ValueError(
                "Could not resolve a positive finite travel time for "
                f"origin={origin!r}, destination={destination!r}, mode={mode!r}, "
                f"departure_second={departure_second}."
            )
        return max(1, int(round(float(travel_hours) * SECONDS_PER_HOUR)))

    def _intrazonal_hours(self, zone: str, mode: str) -> float:
        encoded_zone = self.zone_encoder.get(zone)
        length_km = (
            float(self.zonal_lengths_km[encoded_zone])
            if encoded_zone is not None
            else float(np.nanmean(self.zonal_lengths_km))
        )
        return length_km / _MODE_SPEED_KM_PER_HOUR[mode]

    def _interzonal_hours(
        self, origin: str, destination: str, mode: str, departure_second: int
    ) -> float:
        encoded_origin = self.zone_encoder.get(origin)
        encoded_destination = self.zone_encoder.get(destination)
        if mode in _TRANSIT_MODES:
            matrix = self.transit_matrix_hours
            scaling_factor = 1.0
        else:
            matrix = self.driving_matrix_hours
            scaling_factor = (
                _MODE_SPEED_KM_PER_HOUR["car"] / _MODE_SPEED_KM_PER_HOUR[mode]
            )
        fallback_samples = _finite_time_means(matrix)
        if encoded_origin is None or encoded_destination is None:
            samples = fallback_samples
        else:
            samples = matrix[:, encoded_origin, encoded_destination]
            if self.missing_sample_policy == "finite_mean":
                samples = np.where(np.isfinite(samples), samples, fallback_samples)
        civil_departure_hour = (
            departure_second / SECONDS_PER_HOUR + self.time_origin_clock_hour
        ) % 24
        return (
            float(
                np.interp(
                    civil_departure_hour,
                    xp=_sample_hours(matrix.shape[0]),
                    fp=samples,
                    period=24,
                )
            )
            * scaling_factor
        )


def _load_zone_encoder(path: Path) -> dict[str, int]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError(
            f"`{path}` must contain a JSON object mapping zone ids to integer "
            "positions."
        )
    zone_encoder: dict[str, int] = {}
    for key, value in raw.items():
        if (
            not isinstance(key, str)
            or isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise ValueError(
                f"`{path}` contains invalid zone encoder entry {key!r}: {value!r}."
            )
        zone_encoder[key] = value
    return zone_encoder


def _as_matrix3d(
    array: np.ndarray[tuple[int, ...], np.dtype[np.float64]], name: str
) -> Matrix3D:
    if array.ndim != 3:
        raise ValueError(
            f"`{name}` must be a three-dimensional array, got shape {array.shape}."
        )
    if array.shape[1] != array.shape[2]:
        raise ValueError(
            f"`{name}` must be square by origin/destination zone, got shape "
            f"{array.shape}."
        )
    return cast("Matrix3D", array)


def _as_vector1d(
    array: np.ndarray[tuple[int, ...], np.dtype[np.float64]], name: str
) -> Vector1D:
    if array.ndim != 1:
        raise ValueError(
            f"`{name}` must be a one-dimensional array, got shape {array.shape}."
        )
    return cast("Vector1D", array)


def _finite_time_means(matrix: Matrix3D) -> Vector1D:
    means = np.nanmean(matrix, axis=(1, 2))
    global_mean = float(np.nanmean(matrix))
    if not np.isfinite(global_mean) or global_mean <= 0:
        raise ValueError(
            "Routing matrix does not contain any positive finite travel-time samples."
        )
    return cast("Vector1D", np.where(np.isfinite(means), means, global_mean))


def _sample_hours(sample_count: int) -> Vector1D:
    return cast(
        "Vector1D",
        np.arange(
            0,
            sample_count * DEFAULT_SAMPLE_PERIOD_HOURS,
            DEFAULT_SAMPLE_PERIOD_HOURS,
            dtype=np.float64,
        ),
    )


def _canonical_mode(mode: str) -> str:
    if mode == "service":
        return "car"
    if mode not in _MODE_SPEED_KM_PER_HOUR:
        raise ValueError(f"Unsupported travel mode {mode!r}.")
    return mode
