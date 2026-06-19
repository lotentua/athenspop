import json
from pathlib import Path

import numpy as np
import pytest

from examples.athens.travel_time import AthensTravelTimeResolver, MissingSamplePolicy


def test_athens_travel_time_resolver_returns_integer_seconds_for_known_od() -> None:
    resolver = _resolver()
    assert resolver("1", "2", "car", 0) == 1080
    assert resolver("1", "2", "walk", 0) == 8640
    assert resolver("1", "2", "bus", 0) == 2160


def test_athens_travel_time_resolver_uses_diary_time_origin_to_interpolate_civil_hour() -> None:
    resolver = _resolver()
    assert resolver("1", "2", "car", 0) == 1080
    assert resolver("1", "2", "car", 7_200) == 1440


def test_athens_travel_time_resolver_falls_back_for_nan_and_unknown_zones() -> None:
    resolver = _resolver()
    assert resolver("2", "1", "car", 0) == 960
    assert resolver("999", "1", "car", 0) == 960
    assert resolver("999", "999", "walk", 0) == 2_160


def test_athens_travel_time_resolver_can_preserve_strict_missing_samples() -> None:
    resolver = _resolver(missing_sample_policy="strict")
    with pytest.raises(ValueError, match="Could not resolve a positive finite travel time"):
        resolver("2", "1", "car", 0)
    assert resolver("999", "1", "car", 0) == 960


def test_athens_travel_time_resolver_loads_files(tmp_path: Path) -> None:
    routing_path = tmp_path / "routing.npz"
    zone_encoder_path = tmp_path / "zone_encoder.json"
    np.savez(
        routing_path,
        driving_matrix=_driving_matrix(),
        transit_matrix=_transit_matrix(),
        zonal_lengths=np.array([1.0, 2.0], dtype=np.float64),
    )
    zone_encoder_path.write_text(json.dumps({"1": 0, "2": 1}), encoding="utf-8")
    resolver = AthensTravelTimeResolver.from_files(routing_path=routing_path, zone_encoder_path=zone_encoder_path)
    assert resolver("1", "1", "walk", 0) == 720


def test_athens_travel_time_resolver_loads_migrated_default_resources() -> None:
    resolver = AthensTravelTimeResolver.from_files()
    assert resolver("2", "15", "train", 14_400) > 0
    assert resolver("15", "2", "walk", 46_800) > 0


def test_athens_travel_time_resolver_rejects_unsupported_modes() -> None:
    resolver = _resolver()
    with pytest.raises(ValueError, match="Unsupported travel mode"):
        resolver("1", "2", "hoverboard", 0)


def _resolver(*, missing_sample_policy: MissingSamplePolicy = "finite_mean") -> AthensTravelTimeResolver:
    return AthensTravelTimeResolver(
        driving_matrix_hours=_driving_matrix(),
        transit_matrix_hours=_transit_matrix(),
        zonal_lengths_km=np.array([1.0, 5.0], dtype=np.float64),
        zone_encoder={"1": 0, "2": 1},
        missing_sample_policy=missing_sample_policy,
    )


def _driving_matrix() -> np.ndarray[tuple[int, int, int], np.dtype[np.float64]]:
    matrix = np.full((12, 2, 2), 0.25, dtype=np.float64)
    matrix[:, 0, 1] = np.linspace(0.1, 1.2, 12)
    matrix[:, 1, 0] = np.nan
    return matrix


def _transit_matrix() -> np.ndarray[tuple[int, int, int], np.dtype[np.float64]]:
    matrix = np.full((12, 2, 2), 0.5, dtype=np.float64)
    matrix[:, 0, 1] = np.linspace(0.2, 2.4, 12)
    return matrix
