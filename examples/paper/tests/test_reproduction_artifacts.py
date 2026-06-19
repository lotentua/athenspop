import json
from pathlib import Path

import numpy as np
import pandas as pd

from examples.paper.reproduce import (
    EXPECTED_ZIP_MEMBER_HASHES,
    SMOKE_ARTIFACT_EXPECTATIONS,
    validate_paper_artifacts,
    verify_paper_sources,
    write_smoke_artifacts,
)


def test_write_smoke_artifacts_materializes_named_paper_outputs(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    assert paths.manifest.exists()
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    assert manifest["workflow"] == "paper_smoke"
    assert manifest["scheduled_diaries"] == 3
    assert manifest["sequence_shape"] == [3, 96]
    source_hashes = json.loads(paths.source_hash_report.read_text(encoding="utf-8"))
    assert source_hashes["all_sources_match"] is True
    assert set(source_hashes["files"]) == {"CSuM2026.pdf", "CSuM2026.zip"}
    assert set(source_hashes["zip_members"]) == set(EXPECTED_ZIP_MEMBER_HASHES)
    input_stage = json.loads(paths.input_stage_report.read_text(encoding="utf-8"))
    assert input_stage["raw_diaries"] == 3
    assert input_stage["canonical_trips"] == 9
    scheduled_trips = pd.read_csv(paths.scheduled_trips)
    assert len(scheduled_trips) == 9
    assert scheduled_trips["departure_second"].notna().all()
    assert scheduled_trips["arrival_second"].notna().all()
    assert {
        "is_imputed_return_home",
        "imputation_method",
        "observed_last_trip_id",
    } <= set(scheduled_trips.columns)
    diary_summary = pd.read_csv(paths.diary_summary)
    assert diary_summary["n_trips"].sum() == 9
    episodes = pd.read_csv(paths.episodes)
    assert episodes.groupby(["household_id", "person_id"])["start_second"].min().eq(0).all()
    assert episodes.groupby(["household_id", "person_id"])["end_second"].max().eq(86400).all()
    state_sequences = np.load(paths.state_sequences)
    compound_sequences = np.load(paths.compound_state_sequences)
    assert state_sequences.shape == (3, 96)
    assert compound_sequences.shape == (3, 96)
    dissimilarity_matrix = np.load(paths.dissimilarity_matrix)
    assert dissimilarity_matrix.shape == (3, 3)
    np.testing.assert_allclose(dissimilarity_matrix, dissimilarity_matrix.T)
    linkage_matrix = np.load(paths.linkage_matrix)
    assert linkage_matrix.shape == (2, 4)
    cluster_labels = pd.read_csv(paths.cluster_labels)
    assert len(cluster_labels) == 3
    diagnostics = json.loads(paths.scheduling_diagnostics.read_text(encoding="utf-8"))
    assert diagnostics["scheduled_diaries"] == 3
    validation = json.loads(paths.validation_report.read_text(encoding="utf-8"))
    assert validation["summary"] == "0 error(s), 0 warning(s), 0 invalid row(s), 0 invalid chain(s)"
    artifact_validation = validate_paper_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    assert artifact_validation.passed


def test_artifact_validation_reports_missing_named_outputs(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    paths.cluster_labels.unlink()
    try:
        validate_paper_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    except ValueError as error:
        message = str(error)
    else:
        message = ""
    assert "cluster_labels" in message


def test_verify_paper_sources_checks_the_method_contract_hashes() -> None:
    source_report = verify_paper_sources(Path.cwd())
    assert source_report["all_sources_match"] is True
    zip_members = source_report["zip_members"]
    assert isinstance(zip_members, dict)
    assert set(zip_members) == set(EXPECTED_ZIP_MEMBER_HASHES)
