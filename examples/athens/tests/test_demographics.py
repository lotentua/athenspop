from pathlib import Path

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
    assert set(
        zip(
            summary.bivariate["variable_x"],
            summary.bivariate["variable_y"],
            strict=True,
        )
    ) == set(BIVARIATE_PAIRS)

    marginal_svg = tmp_path / "marginal.svg"
    bivariate_svg = tmp_path / "bivariate.svg"
    write_marginal_demographic_svg(summary.marginal, marginal_svg)
    write_bivariate_demographic_svg(summary.bivariate, bivariate_svg)
    assert "Marginal demographic distributions" in marginal_svg.read_text(
        encoding="utf-8"
    )
    assert (
        "Selected bivariate demographic distributions"
        in bivariate_svg.read_text(encoding="utf-8")
    )
