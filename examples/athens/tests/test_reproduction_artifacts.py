import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from examples.athens.reproduce import (
    EXPECTED_ATHENS_INPUT_HASHES,
    EXPECTED_ZIP_MEMBER_HASHES,
    SMOKE_ARTIFACT_EXPECTATIONS,
    validate_athens_artifacts,
    validate_paper_result_reference,
    verify_athens_sources,
    write_smoke_artifacts,
)


def test_write_smoke_artifacts_materializes_named_athens_outputs(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    assert paths.manifest.exists()
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    assert manifest["workflow"] == "athens_smoke"
    assert manifest["scheduled_diaries"] == 3
    assert manifest["sequence_shape"] == [3, 96]
    assert manifest["claim_status"] == "smoke_test"
    assert manifest["method"]["unreduced_activity_categories"] == 7
    assert manifest["method"]["unreduced_travel_mode_categories"] == 8
    source_hashes = json.loads(paths.source_hash_report.read_text(encoding="utf-8"))
    assert source_hashes["all_sources_match"] is True
    assert set(source_hashes["files"]) == {"CSuM2026.pdf", "CSuM2026.zip"}
    assert set(source_hashes["zip_members"]) == set(EXPECTED_ZIP_MEMBER_HASHES)
    assert set(source_hashes["inputs"]) == set(EXPECTED_ATHENS_INPUT_HASHES)
    assert source_hashes["software"]["uv_lock_sha256"]
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
    assert (
        episodes.groupby(["household_id", "person_id"])["start_second"]
        .min()
        .eq(0)
        .all()
    )
    assert (
        episodes.groupby(["household_id", "person_id"])["end_second"]
        .max()
        .eq(86400)
        .all()
    )
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
    assert (
        validation["summary"]
        == "0 error(s), 0 warning(s), 0 invalid row(s), 0 invalid chain(s)"
    )
    artifact_validation = validate_athens_artifacts(
        paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS
    )
    assert artifact_validation.passed


def test_artifact_validation_reports_missing_named_outputs(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    paths.cluster_labels.unlink()
    try:
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    except ValueError as error:
        message = str(error)
    else:
        message = ""
    assert "cluster_labels" in message


def test_artifact_validation_rejects_corrupt_cluster_content(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    labels = pd.read_csv(paths.cluster_labels)
    labels.loc[0, "cluster"] = 99
    labels.to_csv(paths.cluster_labels, index=False)

    try:
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    except ValueError as error:
        message = str(error)
    else:
        message = ""
    assert "cluster_labels" in message


def test_artifact_validation_rejects_broken_episode_chain(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    paths.episodes.write_text("garbage\nx\n", encoding="utf-8")

    with pytest.raises(ValueError, match="episodes.partition_and_diary_order"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_compound_sequence_row_swap(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    sequences = np.load(paths.compound_state_sequences)
    sequences[[0, 1]] = sequences[[1, 0]]
    np.save(paths.compound_state_sequences, sequences)

    with pytest.raises(
        ValueError, match="compound_state_sequences.from_state_sequences"
    ):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_false_manifest_claim(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    manifest["claim_status"] = "end_to_end_reproduction"
    paths.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest.claim_status"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rebuilds_demographics_from_persons(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    complete = pd.read_csv(paths.complete_demographic_records)
    complete.loc[0, "gender"] = "corrupt"
    complete.to_csv(paths.complete_demographic_records, index=False)
    _refresh_manifest_hash(
        paths.manifest,
        "complete_demographic_records",
        paths.complete_demographic_records,
    )

    with pytest.raises(ValueError, match="complete_records_from_persons"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_checks_concrete_trip_timing(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    trips = pd.read_csv(paths.scheduled_trips)
    trips.loc[0, "arrival_second"] = trips.loc[0, "departure_second"]
    trips.to_csv(paths.scheduled_trips, index=False)
    _refresh_manifest_hash(paths.manifest, "scheduled_trips", paths.scheduled_trips)

    with pytest.raises(ValueError, match="concrete_positive_integer_timing"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_coordinated_canonical_corruption(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    trips = pd.read_csv(paths.trips)
    trips.loc[1, "trip_id"] = trips.loc[0, "trip_id"]
    trips.loc[0, "earliest_departure_second"] = -1
    trips.to_csv(paths.trips, index=False)
    _refresh_manifest_hash(paths.manifest, "trips", paths.trips)

    with pytest.raises(ValueError, match="data.canonical_table_contract"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_false_scheduled_travel_time(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    trips = pd.read_csv(paths.scheduled_trips)
    trips.loc[0, "travel_time_seconds"] = -999
    trips.to_csv(paths.scheduled_trips, index=False)
    _refresh_manifest_hash(paths.manifest, "scheduled_trips", paths.scheduled_trips)

    with pytest.raises(ValueError, match="concrete_positive_integer_timing"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_short_scheduled_activity(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    trips = pd.read_csv(paths.scheduled_trips)
    first_diary = trips.loc[
        (trips["household_id"] == trips.loc[0, "household_id"])
        & (trips["person_id"] == trips.loc[0, "person_id"])
    ].sort_values("trip_sequence")
    previous = first_diary.index[0]
    following = first_diary.index[1]
    travel_time = int(trips.loc[following, "travel_time_seconds"])
    departure = int(trips.loc[previous, "arrival_second"]) + 1_799
    trips.loc[following, "departure_second"] = departure
    trips.loc[following, "arrival_second"] = departure + travel_time
    trips.to_csv(paths.scheduled_trips, index=False)
    _refresh_manifest_hash(paths.manifest, "scheduled_trips", paths.scheduled_trips)

    with pytest.raises(ValueError, match="concrete_positive_integer_timing"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_artifact_validation_rejects_self_authored_provenance(
    tmp_path: Path,
) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    report = json.loads(paths.source_hash_report.read_text(encoding="utf-8"))
    for section in ("files", "zip_members", "inputs"):
        for record in report[section].values():
            record["sha256"] = "0" * 64
            record["expected_sha256"] = "0" * 64
    report["software"]["uv_lock_sha256"] = "0" * 64
    paths.source_hash_report.write_text(json.dumps(report), encoding="utf-8")
    _refresh_manifest_hash(
        paths.manifest, "source_hash_report", paths.source_hash_report
    )

    with pytest.raises(ValueError, match=r"source_hashes\..*\.contract"):
        validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)


def test_manifest_hashes_cover_each_artifact_category(tmp_path: Path) -> None:
    paths = write_smoke_artifacts(tmp_path / "paper")
    representatives = {
        "trips": paths.trips,
        "source_hash_report": paths.source_hash_report,
        "episodes": paths.episodes,
        "compound_state_sequences": paths.compound_state_sequences,
        "dissimilarity_matrix": paths.dissimilarity_matrix,
        "cluster_labels": paths.cluster_labels,
        "complete_demographic_records": paths.complete_demographic_records,
        "dendrogram_figure": paths.dendrogram_figure,
    }

    for name, path in representatives.items():
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match=rf"artifact_sha256\.{name}"):
            validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
        path.write_bytes(original)


def test_paper_result_reference_rejects_non_reference_arrays(
    tmp_path: Path,
) -> None:
    sequences_path = tmp_path / "state_sequences.npy"
    distance_path = tmp_path / "distance_matrix.npy"
    diary_summary_path = tmp_path / "diary_summary.csv"
    np.save(sequences_path, np.array([["home", "home"]], dtype=np.str_))
    np.save(distance_path, np.zeros((1, 1), dtype=np.float64))
    pd.DataFrame([{"household_id": "1", "person_id": "1"}]).to_csv(
        diary_summary_path, index=False
    )

    validation = validate_paper_result_reference(
        sequences_path, distance_path, diary_summary_path
    )

    assert not validation.passed
    assert {check.name for check in validation.checks} == {
        "paper_reference.state_sequences.file_sha256",
        "paper_reference.state_sequences.shape",
        "paper_reference.dissimilarity_matrix.file_sha256",
        "paper_reference.dissimilarity_matrix.shape",
        "paper_reference.observation_keys.count",
        "paper_reference.observation_keys.sha256",
    }


def test_paper_result_reference_checks_supplied_demographic_oracle(
    tmp_path: Path,
) -> None:
    sequences_path = tmp_path / "state_sequences.npy"
    distance_path = tmp_path / "distance_matrix.npy"
    diary_summary_path = tmp_path / "diary_summary.csv"
    associations_path = tmp_path / "associations.csv"
    np.save(sequences_path, np.array([["home", "home"]], dtype=np.str_))
    np.save(distance_path, np.zeros((1, 1), dtype=np.float64))
    pd.DataFrame([{"household_id": "1", "person_id": "1"}]).to_csv(
        diary_summary_path, index=False
    )
    pd.DataFrame(
        [{"variable_x": "wrong", "variable_y": "wrong", "cramers_v": 0.0}]
    ).to_csv(associations_path, index=False)

    validation = validate_paper_result_reference(
        sequences_path,
        distance_path,
        diary_summary_path,
        demographic_associations_path=associations_path,
    )

    assert "paper_reference.demographics.associations" in {
        check.name for check in validation.checks
    }
    assert not validation.passed


def test_verify_athens_sources_checks_the_method_contract_hashes() -> None:
    source_report = verify_athens_sources(Path.cwd())
    assert source_report["all_sources_match"] is True
    zip_members = source_report["zip_members"]
    assert isinstance(zip_members, dict)
    assert set(zip_members) == set(EXPECTED_ZIP_MEMBER_HASHES)


def test_verify_athens_sources_hashes_the_supplied_survey_path(
    tmp_path: Path,
) -> None:
    survey = tmp_path / "survey.csv"
    survey.write_text("not the paper survey\n", encoding="utf-8")

    with pytest.raises(ValueError, match="raw_diaries_athens_wide.csv"):
        verify_athens_sources(Path.cwd(), wide_diary_path=survey)


def _refresh_manifest_hash(manifest_path: Path, name: str, artifact: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"][name] = (
        sha256(artifact.read_bytes()).hexdigest().upper()
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
