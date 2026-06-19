"""Thin CSV wrappers around pandas and the validated dataframe loader."""

from os import PathLike

import pandas as pd

from athenspop.model import SurveyDataset, TravelTimeFn

type CsvPath = str | PathLike[str]


def read_survey_dataframes(
    trips_path: CsvPath,
    persons_path: CsvPath | None = None,
    households_path: CsvPath | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None]:
    """Read survey CSV files as dataframes without validation side effects.

    Args:
        trips_path: CSV path for the required trip table.
        persons_path: Optional CSV path for the person table.
        households_path: Optional CSV path for the household table.

    Returns:
        Tuple containing the trip dataframe and optional person and household dataframes.
    """
    trips = pd.read_csv(trips_path)
    persons = None if persons_path is None else pd.read_csv(persons_path)
    households = None if households_path is None else pd.read_csv(households_path)
    return trips, persons, households


def read_survey_csvs(
    trips_path: CsvPath,
    persons_path: CsvPath | None = None,
    households_path: CsvPath | None = None,
    *,
    travel_time_fn: TravelTimeFn | None = None,
) -> SurveyDataset:
    """Read survey CSV files and build a validated survey dataset.

    Args:
        trips_path: CSV path for the required trip table.
        persons_path: Optional CSV path for the person table.
        households_path: Optional CSV path for the household table.
        travel_time_fn: Optional callable returning positive integer travel seconds for timing patterns that need external travel times.

    Returns:
        Trusted survey dataset built from the CSV inputs.

    Raises:
        ValidationError: If dataframe validation collected any hard errors.
        ValueError: If `travel_time_fn` is needed and returns an invalid value.
    """
    trips, persons, households = read_survey_dataframes(trips_path, persons_path=persons_path, households_path=households_path)
    return SurveyDataset.from_dataframes(trips, persons=persons, households=households, travel_time_fn=travel_time_fn)
