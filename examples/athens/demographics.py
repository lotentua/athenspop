"""Demographic summaries and portable SVG figures for the Athens example."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from itertools import combinations
from math import inf, sqrt
from pathlib import Path
from typing import Final

import pandas as pd
from scipy.stats import chi2_contingency

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
    ("employment_status", "monthly_income"),
    ("age_group", "employment_status"),
    ("education", "employment_status"),
    ("education", "monthly_income"),
)
AGE_BINS: Final[tuple[float, ...]] = (0, 9, 19, 29, 39, 49, 59, 69, 79, inf)
AGE_LABELS: Final[tuple[str, ...]] = (
    "0-9",
    "10-19",
    "20-29",
    "30-39",
    "40-49",
    "50-59",
    "60-69",
    "70-79",
    "80-89",
)


@dataclass(frozen=True, slots=True)
class DemographicSummary:
    """Athens demographic summaries generated from complete respondent records."""

    complete_records: pd.DataFrame
    marginal: pd.DataFrame
    associations: pd.DataFrame
    bivariate: pd.DataFrame


def demographic_summary(persons: pd.DataFrame) -> DemographicSummary:
    """Return complete demographic records plus marginal and bivariate summaries."""
    complete = complete_demographic_records(persons)
    enriched = complete.assign(age_group=_age_groups(complete["age"]))
    marginal = marginal_demographic_summary(enriched)
    associations = demographic_association_summary(enriched)
    selected = associations.head(len(BIVARIATE_PAIRS))
    selected_pairs = tuple(
        (str(variable_x), str(variable_y))
        for variable_x, variable_y in zip(
            selected["variable_x"], selected["variable_y"], strict=True
        )
    )
    bivariate = bivariate_demographic_summary(enriched, pairs=selected_pairs)
    return DemographicSummary(
        complete_records=complete,
        marginal=marginal,
        associations=associations,
        bivariate=bivariate,
    )


def complete_demographic_records(persons: pd.DataFrame) -> pd.DataFrame:
    """Return records complete across the paper demographic variables."""
    missing = [
        column for column in DEMOGRAPHIC_COLUMNS if column not in persons.columns
    ]
    if missing:
        raise ValueError(
            f"Persons table is missing demographic column(s): {', '.join(missing)}."
        )
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


def demographic_association_summary(complete: pd.DataFrame) -> pd.DataFrame:
    """Rank all off-diagonal demographic pairs by corrected Cramer's V."""
    rows = [
        {
            "variable_x": variable_x,
            "variable_y": variable_y,
            "cramers_v": bias_corrected_cramers_v(
                complete[variable_x], complete[variable_y]
            ),
        }
        for variable_x, variable_y in combinations(CATEGORICAL_COLUMNS, 2)
    ]
    return pd.DataFrame(rows).sort_values(
        "cramers_v", ascending=False, ignore_index=True
    )


def bivariate_demographic_summary(
    complete: pd.DataFrame,
    *,
    pairs: tuple[tuple[str, str], ...] | None = None,
) -> pd.DataFrame:
    """Return counts, shares, and Cramer's V for the paper's selected pairs."""
    rows: list[dict[str, str | int | float]] = []
    total = len(complete)
    if pairs is None:
        ranked = demographic_association_summary(complete).head(len(BIVARIATE_PAIRS))
        selected_pairs = tuple(
            (str(variable_x), str(variable_y))
            for variable_x, variable_y in zip(
                ranked["variable_x"], ranked["variable_y"], strict=True
            )
        )
    else:
        selected_pairs = pairs
    for variable_x, variable_y in selected_pairs:
        association = bias_corrected_cramers_v(
            complete[variable_x], complete[variable_y]
        )
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
                    "cramers_v": association,
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
            "cramers_v",
        ],
    )


def bias_corrected_cramers_v(first: pd.Series, second: pd.Series) -> float:
    """Return the Bergsma bias-corrected Cramer's V association."""
    contingency = pd.crosstab(first, second)
    sample_size = int(contingency.to_numpy().sum())
    if sample_size <= 1:
        return 0.0
    chi_squared, _, _, _ = chi2_contingency(contingency, correction=False)
    rows, columns = contingency.shape
    phi_squared = chi_squared / sample_size
    corrected_phi_squared = max(
        0.0,
        phi_squared - ((columns - 1) * (rows - 1)) / (sample_size - 1),
    )
    corrected_columns = columns - (columns - 1) ** 2 / (sample_size - 1)
    corrected_rows = rows - (rows - 1) ** 2 / (sample_size - 1)
    denominator = min(corrected_columns - 1, corrected_rows - 1)
    return 0.0 if denominator <= 0 else sqrt(corrected_phi_squared / denominator)


def write_marginal_demographic_svg(summary: pd.DataFrame, path: Path) -> None:
    """Write a compact SVG bar chart for marginal demographic shares."""
    width = 960
    row_height = 22
    left = 220
    bar_width = 560
    height = 50 + row_height * len(summary)
    lines = [
        _svg_header(width, height),
        (
            '<text x="20" y="28" font-size="18" font-family="Arial">'
            "Marginal demographic distributions</text>"
        ),
    ]
    for index, (_, row) in enumerate(summary.iterrows()):
        y = 50 + index * row_height
        label = f"{row['variable']}: {row['category']}"
        count = int(row["count"])
        share = float(row["share"])
        lines.append(
            f'<text x="20" y="{y + 14}" font-size="12" '
            f'font-family="Arial">{escape(label)}</text>'
        )
        lines.append(
            f'<rect x="{left}" y="{y}" width="{share * bar_width:.2f}" '
            'height="14" fill="#357ABD" />'
        )
        lines.append(
            f'<text x="{left + bar_width + 12}" y="{y + 12}" font-size="12" '
            f'font-family="Arial">{count} ({share:.1%})</text>'
        )
    lines.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bivariate_demographic_svg(summary: pd.DataFrame, path: Path) -> None:
    """Write a compact SVG listing the largest selected bivariate cells."""
    sorted_summary = summary.sort_values(
        ["variable_x", "variable_y", "count"], ascending=[True, True, False]
    )
    rows = sorted_summary.groupby(["variable_x", "variable_y"], sort=False).head(8)
    width = 1120
    row_height = 22
    left = 360
    bar_width = 520
    height = 50 + row_height * len(rows)
    lines = [
        _svg_header(width, height),
        (
            '<text x="20" y="28" font-size="18" font-family="Arial">'
            "Selected bivariate demographic distributions</text>"
        ),
    ]
    for index, (_, row) in enumerate(rows.iterrows()):
        y = 50 + index * row_height
        label = (
            f"{row['variable_x']}/{row['variable_y']}: {row['category_x']} | "
            f"{row['category_y']}"
        )
        count = int(row["count"])
        share = float(row["share"])
        association = float(row["cramers_v"])
        lines.append(
            f'<text x="20" y="{y + 14}" font-size="12" '
            f'font-family="Arial">{escape(label)}</text>'
        )
        lines.append(
            f'<rect x="{left}" y="{y}" width="{share * bar_width:.2f}" '
            'height="14" fill="#8A5A9E" />'
        )
        lines.append(
            f'<text x="{left + bar_width + 12}" y="{y + 12}" font-size="12" '
            f'font-family="Arial">{count} ({share:.1%}); '
            f"V={association:.3f}</text>"
        )
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
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
