#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

import json
import pathlib
from enum import IntFlag, auto
from functools import partial
from typing import Any, Literal, Unpack

import numpy as np
import numpy.typing as npt


def sanitize_categorical_column(data: str, keep: Literal["left", "right"]) -> int | str:
    output = (
        data.strip()
        .replace(":", "")
        .split(" ", maxsplit=2)[0 if keep == "left" else -1]
    )
    if keep == "left":
        output = int(output)

    return output


def read_json(filename: str) -> dict[Any, Any]:
    with open(filename) as f:
        return json.load(f)


def write_json(
    filename: str, data: dict[Any, Any], mkdirs: bool, overwrite: bool, **kwargs
) -> None:
    filename = _prepare_filename(filename, suffix=".json", mkdirs=mkdirs)
    if not _is_writable(filename, overwrite=overwrite):
        return

    with open(filename, mode="w") as f:
        json.dump(data, f, **kwargs)


def read_numpy(filename: str) -> npt.NDArray:
    return np.load(filename)


def write_numpy(
    filename: str,  # TODO: Check this type hint.
    *args: Unpack[npt.NDArray],
    kind: Literal["npy", "npz", "npz_compressed"],
    mkdirs: bool,
    overwrite: bool,
    # TODO: Check this type hint.
    **kwargs: Unpack[npt.NDArray],
) -> None:
    filename = _prepare_filename(
        filename, suffix=".npy" if kind == "npy" else ".npz", mkdirs=mkdirs
    )
    if not _is_writable(filename, overwrite=overwrite):
        return

    if kind == "npy":
        if not args:
            raise ValueError(
                "The '.npy' file format expects exactly one unnamed array."
            )
        if len(args) > 1:
            raise ValueError("The '.npy' file format does not support multiple arrays.")
        if kwargs:
            raise ValueError("The '.npy' file format does not support named arrays.")
        writer = partial(np.save, allow_pickle=False)
    elif kind == "npz":
        writer = partial(np.savez, allow_pickle=False)
    elif kind == "npz_compressed":
        writer = partial(np.savez_compressed, allow_pickle=False)
    else:
        raise ValueError(
            f"Invalid file format: '{kind}'."
            f" "
            f"Hint: The supported file formats are 'npy', 'npz', 'npz_compressed'."
        )

    writer(filename, *args, **kwargs)


def _prepare_filename(filename: str, suffix: str, mkdirs: bool) -> pathlib.Path:
    filename = pathlib.Path(filename)
    if not filename.suffix:
        filename = filename.with_suffix(suffix)

    if mkdirs:
        filename.parent.mkdir(parents=True, exist_ok=True)

    return filename


def _is_writable(filename: pathlib.Path, overwrite: bool) -> bool:
    if filename.is_file():
        if overwrite:
            print(
                f"The provided filename ({filename.resolve().as_posix()}) points to an existing file.)"
                f" "
                f"The file will be overwritten."
            )
            return True
        print(
            f"The provided filename ({filename.resolve().as_posix()}) points to an existing file.)"
            f" "
            f"The file will not be overwritten."
        )
        return False
    print(
        f"The provided filename ({filename.resolve().as_posix()}) does not point to an existing file.)"
        f" "
        f"The 'overwrite' flag will be ignored."
    )
    return True


class ArrayCheck(IntFlag):
    # Constraints
    TARGET_ROW_SUM = auto()
    TARGET_SIGN = auto()

    # Properties
    HOLLOW = auto()
    SQUARE = auto()
    SYMMETRIC = auto()

    DISTANCE_MATRIX = HOLLOW | SYMMETRIC


def check_array(
    data: np.ndarray[tuple[Any, Any], np.dtype[np.number]],
    check: ArrayCheck,
    target: float | np.number | None = None,
) -> bool:
    if check & ArrayCheck.TARGET_ROW_SUM:
        _validate_target(target)
        if not np.all(np.isclose(data.sum(axis=1), target)):
            return False

    # TODO:Clean up this block.
    # TODO: Add a 'strict' flag parameter to disallow zeros.
    if check & ArrayCheck.TARGET_SIGN:
        _validate_target(target)
        if target == -1:
            if not np.all(data <= 0):
                return False
        elif target == 1:
            if not np.all(data >= 0):
                return False
        else:
            raise ValueError(
                "The provided target value must be either -1 or 1 when performing sign checks."
            )

    if check & ArrayCheck.HOLLOW:
        if not np.allclose(np.diag(data), 0):
            return False

    if check & ArrayCheck.SQUARE:
        if data.shape[0] != data.shape[1]:
            return False

    if check & ArrayCheck.SYMMETRIC:
        if not np.allclose(data, data.T):
            return False

    return True


def _validate_target(target):
    if target is None:
        raise ValueError(
            "A target value must be provided when performing constraint-like checks."
        )
