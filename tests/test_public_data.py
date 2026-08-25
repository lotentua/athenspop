# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""This module defines release contracts for the processed Athens diaries."""

import hashlib
import pathlib
from typing import Final

import pandas as pd

import athenspop.model.survey
import athenspop.validation.schema

#: This path identifies the directory containing the three Athens tables.
DATA_DIRECTORY: Final[pathlib.Path] = (
    pathlib.Path(__file__).resolve().parents[1] / "data" / "athens"
)
#: These pairs bind each immutable CSV payload to its published SHA-256 value.
EXPECTED_HASHES: Final[tuple[tuple[str, str], ...]] = (
    (
        "households.csv",
        "772c4ecc15418f02c34826b190e4773b510de50af8c2409e2956af4cb36ab560",
    ),
    (
        "persons.csv",
        "2a24378c38089ae8ca107181222ef3d15a55d8496df47eef5635c1b60e5b9ab3",
    ),
    (
        "trips.csv",
        "4b36212ae877df944e451b36a121d4a4f688334b421ad9b0666e51346241e591",
    ),
)
#: This digest identifies Creative Commons' authoritative CC BY 4.0 legal code.
EXPECTED_CC_BY_LICENSE_HASH: Final[str] = (
    "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411"
)


def _tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the released households, persons, and trips tables."""
    return (
        pd.read_csv(DATA_DIRECTORY / "households.csv"),
        pd.read_csv(DATA_DIRECTORY / "persons.csv"),
        pd.read_csv(DATA_DIRECTORY / "trips.csv"),
    )


def test_public_data_payloads_have_fixed_hashes_and_row_counts() -> None:
    """Bind the documented product to exact files and observation counts."""
    for filename, expected_hash in EXPECTED_HASHES:
        payload = (DATA_DIRECTORY / filename).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected_hash

    households, persons, trips = _tables()
    assert (len(households), len(persons), len(trips)) == (513, 513, 1_347)


def test_public_data_includes_the_complete_cc_by_four_legal_code() -> None:
    """Match the locally bundled license to the authoritative CC BY legal code."""
    legal_code = (DATA_DIRECTORY / "LICENSE").read_bytes()

    assert hashlib.sha256(legal_code).hexdigest() == EXPECTED_CC_BY_LICENSE_HASH


def test_public_tables_use_stable_columns_keys_and_foreign_keys() -> None:
    """Keep schema names, primary keys, and joins stable for downstream users."""
    households, persons, trips = _tables()
    assert tuple(households.columns) == ("household_id", "home_zone")
    assert tuple(persons.columns) == (
        "household_id",
        "person_id",
        "gender",
        "age_group_years",
        "education_level",
        "employment_status",
        "monthly_income_eur_band",
        "owns_car",
    )
    assert tuple(trips.columns) == (
        "household_id",
        "person_id",
        "trip_id",
        "trip_sequence",
        "origin",
        "destination",
        "purpose",
        "mode",
        "earliest_departure_second",
        "latest_departure_second",
    )
    assert households["household_id"].is_unique
    assert persons[["household_id", "person_id"]].duplicated().sum() == 0
    assert trips["trip_id"].is_unique
    assert set(persons["household_id"]) == set(households["household_id"])
    assert set(trips["household_id"]) == set(households["household_id"])
    assert set(zip(trips["household_id"], trips["person_id"], strict=True)) == set(
        zip(persons["household_id"], persons["person_id"], strict=True)
    )
    assert persons.groupby("household_id").size().eq(1).all()


def test_public_trip_chains_preserve_order_continuity_and_hour_windows() -> None:
    """Keep reported chain order and inclusive one-hour departure bounds exact."""
    _, _, trips = _tables()
    ordered = trips.sort_values(
        ["household_id", "person_id", "trip_sequence"], kind="stable"
    )
    for _, chain in ordered.groupby(["household_id", "person_id"], sort=False):
        assert chain["trip_sequence"].tolist() == list(range(1, len(chain) + 1))
        assert (
            chain["origin"].iloc[1:].tolist() == chain["destination"].iloc[:-1].tolist()
        )
        assert chain["earliest_departure_second"].is_monotonic_increasing
    assert (
        (trips["latest_departure_second"] - trips["earliest_departure_second"])
        .eq(3_599)
        .all()
    )
    assert trips["earliest_departure_second"].mod(3_600).eq(0).all()


def test_public_demographic_and_trip_categories_are_controlled() -> None:
    """Keep normalized category vocabularies and missing-value counts stable."""
    _, persons, trips = _tables()
    expected_person_categories = {
        "gender": {"female", "male"},
        "age_group_years": {
            "18_to_30",
            "31_to_40",
            "41_to_50",
            "51_to_65",
            "66_or_older",
        },
        "education_level": {
            "primary_school",
            "secondary_school",
            "bachelors_degree",
            "masters_or_doctoral_degree",
        },
        "employment_status": {
            "employed",
            "unemployed",
            "student",
            "not_in_labor_force",
        },
        "monthly_income_eur_band": {
            "no_income",
            "up_to_750_eur",
            "750_to_1500_eur",
            "1500_to_2500_eur",
            "2500_eur_or_more",
        },
        "owns_car": {False, True},
    }
    for column, expected in expected_person_categories.items():
        assert set(persons[column].dropna()) == expected
    assert persons.isna().sum().to_dict() == {
        "household_id": 0,
        "person_id": 0,
        "gender": 6,
        "age_group_years": 7,
        "education_level": 2,
        "employment_status": 5,
        "monthly_income_eur_band": 45,
        "owns_car": 0,
    }
    assert set(trips["purpose"]) == {
        "education",
        "home",
        "market",
        "other",
        "recreation",
        "service",
        "work",
    }
    assert set(trips["mode"]) == {
        "bicycle",
        "bus",
        "car",
        "escooter",
        "motorcycle",
        "taxi",
        "train",
        "walk",
    }


def test_public_diary_scope_statistics_remain_explicit() -> None:
    """Bind the limitations reported in the data documentation to the tables."""
    households, _, trips = _tables()
    ordered = trips.sort_values(
        ["household_id", "person_id", "trip_sequence"], kind="stable"
    )
    chains = tuple(
        tuple(group["purpose"])
        for _, group in ordered.groupby(["household_id", "person_id"], sort=False)
    )
    final_destinations = ordered.groupby("household_id", sort=False)[
        "destination"
    ].last()
    home_zones = households.set_index("household_id")["home_zone"]
    maximum_times = ordered.groupby("household_id", sort=False)[
        "latest_departure_second"
    ].max()

    assert len(set(chains)) == 144
    assert {len(chain) for chain in chains} == {2, 3, 4, 5}
    assert int((final_destinations != home_zones).sum()) == 203
    assert int((trips["origin"] == trips["destination"]).sum()) == 373
    assert int((maximum_times > 86_400).sum()) == 102
    assert int((maximum_times > 172_800).sum()) == 4


def test_public_tables_load_without_a_packaged_travel_time_product() -> None:
    """Construct unresolved diaries without a bundled travel-time product."""
    households, persons, trips = _tables()
    result = athenspop.validation.schema.validate_dataframes(
        trips, persons=persons, households=households
    )
    result.report.raise_if_invalid()
    dataset = athenspop.model.survey.SurveyDataset.from_dataframes(
        trips, persons=persons, households=households
    )

    assert len(dataset.diaries) == 513
    assert all(
        trip.arrival_second is None for diary in dataset.diaries for trip in diary.trips
    )
