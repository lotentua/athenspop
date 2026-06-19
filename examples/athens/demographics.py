"""Demographic summaries and portable SVG figures for the Athens example."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Final

import pandas as pd

DEMOGRAPHIC_COLUMNS: Final[tuple[str, ...]] = (
    "gender",
    "age",
    "education",
    "employment_status",
    "monthly_income",
    "car_ownership",
)
CATEGORICAL_COLUMNS: Final[tuple[str, ...]] = (
    "gender",
    "age_group",
    "education",
    "employment_status",
    "monthly_income",
    "car_ownership",
)
BIVARIATE_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("gender", "car_ownership"),
    ("age_group", "employment_status"),
    ("education", "monthly_income"),
    ("employment_status", "monthly_income"),
)
AGE_BINS: Final[tuple[int, ...]] = (0, 24, 34, 44, 54, 64, 200)
AGE_LABELS: Final[tuple[str, ...]] = (
    "18-24",
    "25-34",
    "35-44",
    "45-54",
    "55-64",
    "65+",
)


@dataclass(frozen=True, slots=True)
class DemographicSummary:
    """Athens demographic summaries generated from complete respondent records."""

    complete_records: pd.DataFrame
    marginal: pd.DataFrame
    bivariate: pd.DataFrame


def demographic_summary(persons: pd.DataFrame) -> DemographicSummary:
    """Return complete demographic records plus marginal and bivariate summaries."""
    complete = complete_demographic_records(persons)
    enriched = complete.assign(age_group=_age_groups(complete["age"]))
    marginal = marginal_demographic_summary(enriched)
    bivariate = bivariate_demographic_summary(enriched)
    return DemographicSummary(complete_records=complete, marginal=marginal, bivariate=bivariate)


def complete_demographic_records(persons: pd.DataFrame) -> pd.DataFrame:
    """Return records complete across the paper demographic variables."""
    missing = [column for column in DEMOGRAPHIC_COLUMNS if column not in persons.columns]
    if missing:
        raise ValueError(f"Persons table is missing demographic column(s): {', '.join(missing)}.")
    return persons.dropna(subset=list(DEMOGRAPHIC_COLUMNS)).copy()


def marginal_demographic_summary(complete: pd.DataFrame) -> pd.DataFrame:
    """Return counts and shares by one demographic variable at a time."""
    rows: list[dict[str, str | int | float]] = []
    total = len(complete)
    for variable in CATEGORICAL_COLUMNS:
        counts = complete[variable].astype(str).value_counts(sort=False)
        for category, count in counts.items():
            rows.append(
                {
                    "variable": variable,
                    "category": str(category),
                    "count": int(count),
                    "share": int(count) / total,
                }
            )
    return pd.DataFrame(rows, columns=["variable", "category", "count", "share"])


def bivariate_demographic_summary(complete: pd.DataFrame) -> pd.DataFrame:
    """Return counts and shares for the v1 selected demographic pairs."""
    rows: list[dict[str, str | int | float]] = []
    total = len(complete)
    for variable_x, variable_y in BIVARIATE_PAIRS:
        counts: dict[tuple[str, str], int] = {}
        for _, record in complete.iterrows():
            key = (str(record[variable_x]), str(record[variable_y]))
            counts[key] = counts.get(key, 0) + 1
        for category_x, category_y in counts:
            count = counts[(category_x, category_y)]
            rows.append(
                {
                    "variable_x": variable_x,
                    "variable_y": variable_y,
                    "category_x": category_x,
                    "category_y": category_y,
                    "count": count,
                    "share": count / total,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "variable_x",
            "variable_y",
            "category_x",
            "category_y",
            "count",
            "share",
        ],
    )


def write_marginal_demographic_svg(summary: pd.DataFrame, path: Path) -> None:
    """Write a compact SVG bar chart for marginal demographic shares."""
    width = 960
    row_height = 22
    left = 220
    bar_width = 560
    height = 50 + row_height * len(summary)
    lines = [
        _svg_header(width, height),
        '<text x="20" y="28" font-size="18" font-family="Arial">Marginal demographic distributions</text>',
    ]
    for index, (_, row) in enumerate(summary.iterrows()):
        y = 50 + index * row_height
        label = f"{row['variable']}: {row['category']}"
        count = int(row["count"])
        share = float(row["share"])
        lines.append(f'<text x="20" y="{y + 14}" font-size="12" font-family="Arial">{escape(label)}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{share * bar_width:.2f}" height="14" fill="#357ABD" />')
        lines.append(f'<text x="{left + bar_width + 12}" y="{y + 12}" font-size="12" font-family="Arial">{count} ({share:.1%})</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bivariate_demographic_svg(summary: pd.DataFrame, path: Path) -> None:
    """Write a compact SVG listing the largest selected bivariate cells."""
    sorted_summary = summary.sort_values(["variable_x", "variable_y", "count"], ascending=[True, True, False])
    rows = sorted_summary.groupby(["variable_x", "variable_y"], sort=False).head(8)
    width = 1120
    row_height = 22
    left = 360
    bar_width = 520
    height = 50 + row_height * len(rows)
    lines = [
        _svg_header(width, height),
        '<text x="20" y="28" font-size="18" font-family="Arial">Selected bivariate demographic distributions</text>',
    ]
    for index, (_, row) in enumerate(rows.iterrows()):
        y = 50 + index * row_height
        label = f"{row['variable_x']}/{row['variable_y']}: {row['category_x']} | {row['category_y']}"
        count = int(row["count"])
        share = float(row["share"])
        lines.append(f'<text x="20" y="{y + 14}" font-size="12" font-family="Arial">{escape(label)}</text>')
        lines.append(f'<rect x="{left}" y="{y}" width="{share * bar_width:.2f}" height="14" fill="#8A5A9E" />')
        lines.append(f'<text x="{left + bar_width + 12}" y="{y + 12}" font-size="12" font-family="Arial">{count} ({share:.1%})</text>')
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _age_groups(age: pd.Series) -> pd.Series:
    return pd.cut(
        age.astype(float),
        bins=list(AGE_BINS),
        labels=list(AGE_LABELS),
        right=True,
        include_lowest=True,
    ).astype(str)


def _svg_header(width: int, height: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
