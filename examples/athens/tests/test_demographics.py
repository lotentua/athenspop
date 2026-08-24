from pathlib import Path

import pytest

from examples.athens.demographics import (
    BIVARIATE_PAIRS,
    CATEGORICAL_COLUMNS,
    demographic_summary,
    write_bivariate_demographic_svg,
    write_marginal_demographic_svg,
)
from examples.athens.inputs import load_athens_wide_diaries


def test_athens_demographic_summary_uses_461_complete_records(
    tmp_path: Path,
) -> None:
    tables = load_athens_wide_diaries(fixture_travel_time_seconds=None)
    summary = demographic_summary(tables.persons)

    assert len(summary.complete_records) == 461
    assert set(summary.marginal["variable"]) == set(CATEGORICAL_COLUMNS)
    totals = summary.marginal.groupby("variable")["count"].sum()
    assert totals.eq(461).all()
    assert len(summary.associations) == 15
    assert (
        tuple(
            zip(
                summary.associations["variable_x"].head(4),
                summary.associations["variable_y"].head(4),
                strict=True,
            )
        )
        == BIVARIATE_PAIRS
    )
    assert set(
        zip(
            summary.bivariate["variable_x"],
            summary.bivariate["variable_y"],
            strict=True,
        )
    ) == set(BIVARIATE_PAIRS)
    associations = (
        summary.bivariate.groupby(["variable_x", "variable_y"])["cramers_v"]
        .first()
        .to_dict()
    )
    assert associations == pytest.approx(
        {
            ("employment_status", "monthly_income"): 0.4573093033275265,
            ("age_group", "employment_status"): 0.45214118722057955,
            ("education", "employment_status"): 0.410251653543263,
            ("education", "monthly_income"): 0.3921678366572207,
        }
    )

    marginal_svg = tmp_path / "marginal.svg"
    bivariate_svg = tmp_path / "bivariate.svg"
    write_marginal_demographic_svg(summary.marginal, marginal_svg)
    write_bivariate_demographic_svg(summary.bivariate, bivariate_svg)
    assert "Marginal demographic distributions" in marginal_svg.read_text(
        encoding="utf-8"
    )
    assert "Selected bivariate demographic distributions" in bivariate_svg.read_text(
        encoding="utf-8"
    )


def test_demographic_summary_rejects_missing_method_columns() -> None:
    persons = load_athens_wide_diaries().persons.drop(columns="monthly_income")

    with pytest.raises(ValueError, match="missing demographic column.*monthly_income"):
        demographic_summary(persons)
