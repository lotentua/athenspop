import argparse
import glob
import os
import pathlib
from functools import partial
from typing import Final, TypeAlias

import geopandas as gpd
import numpy as np
import pandas as pd
from testbed.csum.scripts.sequencing.type import PositiveFloat, ResidentialZone
from testbed.csum.scripts.utils.io import (
    sanitize_categorical_column,
    write_json,
    write_numpy,
)
from testbed.csum.scripts.utils.math import Array1D, Array3D

_NUM_FILENAMES: Final[int] = 12

_ResidentialZoneEncoder: TypeAlias = dict[ResidentialZone, int]
_TravelTimeTables: TypeAlias = dict[PositiveFloat, pd.DataFrame]


def prepare_resources(
    src_dirname: pathlib.Path,
    dst_dirname: pathlib.Path,
    mkdirs: bool = True,
    overwrite: bool = True,
) -> None:
    directions_dirname = src_dirname / "directions"
    if not directions_dirname.is_dir():
        raise ValueError(
            f"The provided directory ({src_dirname.resolve().as_posix()}) is missing the 'directions' subdirectory."
            f" "
            f"Hint: The raw resource directory is expected to be in the following form:"
            f"""
.
├── directions/
│   ├── directions_YYYY-MM-DD_HH-MM.csv
│   └── ...
└── zones.gpkg
"""
        )
    directions_filenames = glob.glob(
        (directions_dirname / "directions_*.csv").resolve().as_posix()
    )
    if not directions_filenames:
        raise ValueError(
            f"The provided directory ({src_dirname.resolve().as_posix()}) is missing the required directions files."
            f" "
            f"Hint: The 'directions' subdirectory is expected to contain {_NUM_FILENAMES} files with names matching the following pattern: 'directions_*.csv'."
        )
    if len(directions_filenames) != _NUM_FILENAMES:
        # TODO: Find exactly which files are missing.
        raise ValueError(
            f"The provided directory ({src_dirname.resolve().as_posix()}) is missing some required number of directions files."
            f" "
            f"Hint: The 'directions' subdirectory is expected to contain {_NUM_FILENAMES} files with names matching the following pattern: 'directions_*.csv'."
        )

    driving_tables, transit_tables = _create_travel_time_tables(directions_filenames)

    # TODO: Should this block be moved into the zone encoder factory?
    driving_zone_encoder = _create_zone_encoder(driving_tables)
    transit_zone_encoder = _create_zone_encoder(transit_tables)
    # This shouldn't happen.
    if driving_zone_encoder != transit_zone_encoder:
        raise ValueError("The provided table do not represent the same zones.")

    driving_matrix = _tables_to_matrix(driving_tables, driving_zone_encoder)
    transit_matrix = _tables_to_matrix(transit_tables, transit_zone_encoder)

    zones_filename = src_dirname / "zones.gpkg"
    if not zones_filename.is_file():
        raise ValueError(
            f"The provided directory ({src_dirname.resolve().as_posix()}) is missing 'zones.gpkg'."
            f" "
            f"Hint: The raw resource directory is expected to be in the following form:"
            f"""
.
├── directions/
│   ├── directions_YYYY-MM-DD_HH-MM.csv
│   └── ...
└── zones.gpkg
        """
        )

    zonal_lengths = calculate_characteristic_zonal_length(
        zones_filename, driving_zone_encoder
    )

    # FIXME: Package a metadata file along with the actual resources.
    # with io.BytesIO() as b:
    #     np.savez_compressed(
    #         b,
    #         allow_pickle=False,
    #         driving_table=driving_matrix,
    #         transit_table=transit_matrix,
    #         zonal_lengths=zonal_lengths,
    #     )
    #     numpy_sha256 = hashlib.sha256(b.getvalue()).hexdigest()
    #
    # metadata = {
    #     "creation_date": dt.datetime.now(dt.timezone.utc).isoformat(),
    #     "resources": [
    #         {
    #             "filename": {f"{dst_dirname.parent.name}.npz"},
    #             "format": "Compressed NumPy Binary Archive",
    #             "keys": {
    #                 "driving_matrix": "The pairwise travel time matrix using the road network.",
    #                 "transit_matrix": "The pairwise travel time matrix using public transit routes.",
    #                 "zonal_lengths": "The characteristic zonal lengths used to estimate intrazonal travel times.",
    #             },
    #             "sha256": numpy_sha256,
    #         },
    #         {
    #             "filename": {"zone_encoder.json"},
    #             "format": "JSON (JavaScript Object Notation)",
    #             "keys": {
    #                 "driving_matrix": "The pairwise travel time matrix using the road network.",
    #                 "transit_matrix": "The pairwise travel time matrix using the public transit routes.",
    #                 "zonal_lengths": "The characteristic zonal lengths used to estimate intrazonal travel times.",
    #             },
    #             "sha256": hashlib.sha256(
    #                 json.dumps(driving_zone_encoder, indent=4).encode()
    #             ).hexdigest(),
    #         },
    #     ],
    # }

    write_numpy(
        dst_dirname / dst_dirname.parent.name,
        driving_matrix=driving_matrix,
        transit_matrix=transit_matrix,
        zonal_lengths=zonal_lengths,
        kind="npz_compressed",
        mkdirs=mkdirs,
        overwrite=overwrite,
    )
    write_json(
        dst_dirname / "zone_encoder",
        driving_zone_encoder,
        mkdirs=mkdirs,
        overwrite=overwrite,
        indent=4,
    )


