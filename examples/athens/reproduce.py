"""Write canonical paper-pipeline artifacts to disk."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Final
from zipfile import ZipFile

import numpy as np
import pandas as pd

from athenspop.model import Diary
from athenspop.scheduling import ScheduledSurveyDataset
from athenspop.sequence import (
    Episode,
    episodes_from_diary,
    state_sequence_from_diary,
)
from examples.athens.demographics import (
    demographic_summary,
    write_bivariate_demographic_svg,
    write_marginal_demographic_svg,
)
from examples.athens.imputation import impute_athens_return_home_trips
from examples.athens.inputs import (
    DEFAULT_ATHENS_WIDE_DIARY_PATH,
    AthensInputTables,
    load_athens_wide_diaries,
    load_wide_diary_fixture,
)
from examples.athens.method import (
    athens_travel_state,
    substitution_costs,
    transition_counts,
)
from examples.athens.smoke import AthensSmokeOutputs, run_pipeline
from examples.athens.travel_time import AthensTravelTimeResolver
from examples.athens.visualization import (
    cluster_time_distribution,
    write_cut_dendrogram_distribution_svg,
)

type JsonValue = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)
type MetadataValue = None | bool | int | float | str

EXPECTED_ATHENS_SOURCE_HASHES: Final[dict[str, str]] = {
    "CSuM2026.zip": "2EA15A9D1448FB29CFCDE5DA0C2BD3D515D52442EE558E41841138644A297841",
    "CSuM2026.pdf": "5BC2AA37934F458B1E56BF8581F0A7FE7A156535AF59BD3FF98A0ED27BFACEE1",
}
EXPECTED_ZIP_MEMBER_HASHES: Final[dict[str, str]] = {
    "main.tex": "0C88CC332459B59FD0977B4D6C961547D32BA1DF6D240B53D54354D9B32161AE",
    "methods.tex": "59F7A9F030124BBB49A0D6545130AC852B84E742DD0683DA56CF6AB76A0CECC0",
    "results.tex": "58C80CF04493FB2F21F7E3998C3C05CA0CC6A5A3E7A5D7937E02CA4913ABDE8B",
    "intro.tex": "7E86656D9DF6FB5D96888D8953DD818F970CFC81CBD2C91EDAEB61097B519792",
    "conclusion.tex": "AF1C6C3D81001426071475C9E772475DE9C1AFA13425A6C53591C1543B8808C8",
    "CSuM2026.bib": "959845FCF78B5AC45DD714DF981C98B04479751B49AADD4B19B20E4128A2737B",
    "figures/MarginalDistributions.pgf": "395E505044F8C84E81C816E97061C883303BB17B0A1327C3EB341CCB17594AC8",
    "figures/BivariateDistributions.pgf": "1AF15D42D8CFB96536F6FBE06D81A34E01F308341E779BAB66653B929883E5AE",
    "figures/Dendrogram.pdf": "499D74210B23307725DF8BE07F6EB636DB6A29FDFEBDE79885D6883E6666EDA1",
    "figures/Dendrogram.pgf": "44C5211D0B2DE43E35B6AF8BE08CF505EDDD473CC0F9EB2B2C947EC82BA5D0B0",
    "figures/Dendrogram.eps": "272246A30AFA93D8F11DB8DE0487A9338535FE0A3EF0A4A1962E09D86E319BF3",
}


@dataclass(frozen=True, slots=True)
class AthensArtifactPaths:
    """Named artifact paths written by a paper reproduction workflow."""

    root: Path
    trips: Path
    persons: Path
    households: Path
    manifest: Path
    source_hash_report: Path
    input_stage_report: Path
    validation_report: Path
    scheduling_diagnostics: Path
    scheduled_trips: Path
    diary_summary: Path
    episodes: Path
    state_sequences: Path
    compound_state_sequences: Path
    transition_counts: Path
    substitution_costs: Path
    dissimilarity_matrix: Path
    linkage_matrix: Path
    cluster_labels: Path
    cluster_summaries: Path
    cluster_state_distribution: Path
    cluster_time_distribution: Path
    dendrogram_layout: Path
    dendrogram_figure: Path
    complete_demographic_records: Path
    marginal_demographics: Path
    bivariate_demographics: Path
    marginal_demographic_figure: Path
    bivariate_demographic_figure: Path


@dataclass(frozen=True, slots=True)
class AthensArtifactExpectations:
    """Expected stage counts and shapes for an artifact workflow."""

    workflow: str
    raw_diaries: int
    canonical_trips: int
    attempted_diaries: int
    scheduled_diaries: int
    sequence_shape: tuple[int, int]
    dissimilarity_shape: tuple[int, int]
    linkage_shape: tuple[int, int]
    cluster_count: int
    imputed_return_home_trips: int
    complete_demographic_records: int
    infeasible_diaries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AthensArtifactCheck:
    """One artifact validation check result."""

    name: str
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class AthensArtifactValidation:
    """Validation report for a written paper artifact directory."""

    root: Path
    checks: tuple[AthensArtifactCheck, ...]

    @property
    def passed(self) -> bool:
        """Return whether every artifact validation check passed."""
        return all(check.passed for check in self.checks)

    def raise_if_invalid(self) -> None:
        """Raise `ValueError` with every failing artifact check."""
        failures = tuple(check for check in self.checks if not check.passed)
        if failures:
            details = "; ".join(
                f"{check.name}: {check.message}" for check in failures
            )
            raise ValueError(f"Athens artifact validation failed: {details}")


SMOKE_ARTIFACT_EXPECTATIONS: Final[AthensArtifactExpectations] = (
    AthensArtifactExpectations(
        workflow="athens_smoke",
        raw_diaries=3,
        canonical_trips=9,
        attempted_diaries=3,
        scheduled_diaries=3,
        sequence_shape=(3, 96),
        dissimilarity_shape=(3, 3),
        linkage_shape=(2, 4),
        cluster_count=2,
        imputed_return_home_trips=0,
        complete_demographic_records=0,
        infeasible_diaries=(),
    )
)
FULL_ARTIFACT_EXPECTATIONS: Final[AthensArtifactExpectations] = (
    AthensArtifactExpectations(
        workflow="athens_full",
        raw_diaries=513,
        canonical_trips=1347,
        attempted_diaries=513,
        scheduled_diaries=512,
        sequence_shape=(512, 96),
        dissimilarity_shape=(512, 512),
        linkage_shape=(511, 4),
        cluster_count=10,
        imputed_return_home_trips=124,
        complete_demographic_records=461,
        infeasible_diaries=("household_id=549; person_id=549",),
    )
)


def write_smoke_artifacts(
    output_root: Path,
    *,
    source_root: Path | None = None,
    wide_diary_path: Path | None = None,
) -> AthensArtifactPaths:
    """Run the canonical smoke workflow and write named artifacts under `output_root`."""
    root = output_root.resolve()
    resolved_source_root = Path.cwd() if source_root is None else source_root
    resolved_wide_diary_path = (
        Path("tests/example_data/NEW_diaries_athens_final.csv")
        if wide_diary_path is None
        else wide_diary_path
    )
    root.mkdir(parents=True, exist_ok=True)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    input_tables = load_wide_diary_fixture(resolved_wide_diary_path)
    outputs = run_pipeline(
        input_tables.trips, input_tables.persons, input_tables.households
    )
    paths = _write_artifacts(
        root=root,
        input_tables=input_tables,
        wide_diary_path=resolved_wide_diary_path,
        source_report=verify_athens_sources(resolved_source_root),
        outputs=outputs,
        workflow="athens_smoke",
        description="Tiny deterministic artifact-writing workflow for fast tests and documentation smoke checks.",
    )
    validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    return paths


def write_full_artifacts(
    output_root: Path,
    *,
    source_root: Path | None = None,
    wide_diary_path: Path = DEFAULT_ATHENS_WIDE_DIARY_PATH,
) -> AthensArtifactPaths:
    """Run the migrated 513-diary paper workflow and write named artifacts under `output_root`."""
    root = output_root.resolve()
    resolved_source_root = Path.cwd() if source_root is None else source_root
    root.mkdir(parents=True, exist_ok=True)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    input_tables = load_athens_wide_diaries(
        wide_diary_path, fixture_travel_time_seconds=None
    )
    travel_time_resolver = AthensTravelTimeResolver.from_files(
        missing_sample_policy="strict"
    )
    imputed_return_travel_time_resolver = AthensTravelTimeResolver.from_files(
        missing_sample_policy="finite_mean"
    )

    def impute_return_home(
        scheduled: ScheduledSurveyDataset,
    ) -> ScheduledSurveyDataset:
        return impute_athens_return_home_trips(
            scheduled,
            travel_time_function=imputed_return_travel_time_resolver,
            seed=2026,
            min_activity_duration_seconds=1800,
        )

    outputs = run_pipeline(
        input_tables.trips,
        input_tables.persons,
        input_tables.households,
        travel_time_function=travel_time_resolver,
        allow_infeasible_diaries=True,
        n_clusters=10,
        scheduled_transform=impute_return_home,
    )
    paths = _write_artifacts(
        root=root,
        input_tables=input_tables,
        wide_diary_path=wide_diary_path,
        source_report=verify_athens_sources(resolved_source_root),
        outputs=outputs,
        workflow="athens_full",
        description="Full migrated paper artifact workflow using canonical long-form inputs, deterministic strict routing resources, the legacy one-diary routing infeasibility exclusion, 96-bin compound sequences, local optimal matching, and average-linkage clustering.",
    )
    validate_athens_artifacts(paths, expectations=FULL_ARTIFACT_EXPECTATIONS)
    return paths


def validate_athens_artifacts(
    paths: AthensArtifactPaths, *, expectations: AthensArtifactExpectations
) -> AthensArtifactValidation:
    """Validate written paper artifacts against release-relevant stage counts and shapes."""
    checks = [
        _check_path_exists("artifact_root", paths.root),
        *(
            _check_path_exists(name, path)
            for name, path in _named_artifact_paths(paths)
        ),
    ]
    if not all(check.passed for check in checks):
        validation = AthensArtifactValidation(paths.root, tuple(checks))
        validation.raise_if_invalid()
        return validation
    manifest = _read_json_file(paths.manifest)
    input_stage = _read_json_file(paths.input_stage_report)
    source_hashes = _read_json_file(paths.source_hash_report)
    scheduling = _read_json_file(paths.scheduling_diagnostics)
    validation_report = _read_json_file(paths.validation_report)
    state_sequences = np.load(paths.state_sequences)
    compound_sequences = np.load(paths.compound_state_sequences)
    dissimilarity = np.load(paths.dissimilarity_matrix)
    linkage_matrix = np.load(paths.linkage_matrix)
    cluster_labels = pd.read_csv(paths.cluster_labels)
    diary_summary = pd.read_csv(paths.diary_summary)
    scheduled_trips = pd.read_csv(paths.scheduled_trips)
    cluster_time_distribution_frame = pd.read_csv(
        paths.cluster_time_distribution
    )
    complete_demographics = pd.read_csv(paths.complete_demographic_records)
    marginal_demographics = pd.read_csv(paths.marginal_demographics)
    bivariate_demographics = pd.read_csv(paths.bivariate_demographics)
    manifest_artifacts = _json_dict(manifest, "artifacts")
    checks.extend(
        [
            _check_equal(
                "manifest.workflow",
                _json_string(manifest, "workflow"),
                expectations.workflow,
            ),
            _check_equal(
                "manifest.scheduled_diaries",
                _json_int(manifest, "scheduled_diaries"),
                expectations.scheduled_diaries,
            ),
            _check_equal(
                "manifest.sequence_shape",
                _json_int_tuple(manifest, "sequence_shape"),
                expectations.sequence_shape,
            ),
            _check_equal(
                "manifest.cluster_count",
                _json_int(manifest, "cluster_count"),
                expectations.cluster_count,
            ),
            _check_equal(
                "manifest.imputed_return_home_trips",
                _json_int(manifest, "imputed_return_home_trips"),
                expectations.imputed_return_home_trips,
            ),
            _check_equal(
                "input.raw_diaries",
                _json_int(input_stage, "raw_diaries"),
                expectations.raw_diaries,
            ),
            _check_equal(
                "input.canonical_trips",
                _json_int(input_stage, "canonical_trips"),
                expectations.canonical_trips,
            ),
            _check_true(
                "source_hashes.all_sources_match",
                _json_bool(source_hashes, "all_sources_match"),
            ),
            _check_equal(
                "source_hashes.files",
                tuple(sorted(_json_dict(source_hashes, "files"))),
                tuple(sorted(EXPECTED_ATHENS_SOURCE_HASHES)),
            ),
            _check_equal(
                "source_hashes.zip_members",
                tuple(sorted(_json_dict(source_hashes, "zip_members"))),
                tuple(sorted(EXPECTED_ZIP_MEMBER_HASHES)),
            ),
            _check_equal(
                "scheduling.attempted_diaries",
                _json_int(scheduling, "attempted_diaries"),
                expectations.attempted_diaries,
            ),
            _check_equal(
                "scheduling.scheduled_diaries",
                _json_int(scheduling, "scheduled_diaries"),
                expectations.scheduled_diaries,
            ),
            _check_equal(
                "scheduling.infeasible_diaries",
                tuple(_json_string_list(scheduling, "infeasible_diaries")),
                expectations.infeasible_diaries,
            ),
            _check_true(
                "validation.has_errors",
                not _json_bool(validation_report, "has_errors"),
            ),
            _check_equal(
                "state_sequences.shape",
                _array_shape(state_sequences),
                expectations.sequence_shape,
            ),
            _check_equal(
                "compound_state_sequences.shape",
                _array_shape(compound_sequences),
                expectations.sequence_shape,
            ),
            _check_equal(
                "dissimilarity_matrix.shape",
                _array_shape(dissimilarity),
                expectations.dissimilarity_shape,
            ),
            _check_true(
                "dissimilarity_matrix.symmetric",
                bool(np.allclose(dissimilarity, dissimilarity.T)),
            ),
            _check_true(
                "dissimilarity_matrix.diagonal_zero",
                bool(
                    np.allclose(
                        np.diag(dissimilarity), np.zeros(dissimilarity.shape[0])
                    )
                ),
            ),
            _check_equal(
                "linkage_matrix.shape",
                _array_shape(linkage_matrix),
                expectations.linkage_shape,
            ),
            _check_equal(
                "cluster_labels.rows",
                len(cluster_labels),
                expectations.scheduled_diaries,
            ),
            _check_equal(
                "diary_summary.rows",
                len(diary_summary),
                expectations.scheduled_diaries,
            ),
            _check_equal(
                "scheduled_trips.diary_count",
                len(scheduled_trips.groupby(["household_id", "person_id"])),
                expectations.scheduled_diaries,
            ),
            _check_equal(
                "scheduled_trips.imputed_return_home_trips",
                _imputed_return_home_count(scheduled_trips),
                expectations.imputed_return_home_trips,
            ),
            _check_true(
                "scheduled_trips.imputed_return_home_provenance",
                _imputed_return_home_provenance_complete(scheduled_trips),
            ),
            _check_true(
                "cluster_time_distribution.rows",
                len(cluster_time_distribution_frame) > 0,
            ),
            _check_equal(
                "demographics.complete_records",
                len(complete_demographics),
                expectations.complete_demographic_records,
            ),
            _check_true(
                "demographics.marginal_rows",
                expectations.complete_demographic_records == 0
                or len(marginal_demographics) > 0,
            ),
            _check_true(
                "demographics.bivariate_rows",
                expectations.complete_demographic_records == 0
                or len(bivariate_demographics) > 0,
            ),
            _check_equal(
                "manifest.artifact_paths",
                tuple(sorted(manifest_artifacts)),
                tuple(sorted(_expected_manifest_artifact_names())),
            ),
            *_check_manifest_paths(paths, manifest_artifacts),
        ]
    )
    validation = AthensArtifactValidation(paths.root, tuple(checks))
    validation.raise_if_invalid()
    return validation


def _write_artifacts(
    *,
    root: Path,
    input_tables: AthensInputTables,
    wide_diary_path: Path,
    source_report: dict[str, JsonValue],
    outputs: AthensSmokeOutputs,
    workflow: str,
    description: str,
) -> AthensArtifactPaths:
    trips = input_tables.trips
    persons = input_tables.persons
    households = input_tables.households
    paths = _artifact_paths(root)
    trips.to_csv(paths.trips, index=False)
    persons.to_csv(paths.persons, index=False)
    households.to_csv(paths.households, index=False)
    _write_json(paths.source_hash_report, source_report)
    _write_json(
        paths.input_stage_report,
        _input_stage_report_json(input_tables, wide_diary_path),
    )
    _write_json(paths.validation_report, _validation_report_json(outputs))
    _write_json(
        paths.scheduling_diagnostics, _scheduling_diagnostics_json(outputs)
    )
    _scheduled_trips_frame(outputs.scheduled.diaries).to_csv(
        paths.scheduled_trips, index=False
    )
    _diary_summary_frame(outputs.scheduled.diaries).to_csv(
        paths.diary_summary, index=False
    )
    episodes = _episodes_by_diary(outputs.scheduled.diaries)
    _episodes_frame(episodes).to_csv(paths.episodes, index=False)
    state_sequences = tuple(
        state_sequence_from_diary(
            diary,
            initial_activity_state="home",
            travel_state_labeler=athens_travel_state,
        )
        for diary in outputs.scheduled.diaries
    )
    np.save(paths.state_sequences, np.array(state_sequences, dtype=np.str_))
    np.save(
        paths.compound_state_sequences,
        np.array(outputs.sequences, dtype=np.str_),
    )
    _transition_counts_frame(outputs.sequences).to_csv(
        paths.transition_counts, index=False
    )
    _substitution_costs_frame(outputs.sequences).to_csv(
        paths.substitution_costs, index=False
    )
    np.save(paths.dissimilarity_matrix, outputs.dissimilarity_matrix)
    np.save(paths.linkage_matrix, outputs.linkage_matrix)
    _cluster_labels_frame(outputs).to_csv(paths.cluster_labels, index=False)
    outputs.cluster_sizes.to_csv(paths.cluster_summaries, index=False)
    outputs.state_distribution.to_csv(
        paths.cluster_state_distribution, index=False
    )
    temporal_distribution = cluster_time_distribution(
        state_sequences, tuple(int(label) for label in outputs.labels.tolist())
    )
    temporal_distribution.to_csv(paths.cluster_time_distribution, index=False)
    _write_json(paths.dendrogram_layout, _dendrogram_json(outputs))
    write_cut_dendrogram_distribution_svg(
        outputs.linkage_matrix,
        state_sequences,
        paths.dendrogram_figure,
        n_clusters=int(outputs.cluster_sizes.shape[0]),
    )
    demographics = demographic_summary(persons)
    paths.complete_demographic_records.parent.mkdir(parents=True, exist_ok=True)
    demographics.complete_records.to_csv(
        paths.complete_demographic_records, index=False
    )
    demographics.marginal.to_csv(paths.marginal_demographics, index=False)
    demographics.bivariate.to_csv(paths.bivariate_demographics, index=False)
    write_marginal_demographic_svg(
        demographics.marginal, paths.marginal_demographic_figure
    )
    write_bivariate_demographic_svg(
        demographics.bivariate, paths.bivariate_demographic_figure
    )
    _write_json(
        paths.manifest,
        _manifest_json(
            paths, outputs, workflow=workflow, description=description
        ),
    )
    return paths


def main() -> None:
    """Run the full artifact workflow as a directly executed script."""
    paths = write_full_artifacts(Path("examples/athens/output/full"))
    print(f"Wrote full paper artifacts to {paths.root}")


def verify_athens_sources(source_root: Path) -> dict[str, JsonValue]:
    """Verify CSuM2026 PDF, ZIP, and key ZIP member hashes against the method contract."""
    source_root = source_root.resolve()
    source_files: dict[str, JsonValue] = {}
    for filename, expected_hash in EXPECTED_ATHENS_SOURCE_HASHES.items():
        path = source_root / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Required paper source file is missing: {path}"
            )
        actual_hash = _file_sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}."
            )
        source_files[filename] = {
            "path": filename,
            "sha256": actual_hash,
            "expected_sha256": expected_hash,
            "matches": True,
            "size_bytes": path.stat().st_size,
        }
    zip_members = _verify_zip_members(source_root / "CSuM2026.zip")
    return {
        "source_root": str(source_root),
        "all_sources_match": True,
        "files": source_files,
        "zip_members": zip_members,
    }


def _artifact_paths(root: Path) -> AthensArtifactPaths:
    return AthensArtifactPaths(
        root=root,
        trips=root / "data" / "trips.csv",
        persons=root / "data" / "persons.csv",
        households=root / "data" / "households.csv",
        manifest=root / "manifest.json",
        source_hash_report=root / "source_hashes.json",
        input_stage_report=root / "input_stage_report.json",
        validation_report=root / "validation_report.json",
        scheduling_diagnostics=root / "scheduling_diagnostics.json",
        scheduled_trips=root / "scheduled_trips.csv",
        diary_summary=root / "diary_summary.csv",
        episodes=root / "episodes.csv",
        state_sequences=root / "state_sequences.npy",
        compound_state_sequences=root / "compound_state_sequences.npy",
        transition_counts=root / "transition_counts.csv",
        substitution_costs=root / "substitution_costs.csv",
        dissimilarity_matrix=root / "dissimilarity_matrix.npy",
        linkage_matrix=root / "linkage_average.npy",
        cluster_labels=root / "cluster_labels.csv",
        cluster_summaries=root / "cluster_summaries.csv",
        cluster_state_distribution=root / "cluster_state_distribution.csv",
        cluster_time_distribution=root / "cluster_time_distribution.csv",
        dendrogram_layout=root / "dendrogram_layout.json",
        dendrogram_figure=root / "figures" / "dendrogram.svg",
        complete_demographic_records=root
        / "demographics"
        / "complete_records.csv",
        marginal_demographics=root
        / "demographics"
        / "marginal_demographics.csv",
        bivariate_demographics=root
        / "demographics"
        / "bivariate_demographics.csv",
        marginal_demographic_figure=root
        / "figures"
        / "marginal_demographics.svg",
        bivariate_demographic_figure=root
        / "figures"
        / "bivariate_demographics.svg",
    )


def _named_artifact_paths(
    paths: AthensArtifactPaths,
) -> tuple[tuple[str, Path], ...]:
    return (
        ("trips", paths.trips),
        ("persons", paths.persons),
        ("households", paths.households),
        ("manifest", paths.manifest),
        ("source_hash_report", paths.source_hash_report),
        ("input_stage_report", paths.input_stage_report),
        ("validation_report", paths.validation_report),
        ("scheduling_diagnostics", paths.scheduling_diagnostics),
        ("scheduled_trips", paths.scheduled_trips),
        ("diary_summary", paths.diary_summary),
        ("episodes", paths.episodes),
        ("state_sequences", paths.state_sequences),
        ("compound_state_sequences", paths.compound_state_sequences),
        ("transition_counts", paths.transition_counts),
        ("substitution_costs", paths.substitution_costs),
        ("dissimilarity_matrix", paths.dissimilarity_matrix),
        ("linkage_matrix", paths.linkage_matrix),
        ("cluster_labels", paths.cluster_labels),
        ("cluster_summaries", paths.cluster_summaries),
        ("cluster_state_distribution", paths.cluster_state_distribution),
        ("cluster_time_distribution", paths.cluster_time_distribution),
        ("dendrogram_layout", paths.dendrogram_layout),
        ("dendrogram_figure", paths.dendrogram_figure),
        ("complete_demographic_records", paths.complete_demographic_records),
        ("marginal_demographics", paths.marginal_demographics),
        ("bivariate_demographics", paths.bivariate_demographics),
        ("marginal_demographic_figure", paths.marginal_demographic_figure),
        ("bivariate_demographic_figure", paths.bivariate_demographic_figure),
    )


def _expected_manifest_artifact_names() -> tuple[str, ...]:
    return (
        "trips",
        "persons",
        "households",
        "source_hash_report",
        "input_stage_report",
        "validation_report",
        "scheduling_diagnostics",
        "scheduled_trips",
        "diary_summary",
        "episodes",
        "state_sequences",
        "compound_state_sequences",
        "transition_counts",
        "substitution_costs",
        "dissimilarity_matrix",
        "linkage_matrix",
        "cluster_labels",
        "cluster_summaries",
        "cluster_state_distribution",
        "cluster_time_distribution",
        "dendrogram_layout",
        "dendrogram_figure",
        "complete_demographic_records",
        "marginal_demographics",
        "bivariate_demographics",
        "marginal_demographic_figure",
        "bivariate_demographic_figure",
    )


def _check_path_exists(name: str, path: Path) -> AthensArtifactCheck:
    if path.exists():
        return AthensArtifactCheck(name, True, f"`{path}` exists.")
    return AthensArtifactCheck(name, False, f"`{path}` is missing.")


def _check_equal[ValueT](
    name: str, actual: ValueT, expected: ValueT
) -> AthensArtifactCheck:
    if actual == expected:
        return AthensArtifactCheck(
            name, True, f"got expected value {expected!r}."
        )
    return AthensArtifactCheck(
        name, False, f"expected {expected!r}, got {actual!r}."
    )


def _check_true(name: str, condition: bool) -> AthensArtifactCheck:
    if condition:
        return AthensArtifactCheck(name, True, "condition is true.")
    return AthensArtifactCheck(name, False, "condition is false.")


def _check_manifest_paths(
    paths: AthensArtifactPaths, manifest_artifacts: dict[str, JsonValue]
) -> tuple[AthensArtifactCheck, ...]:
    expected_paths = dict(_expected_manifest_paths(paths))
    checks: list[AthensArtifactCheck] = []
    for name, expected_path in sorted(expected_paths.items()):
        actual_value = manifest_artifacts.get(name)
        if not isinstance(actual_value, str):
            checks.append(
                AthensArtifactCheck(
                    f"manifest.artifacts.{name}",
                    False,
                    f"expected relative path string, got {actual_value!r}.",
                )
            )
            continue
        checks.append(
            _check_equal(
                f"manifest.artifacts.{name}",
                actual_value,
                expected_path.relative_to(paths.root).as_posix(),
            )
        )
    return tuple(checks)


def _expected_manifest_paths(
    paths: AthensArtifactPaths,
) -> tuple[tuple[str, Path], ...]:
    return tuple(
        (name, path)
        for name, path in _named_artifact_paths(paths)
        if name != "manifest"
    )


def _read_json_file(path: Path) -> dict[str, JsonValue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"`{path}` must contain a JSON object.")
    result: dict[str, JsonValue] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError(f"`{path}` contains a non-string JSON object key.")
        result[key] = _json_value(value)
    return result


def _json_value(value: JsonValue) -> JsonValue:
    return value


def _json_dict(data: dict[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = data[key]
    if not isinstance(value, dict):
        raise ValueError(f"JSON key `{key}` must contain an object.")
    result: dict[str, JsonValue] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str):
            raise ValueError(
                f"JSON key `{key}` contains a non-string nested key."
            )
        result[nested_key] = nested_value
    return result


def _json_string(data: dict[str, JsonValue], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise ValueError(f"JSON key `{key}` must contain a string.")
    return value


def _json_int(data: dict[str, JsonValue], key: str) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"JSON key `{key}` must contain an integer.")
    return value


def _json_bool(data: dict[str, JsonValue], key: str) -> bool:
    value = data[key]
    if not isinstance(value, bool):
        raise ValueError(f"JSON key `{key}` must contain a boolean.")
    return value


def _json_int_tuple(data: dict[str, JsonValue], key: str) -> tuple[int, ...]:
    value = data[key]
    if not isinstance(value, list):
        raise ValueError(f"JSON key `{key}` must contain a list of integers.")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError(f"JSON key `{key}` must contain only integers.")
        result.append(item)
    return tuple(result)


def _json_string_list(data: dict[str, JsonValue], key: str) -> tuple[str, ...]:
    value = data[key]
    if not isinstance(value, list):
        raise ValueError(f"JSON key `{key}` must contain a list of strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"JSON key `{key}` must contain only strings.")
        result.append(item)
    return tuple(result)


def _array_shape(
    array: np.ndarray[tuple[int, ...], np.dtype[np.generic]],
) -> tuple[int, ...]:
    return tuple(int(size) for size in array.shape)


def _validation_report_json(
    outputs: AthensSmokeOutputs,
) -> dict[str, JsonValue]:
    report = outputs.validation_report
    return {
        "summary": report.summary,
        "has_errors": report.has_errors,
        "has_warnings": report.has_warnings,
        "errors": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "table": issue.table,
                "message": issue.message,
                "row_identifier": issue.row_identifier,
                "column": issue.column,
                "bad_value": issue.bad_value,
            }
            for issue in report.errors
        ],
        "warnings": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "table": issue.table,
                "message": issue.message,
                "row_identifier": issue.row_identifier,
                "column": issue.column,
                "bad_value": issue.bad_value,
            }
            for issue in report.warnings
        ],
        "invalid_rows": list(report.invalid_rows),
        "invalid_chains": list(report.invalid_chains),
    }


def _scheduling_diagnostics_json(
    outputs: AthensSmokeOutputs,
) -> dict[str, JsonValue]:
    diagnostics = outputs.scheduled.diagnostics
    return {
        "attempted_diaries": diagnostics.attempted_diaries,
        "scheduled_diaries": diagnostics.scheduled_diaries,
        "infeasible_diaries": list(diagnostics.infeasible_diaries),
        "has_errors": diagnostics.has_errors,
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "household_id": issue.household_id,
                "person_id": issue.person_id,
                "trip_id": issue.trip_id,
            }
            for issue in diagnostics.issues
        ],
    }


def _scheduled_trips_frame(diaries: tuple[Diary, ...]) -> pd.DataFrame:
    rows: list[dict[str, str | int | bool | None]] = []
    for diary in diaries:
        for position, trip in enumerate(diary.trips, start=1):
            is_imputed_return_home = bool(
                trip.metadata.get("is_imputed_return_home", False)
            )
            rows.append(
                {
                    "household_id": trip.household_id,
                    "person_id": trip.person_id,
                    "trip_id": trip.trip_id,
                    "trip_sequence": position,
                    "origin": trip.origin,
                    "destination": trip.destination,
                    "purpose": trip.purpose,
                    "mode": trip.mode,
                    "departure_second": trip.departure_second,
                    "arrival_second": trip.arrival_second,
                    "travel_time_seconds": trip.travel_time_seconds,
                    "is_imputed_return_home": is_imputed_return_home,
                    "imputation_method": _string_metadata_value(
                        trip.metadata.get("imputation_method")
                    )
                    if is_imputed_return_home
                    else None,
                    "observed_last_trip_id": _string_metadata_value(
                        trip.metadata.get("observed_last_trip_id")
                    )
                    if is_imputed_return_home
                    else None,
                }
            )
    return pd.DataFrame(rows)


def _string_metadata_value(value: MetadataValue) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _imputed_return_home_count(scheduled_trips: pd.DataFrame) -> int:
    if "is_imputed_return_home" not in scheduled_trips.columns:
        return 0
    return int(scheduled_trips["is_imputed_return_home"].fillna(False).sum())


def _imputed_return_home_provenance_complete(
    scheduled_trips: pd.DataFrame,
) -> bool:
    required_columns = {
        "is_imputed_return_home",
        "imputation_method",
        "observed_last_trip_id",
    }
    if not required_columns <= set(scheduled_trips.columns):
        return False
    imputed_rows = scheduled_trips[
        scheduled_trips["is_imputed_return_home"].fillna(False)
    ]
    if imputed_rows.empty:
        return True
    return bool(
        imputed_rows["imputation_method"].notna().all()
        and imputed_rows["observed_last_trip_id"].notna().all()
    )


def _diary_summary_frame(diaries: tuple[Diary, ...]) -> pd.DataFrame:
    rows: list[dict[str, str | int]] = []
    for diary in diaries:
        rows.append(
            {
                "household_id": diary.household_id,
                "person_id": diary.person_id,
                "n_trips": len(diary.trips),
                "first_departure_second": _first_departure_second(diary),
                "last_arrival_second": _last_arrival_second(diary),
            }
        )
    return pd.DataFrame(rows)


def _episodes_by_diary(
    diaries: tuple[Diary, ...],
) -> tuple[tuple[str, str, tuple[Episode, ...]], ...]:
    return tuple(
        (
            diary.household_id,
            diary.person_id,
            episodes_from_diary(
                diary,
                initial_activity_state="home",
                travel_state_labeler=athens_travel_state,
            ),
        )
        for diary in diaries
    )


def _episodes_frame(
    episodes_by_diary: tuple[tuple[str, str, tuple[Episode, ...]], ...],
) -> pd.DataFrame:
    rows: list[dict[str, str | int]] = []
    for household_id, person_id, episodes in episodes_by_diary:
        for position, episode in enumerate(episodes, start=1):
            rows.append(
                {
                    "household_id": household_id,
                    "person_id": person_id,
                    "episode_sequence": position,
                    "state": episode.state,
                    "start_second": episode.start_second,
                    "end_second": episode.end_second,
                }
            )
    return pd.DataFrame(rows)


def _transition_counts_frame(
    sequences: tuple[tuple[str, ...], ...],
) -> pd.DataFrame:
    counts = transition_counts(sequences)
    return pd.DataFrame(
        [
            {"source": source, "target": target, "count": count}
            for (source, target), count in sorted(counts.items())
        ],
        columns=["source", "target", "count"],
    )


def _substitution_costs_frame(
    sequences: tuple[tuple[str, ...], ...],
) -> pd.DataFrame:
    costs = substitution_costs(sequences)
    return pd.DataFrame(
        [
            {"source": source, "target": target, "cost": cost}
            for (source, target), cost in sorted(costs.items())
        ],
        columns=["source", "target", "cost"],
    )


def _cluster_labels_frame(outputs: AthensSmokeOutputs) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "household_id": diary.household_id,
                "person_id": diary.person_id,
                "cluster": int(label),
            }
            for diary, label in zip(
                outputs.scheduled.diaries, outputs.labels.tolist(), strict=True
            )
        ],
        columns=["household_id", "person_id", "cluster"],
    )


def _dendrogram_json(outputs: AthensSmokeOutputs) -> dict[str, JsonValue]:
    layout = outputs.dendrogram
    return {
        "branch_x": [list(values) for values in layout.branch_x],
        "branch_y": [list(values) for values in layout.branch_y],
        "leaf_indices": list(layout.leaf_indices),
        "leaf_labels": list(layout.leaf_labels),
        "branch_colors": list(layout.branch_colors),
        "leaf_colors": list(layout.leaf_colors),
    }


def _manifest_json(
    paths: AthensArtifactPaths,
    outputs: AthensSmokeOutputs,
    *,
    workflow: str,
    description: str,
) -> dict[str, JsonValue]:
    return {
        "workflow": workflow,
        "description": description,
        "scheduled_diaries": outputs.scheduled.diagnostics.scheduled_diaries,
        "sequence_shape": [len(outputs.sequences), len(outputs.sequences[0])],
        "cluster_count": int(outputs.cluster_sizes.shape[0]),
        "imputed_return_home_trips": _imputed_return_home_count(
            _scheduled_trips_frame(outputs.scheduled.diaries)
        ),
        "artifacts": {
            "trips": _relative_artifact_path(paths.root, paths.trips),
            "persons": _relative_artifact_path(paths.root, paths.persons),
            "households": _relative_artifact_path(paths.root, paths.households),
            "source_hash_report": _relative_artifact_path(
                paths.root, paths.source_hash_report
            ),
            "input_stage_report": _relative_artifact_path(
                paths.root, paths.input_stage_report
            ),
            "validation_report": _relative_artifact_path(
                paths.root, paths.validation_report
            ),
            "scheduling_diagnostics": _relative_artifact_path(
                paths.root, paths.scheduling_diagnostics
            ),
            "scheduled_trips": _relative_artifact_path(
                paths.root, paths.scheduled_trips
            ),
            "diary_summary": _relative_artifact_path(
                paths.root, paths.diary_summary
            ),
            "episodes": _relative_artifact_path(paths.root, paths.episodes),
            "state_sequences": _relative_artifact_path(
                paths.root, paths.state_sequences
            ),
            "compound_state_sequences": _relative_artifact_path(
                paths.root, paths.compound_state_sequences
            ),
            "transition_counts": _relative_artifact_path(
                paths.root, paths.transition_counts
            ),
            "substitution_costs": _relative_artifact_path(
                paths.root, paths.substitution_costs
            ),
            "dissimilarity_matrix": _relative_artifact_path(
                paths.root, paths.dissimilarity_matrix
            ),
            "linkage_matrix": _relative_artifact_path(
                paths.root, paths.linkage_matrix
            ),
            "cluster_labels": _relative_artifact_path(
                paths.root, paths.cluster_labels
            ),
            "cluster_summaries": _relative_artifact_path(
                paths.root, paths.cluster_summaries
            ),
            "cluster_state_distribution": _relative_artifact_path(
                paths.root, paths.cluster_state_distribution
            ),
            "cluster_time_distribution": _relative_artifact_path(
                paths.root, paths.cluster_time_distribution
            ),
            "dendrogram_layout": _relative_artifact_path(
                paths.root, paths.dendrogram_layout
            ),
            "dendrogram_figure": _relative_artifact_path(
                paths.root, paths.dendrogram_figure
            ),
            "complete_demographic_records": _relative_artifact_path(
                paths.root, paths.complete_demographic_records
            ),
            "marginal_demographics": _relative_artifact_path(
                paths.root, paths.marginal_demographics
            ),
            "bivariate_demographics": _relative_artifact_path(
                paths.root, paths.bivariate_demographics
            ),
            "marginal_demographic_figure": _relative_artifact_path(
                paths.root, paths.marginal_demographic_figure
            ),
            "bivariate_demographic_figure": _relative_artifact_path(
                paths.root, paths.bivariate_demographic_figure
            ),
        },
    }


def _input_stage_report_json(
    input_tables: AthensInputTables, wide_diary_path: Path
) -> dict[str, JsonValue]:
    note = (
        "The checked-in wide diary fixture has the paper source schema but only three diaries; it is not the full 513-diary CSuM2026 input."
        if input_tables.raw_diaries < 513
        else "The migrated wide diary source contains the 513 raw diaries used by the canonical full-paper workflow."
    )
    return {
        "wide_diary_path": str(wide_diary_path),
        "raw_diaries": input_tables.raw_diaries,
        "canonical_trips": input_tables.canonical_trips,
        "canonical_persons": len(input_tables.persons),
        "canonical_households": len(input_tables.households),
        "note": note,
    }


def _first_departure_second(diary: Diary) -> int:
    first_trip = diary.trips[0]
    if first_trip.departure_second is None:
        raise RuntimeError(
            f"Diary {diary.household_id}:{diary.person_id} is not scheduled."
        )
    return first_trip.departure_second


def _last_arrival_second(diary: Diary) -> int:
    last_trip = diary.trips[-1]
    if last_trip.arrival_second is None:
        raise RuntimeError(
            f"Diary {diary.household_id}:{diary.person_id} is not scheduled."
        )
    return last_trip.arrival_second


def _relative_artifact_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _verify_zip_members(zip_path: Path) -> dict[str, JsonValue]:
    members: dict[str, JsonValue] = {}
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        for member_name, expected_hash in EXPECTED_ZIP_MEMBER_HASHES.items():
            if member_name not in names:
                raise FileNotFoundError(
                    f"Required paper source member is missing from {zip_path.name}: {member_name}"
                )
            data = archive.read(member_name)
            actual_hash = sha256(data).hexdigest().upper()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch for {member_name} inside {zip_path.name}: expected {expected_hash}, got {actual_hash}."
                )
            members[member_name] = {
                "path": member_name,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "matches": True,
                "size_bytes": len(data),
            }
    return members


def _write_json(path: Path, data: dict[str, JsonValue]) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