def _create_travel_time_tables(
    directions_filenames: list[str],
) -> tuple[_TravelTimeTables, _TravelTimeTables]:
    driving_tables, transit_tables = {}, {}
    for filename in directions_filenames:
        time = int(
            os.path.basename(filename)
            .rsplit("_", maxsplit=3)[-1]
            .rsplit("-", maxsplit=1)[0]
        )
        if time not in range(2, 26, 2):
            raise RuntimeError(
                f"The time in the provided filename ({filename}) could not be parsed."
                f" "
                f"Hint: The travel time table filenames are expected to be in the following form: 'directions_YYYY-MM-DD_HH-MM.csv'. '"
            )

        # TODO: Verify the CSV.
        table = pd.read_csv(filename)
        if table.empty:
            raise RuntimeError(
                f"Failed to parse the contents of the provided filename ({filename})."
                f" "
                f"Hint: Verify the file integrity."
            )

        for column in ["origin", "destination"]:
            table[column] = table[column].apply(
                partial(sanitize_categorical_column, keep="left")
            )

        driving_tables[time] = table.loc[
            table["mode"] == "driving", ["origin", "destination", "duration_min"]
        ]
        transit_tables[time] = table.loc[
            table["mode"] == "transit", ["origin", "destination", "duration_min"]
        ]

    if len(driving_tables) != len(directions_filenames) or len(transit_tables) != len(
        directions_filenames
    ):
        raise RuntimeError(
            "Failed to fully parse the travel time tables."
            " "
            "Hint: Verify the file integrity."
        )

    return driving_tables, transit_tables


def _create_zone_encoder(
    directions_tables: _TravelTimeTables,
) -> _ResidentialZoneEncoder:
    origin_zones = set()
    destination_zones = set()
    for table in directions_tables.values():
        origin_zones.update(table["origin"].unique())
        destination_zones.update(table["destination"].unique())

    # This shouldn't happen.
    if len(origin_zones.symmetric_difference(destination_zones)) > 0:
        raise RuntimeError(
            "The provided travel time tables do not represent the same trip origin and destination zones."
            " "
            "Hint: Verify the file integrity."
        )

    zone_encoder = {
        # NumPy integers are not JSON-serializable.
        int(actual_zone): encoded_zone
        for encoded_zone, actual_zone in enumerate(sorted(origin_zones))
    }
    # TODO: Verify that 'np.unique(table[["origin","destination"]])' remains constant throughout the iteration.
    # # This shouldn't happen.
    # if len(zone_encoder) != len(directions_tables):
    #     # TODO: Find exactly which files are missing.
    #     raise RuntimeError(
    #         f"The provided travel time tables do not represent all required times"
    #         f" "
    #         f"Hint: Verify the file integrity."
    #     )

    return zone_encoder


def _tables_to_matrix(
    tables: _TravelTimeTables, zone_encoder: _ResidentialZoneEncoder
) -> Array3D[float]:
    num_zones = len(zone_encoder)

    # TODO: Verify the travel time matrix.
    matrix = np.full(
        (_NUM_FILENAMES, num_zones, num_zones),
        # Filling the matrix with NaNs instead of zeros results in the same mean travel time calculations as with the corresponding tables.
        # This is because the tables only consider (30 * 30) - 30 = 870 origin-destination zone pairs (i.e., they do not contain intrazonal trip times), whereas the matrix contains 900 elements.
        fill_value=np.nan,
    )
    for time, table in tables.items():
        origins = table["origin"].map(zone_encoder)
        destinations = table["destination"].map(zone_encoder)
        # Convert the travel time from minutes to hours.
        travel_times = table["duration_min"] / 60

        matrix[
            # Map the time to the corresponding index.
            time % 24 // 2, origins.to_numpy(), destinations.to_numpy()
        ] = travel_times.to_numpy()

    return matrix


def calculate_characteristic_zonal_length(
    filename: pathlib.Path, zone_encoder: _ResidentialZoneEncoder
) -> Array1D[float]:
    table = (
        gpd.read_file(filename)
        # Reproject the data from EPSG:4326 to EPSG:2100 (GGRS87) to ensure accurate area calculations.
        .to_crs("EPSG:2100")
    )

    zones = table["zone_name"].apply(partial(sanitize_categorical_column, keep="left"))
    # Convert the zone area from $\text{m}^{2}$ to $\text{km}^{2}$.
    lengths = np.sqrt(table.area * 1e-6)

    if set(zones) != set(zone_encoder.keys()):
        # TODO: Find exactly what the inconsistency is.
        raise ValueError(
            "The travel time tables does not represent the same residential zones as 'zones.gpkg'."
            " "
            "Hint: Verify the file integrity."
        )

    # TODO: Check whether this block can be vectorized.
    output = np.zeros(len(zone_encoder))
    for zone, length in zip(zones, lengths, strict=True):
        output[zone_encoder[zone]] = length

    return output


def main() -> None:
    # TODO: Clean up the CLI interface.
    parser = argparse.ArgumentParser(
        prog="AthensPop Resource Processor",
        description="Prepare the resources required by AthensPop for trip routing purposes."
        " "
        "NOTE: This program is not part of the core AthensPop library and is meant for internal use only!",
    )
    # https://docs.python.org/3/library/argparse.html#suggest-on-error
    parser.suggest_on_error = True

    parser.add_argument(
        "-src",
        "--src_dirname",
        type=pathlib.Path,
        required=True,
        help="The system path to the raw resource directory."
        " "
        "Hint: The raw resource directory is expected to be in the following form:"
        """
     .
     ├── directions/
     │   ├── directions_YYYY-MM-DD_HH-MM.csv
     │   └── ...
     └── zones.gpkg
         """,
    )

    parser.add_argument(
        "-dst",
        "--dst_dirname",
        type=pathlib.Path,
        required=True,
        help="The system path to the preprocessed resource directory.",
    )

    parser.add_argument(
        "--mkdirs",
        default=True,
        type=bool,
        required=False,
        help="Whether to create the preprocessed resource directory and its parents if they do not already exist in the system."
        " "
        "Defaults to 'True'.",
    )
    parser.add_argument(
        "--overwrite",
        default=True,
        type=bool,
        required=False,
        help="Whether to overwrite the preprocessed resources."
        " "
        "This parameter is ignored if the resources do not exist in the system."
        " "
        "Defaults to 'True'.",
    )

    args = parser.parse_args()
    prepare_resources(
        src_dirname=args.src_dirname,
        dst_dirname=args.dst_dirname,
        mkdirs=args.mkdirs,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
    # prepare_resources(
    #     src_dirname=r"C:\Users\Dimit\PycharmProjects\athenspop\testbed\csum\scripts\resources\routing\raw",
    #     dst_dirname=r"C:\Users\Dimit\PycharmProjects\athenspop\testbed\csum\scripts\resources\routing\preprocessed",
    # )
