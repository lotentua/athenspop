"""Write canonical paper-pipeline artifacts to disk."""

from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Final, cast
from zipfile import ZipFile

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cophenet, linkage
from scipy.spatial.distance import squareform

from athenspop import validate_dataframes
from athenspop.clustering import (
    CutDendrogramNode,
    LinkageMatrix,
    average_linkage,
    cluster_state_distribution,
    cut_dendrogram_tree,
    flat_cluster_labels,
    leaf_order,
)
from athenspop.model import Diary
from athenspop.scheduling import ScheduledSurveyDataset
from athenspop.sequence import (
    Episode,
    discretize_episodes,
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
    athens_dissimilarity_matrix,
    athens_travel_state,
    compound_period_sequence,
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

PAPER_RESULT_REFERENCE_PATH: Final[Path] = (
    Path(__file__).resolve().with_name("paper_result_reference.json")
)

EXPECTED_ATHENS_SOURCE_HASHES: Final[dict[str, str]] = {
    "CSuM2026.zip": "2EA15A9D1448FB29CFCDE5DA0C2BD3D515D52442EE558E41841138644A297841",
    "CSuM2026.pdf": "5BC2AA37934F458B1E56BF8581F0A7FE7A156535AF59BD3FF98A0ED27BFACEE1",
}
EXPECTED_ATHENS_INPUT_HASHES: Final[dict[str, str]] = {
    "examples/athens/data/raw_diaries_athens_wide.csv": (
        "231B9F2DFCB11B0A34BBD8869CED79E11D65BA09AF887E0EDA623C57318A54F5"
    ),
    "examples/athens/data/travel_time/routing.npz": (
        "AD0D374DDC65E9ADE0EDE53041534041D8305FE06FCFA839AF7815082DACC5DC"
    ),
    "examples/athens/data/travel_time/zone_encoder.json": (
        "AED03BAC02F1FD0D56CEE0A8CA4589AABEBFC08CF336A3F98D047E5656949873"
    ),
}
EXPECTED_ZIP_MEMBER_HASHES: Final[dict[str, str]] = {
    "main.tex": "0C88CC332459B59FD0977B4D6C961547D32BA1DF6D240B53D54354D9B32161AE",
    "methods.tex": "59F7A9F030124BBB49A0D6545130AC852B84E742DD0683DA56CF6AB76A0CECC0",
    "results.tex": "58C80CF04493FB2F21F7E3998C3C05CA0CC6A5A3E7A5D7937E02CA4913ABDE8B",
    "intro.tex": "7E86656D9DF6FB5D96888D8953DD818F970CFC81CBD2C91EDAEB61097B519792",
    "conclusion.tex": (
        "AF1C6C3D81001426071475C9E772475DE9C1AFA13425A6C53591C1543B8808C8"
    ),
    "CSuM2026.bib": "959845FCF78B5AC45DD714DF981C98B04479751B49AADD4B19B20E4128A2737B",
    "figures/MarginalDistributions.pgf": (
        "395E505044F8C84E81C816E97061C883303BB17B0A1327C3EB341CCB17594AC8"
    ),
    "figures/BivariateDistributions.pgf": (
        "1AF15D42D8CFB96536F6FBE06D81A34E01F308341E779BAB66653B929883E5AE"
    ),
    "figures/Dendrogram.pdf": (
        "499D74210B23307725DF8BE07F6EB636DB6A29FDFEBDE79885D6883E6666EDA1"
    ),
    "figures/Dendrogram.pgf": (
        "44C5211D0B2DE43E35B6AF8BE08CF505EDDD473CC0F9EB2B2C947EC82BA5D0B0"
    ),
    "figures/Dendrogram.eps": (
        "272246A30AFA93D8F11DB8DE0487A9338535FE0A3EF0A4A1962E09D86E319BF3"
    ),
}


@dataclass(frozen=True, slots=True)
class AthensArtifactPaths:
    """Named artifact paths written by an Athens reanalysis workflow."""

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
    linkage_method_comparison: Path
    cluster_labels: Path
    cluster_summaries: Path
    cluster_state_distribution: Path
    cluster_time_distribution: Path
    dendrogram_layout: Path
    dendrogram_figure: Path
    complete_demographic_records: Path
    marginal_demographics: Path
    demographic_associations: Path
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
            details = "; ".join(f"{check.name}: {check.message}" for check in failures)
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
REANALYSIS_ARTIFACT_EXPECTATIONS: Final[AthensArtifactExpectations] = (
    AthensArtifactExpectations(
        workflow="athens_migrated_reanalysis",
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
FULL_ARTIFACT_EXPECTATIONS: Final[AthensArtifactExpectations] = (
    REANALYSIS_ARTIFACT_EXPECTATIONS
)


def write_smoke_artifacts(
    output_root: Path,
    *,
    source_root: Path | None = None,
    wide_diary_path: Path | None = None,
) -> AthensArtifactPaths:
    "Run the canonical smoke workflow and write named artifacts under `output_root`."
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
        description=(
            "Tiny deterministic artifact-writing workflow for fast tests and "
            "documentation smoke checks."
        ),
    )
    validate_athens_artifacts(paths, expectations=SMOKE_ARTIFACT_EXPECTATIONS)
    return paths


def write_reanalysis_artifacts(
    output_root: Path,
    *,
    source_root: Path | None = None,
    wide_diary_path: Path = DEFAULT_ATHENS_WIDE_DIARY_PATH,
) -> AthensArtifactPaths:
    """Run the migrated 513-diary reanalysis and write artifacts under `output_root`."""
    root = output_root.resolve()
    resolved_source_root = Path.cwd() if source_root is None else source_root
    resolved_wide_diary_path = wide_diary_path.resolve()
    source_report = verify_athens_sources(
        resolved_source_root, wide_diary_path=resolved_wide_diary_path
    )
    root.mkdir(parents=True, exist_ok=True)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    input_tables = load_athens_wide_diaries(
        resolved_wide_diary_path, fixture_travel_time_seconds=None
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
        wide_diary_path=resolved_wide_diary_path,
        source_report=source_report,
        outputs=outputs,
        workflow="athens_migrated_reanalysis",
        description=(
            "Migrated reanalysis using canonical long-form inputs, deterministic "
            "routing resources, a one-diary missing-routing-data exclusion, 96-bin "
            "compound sequences, local optimal matching, and average-linkage "
            "clustering. This is not an end-to-end reproduction of the archived "
            "paper result."
        ),
    )
    validate_athens_artifacts(paths, expectations=REANALYSIS_ARTIFACT_EXPECTATIONS)
    return paths


def write_full_artifacts(
    output_root: Path,
    *,
    source_root: Path | None = None,
    wide_diary_path: Path = DEFAULT_ATHENS_WIDE_DIARY_PATH,
) -> AthensArtifactPaths:
    """Preserve the former entry point for the now-labeled migrated reanalysis."""
    return write_reanalysis_artifacts(
        output_root,
        source_root=source_root,
        wide_diary_path=wide_diary_path,
    )


def validate_athens_artifacts(
    paths: AthensArtifactPaths, *, expectations: AthensArtifactExpectations
) -> AthensArtifactValidation:
    "Validate written paper artifacts against release-relevant stage counts and shapes."
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
    linkage_method_comparison = pd.read_csv(paths.linkage_method_comparison)
    cluster_labels = pd.read_csv(paths.cluster_labels)
    cluster_summaries = pd.read_csv(paths.cluster_summaries)
    cluster_state_distribution_frame = pd.read_csv(paths.cluster_state_distribution)
    diary_summary = pd.read_csv(paths.diary_summary)
    scheduled_trips = pd.read_csv(paths.scheduled_trips)
    episodes_frame = pd.read_csv(paths.episodes)
    transition_counts_frame = pd.read_csv(paths.transition_counts)
    substitution_costs_frame = pd.read_csv(paths.substitution_costs)
    cluster_time_distribution_frame = pd.read_csv(paths.cluster_time_distribution)
    complete_demographics = pd.read_csv(paths.complete_demographic_records)
    marginal_demographics = pd.read_csv(paths.marginal_demographics)
    demographic_associations = pd.read_csv(paths.demographic_associations)
    bivariate_demographics = pd.read_csv(paths.bivariate_demographics)
    dendrogram = _read_json_file(paths.dendrogram_layout)
    manifest_artifacts = _json_dict(manifest, "artifacts")
    manifest_hashes = _json_dict(manifest, "artifact_sha256")
    manifest_method = _json_dict(manifest, "method")
    manifest_randomness = _json_dict(manifest, "randomness")
    imputation_randomness = _json_dict(manifest_randomness, "return_home_imputation")
    trips = pd.read_csv(paths.trips)
    persons = pd.read_csv(paths.persons)
    households = pd.read_csv(paths.households)
    expected_demographics = demographic_summary(persons)
    episode_sequences = _state_sequences_from_episodes(episodes_frame, diary_summary)
    raw_sequences = tuple(tuple(row) for row in state_sequences.tolist())
    reduced_sequences = tuple(tuple(row) for row in compound_sequences.tolist())
    expected_compound_sequences = tuple(
        compound_period_sequence(sequence) for sequence in raw_sequences
    )
    expected_dissimilarity = athens_dissimilarity_matrix(reduced_sequences)
    expected_linkage = average_linkage(dissimilarity, optimal_ordering=True)
    labels = tuple(int(value) for value in cluster_labels["cluster"].tolist())
    checks.extend(
        [
            _check_equal(
                "manifest.workflow",
                _json_string(manifest, "workflow"),
                expectations.workflow,
            ),
            _check_equal(
                "manifest.claim_status",
                _json_string(manifest, "claim_status"),
                (
                    "smoke_test"
                    if expectations.workflow == "athens_smoke"
                    else "migrated_reanalysis_not_end_to_end_reproduction"
                ),
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
                "manifest.method.routing_fallback",
                _json_dict(manifest_method, "routing_fallback"),
                _routing_fallback_report(scheduled_trips, expectations.workflow),
            ),
            _check_equal(
                "manifest.method.contract",
                {
                    key: value
                    for key, value in manifest_method.items()
                    if key != "routing_fallback"
                },
                _expected_manifest_method(expectations.workflow),
            ),
            _check_equal(
                "manifest.randomness.scheduling",
                _json_dict(manifest_randomness, "scheduling"),
                {
                    "library": "python.random",
                    "generator": "Random (MT19937)",
                    "seed": 2026,
                    "stream": "one stream shared across diaries in canonical order",
                    "sampling": "uniform over each refined departure interval",
                },
            ),
            _check_equal(
                "manifest.randomness.return_home_imputation.contract",
                {
                    key: value
                    for key, value in imputation_randomness.items()
                    if key != "horizon"
                },
                {
                    "library": "python.random",
                    "generator": "Random (MT19937)",
                    "seed": 2026,
                    "stream": "separate stream shared across eligible diaries",
                    "sampling": (
                        "purpose-stratified inverse empirical activity duration"
                    ),
                },
            ),
            _check_equal(
                "manifest.randomness.return_home_imputation.horizon",
                _json_dict(imputation_randomness, "horizon"),
                _imputation_horizon_report(scheduled_trips),
            ),
            _check_equal(
                "manifest.artifact_sha256.names",
                tuple(sorted(manifest_hashes)),
                tuple(
                    sorted(
                        name
                        for name, _ in _named_artifact_paths(paths)
                        if name != "manifest"
                    )
                ),
            ),
            *_check_artifact_hashes(paths, manifest_hashes),
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
            _check_equal(
                "input.canonical_persons",
                _json_int(input_stage, "canonical_persons"),
                expectations.raw_diaries,
            ),
            _check_equal(
                "input.canonical_households",
                _json_int(input_stage, "canonical_households"),
                expectations.raw_diaries,
            ),
            _check_equal("data.trips.rows", len(trips), expectations.canonical_trips),
            _check_equal("data.persons.rows", len(persons), expectations.raw_diaries),
            _check_equal(
                "data.households.rows", len(households), expectations.raw_diaries
            ),
            _check_true(
                "data.canonical_keys_joinable",
                _canonical_keys_joinable(trips, persons, households),
            ),
            _check_true(
                "data.canonical_table_contract",
                _canonical_tables_are_valid(trips, persons, households),
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
                "source_hashes.inputs",
                tuple(sorted(_json_dict(source_hashes, "inputs"))),
                tuple(sorted(EXPECTED_ATHENS_INPUT_HASHES)),
            ),
            *_source_hash_contract_checks(source_hashes),
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
            _check_true(
                "diary_summary.from_scheduled_trips",
                _diary_summary_matches_scheduled_trips(diary_summary, scheduled_trips),
            ),
            _check_true(
                "episodes.partition_and_diary_order",
                episode_sequences is not None,
            ),
            _check_equal(
                "state_sequences.from_episodes",
                episode_sequences,
                raw_sequences,
            ),
            _check_equal(
                "compound_state_sequences.from_state_sequences",
                reduced_sequences,
                expected_compound_sequences,
            ),
            _check_true(
                "transition_counts.from_compound_state_sequences",
                _frames_match(
                    transition_counts_frame,
                    _transition_counts_frame(reduced_sequences),
                ),
            ),
            _check_true(
                "substitution_costs.from_compound_state_sequences",
                _frames_match(
                    substitution_costs_frame,
                    _substitution_costs_frame(reduced_sequences),
                ),
            ),
            _check_equal(
                "dissimilarity_matrix.shape",
                _array_shape(dissimilarity),
                expectations.dissimilarity_shape,
            ),
            _check_true(
                "dissimilarity_matrix.symmetric",
                bool(
                    np.allclose(
                        dissimilarity,
                        dissimilarity.T,
                        rtol=0.0,
                        atol=1e-12,
                    )
                ),
            ),
            _check_true(
                "dissimilarity_matrix.finite_nonnegative",
                bool(np.isfinite(dissimilarity).all() and np.all(dissimilarity >= 0)),
            ),
            _check_true(
                "dissimilarity_matrix.diagonal_zero",
                bool(
                    np.allclose(
                        np.diag(dissimilarity),
                        np.zeros(dissimilarity.shape[0]),
                        rtol=0.0,
                        atol=1e-12,
                    )
                ),
            ),
            _check_true(
                "dissimilarity_matrix.from_compound_state_sequences",
                bool(
                    np.allclose(
                        dissimilarity,
                        expected_dissimilarity,
                        rtol=0.0,
                        atol=1e-12,
                    )
                ),
            ),
            _check_equal(
                "linkage_matrix.shape",
                _array_shape(linkage_matrix),
                expectations.linkage_shape,
            ),
            _check_true(
                "linkage_matrix.from_dissimilarity_matrix",
                bool(
                    np.allclose(
                        linkage_matrix,
                        expected_linkage,
                        rtol=0.0,
                        atol=1e-12,
                    )
                ),
            ),
            _check_true(
                "linkage_method_comparison.from_dissimilarity_matrix",
                _frames_match(
                    linkage_method_comparison,
                    _linkage_method_comparison(dissimilarity),
                ),
            ),
            _check_true(
                "linkage_method_comparison.average_is_highest",
                expectations.workflow != "athens_migrated_reanalysis"
                or _average_linkage_is_best(linkage_method_comparison),
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
                "cluster_labels.ordered_diary_keys",
                _observation_keys_sha256(cluster_labels),
                _observation_keys_sha256(diary_summary),
            ),
            _check_true(
                "cluster_labels.canonical_cut_partition",
                bool(
                    np.array_equal(
                        cluster_labels["cluster"].to_numpy(dtype=np.int64),
                        flat_cluster_labels(
                            linkage_matrix,
                            n_clusters=expectations.cluster_count,
                        ),
                    )
                ),
            ),
            _check_equal(
                "cluster_labels.identifiers",
                tuple(sorted(cluster_labels["cluster"].unique().tolist())),
                tuple(range(1, expectations.cluster_count + 1)),
            ),
            _check_true(
                "cluster_summaries.match_labels",
                _cluster_summaries_match_labels(
                    cluster_summaries,
                    cluster_labels,
                    expectations.scheduled_diaries,
                ),
            ),
            _check_true(
                "cluster_state_distribution.from_sequences_and_labels",
                _frames_match(
                    cluster_state_distribution_frame,
                    cluster_state_distribution(reduced_sequences, labels),
                ),
            ),
            _check_true(
                "cluster_time_distribution.from_sequences_and_labels",
                _frames_match(
                    cluster_time_distribution_frame,
                    cluster_time_distribution(raw_sequences, labels),
                ),
            ),
            _check_equal(
                "cluster_state_distribution.identifiers",
                tuple(
                    sorted(
                        cluster_state_distribution_frame["cluster"].unique().tolist()
                    )
                ),
                tuple(range(1, expectations.cluster_count + 1)),
            ),
            _check_equal(
                "cluster_time_distribution.identifiers",
                tuple(
                    sorted(cluster_time_distribution_frame["cluster"].unique().tolist())
                ),
                tuple(range(1, expectations.cluster_count + 1)),
            ),
            _check_true(
                "dendrogram.ordered_observations",
                _dendrogram_matches_diaries(dendrogram, diary_summary, linkage_matrix),
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
                "scheduled_trips.concrete_positive_integer_timing",
                _scheduled_trip_timing_is_valid(scheduled_trips),
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
                "demographics.complete_records_from_persons",
                _frames_match(
                    complete_demographics,
                    expected_demographics.complete_records,
                ),
            ),
            _check_true(
                "demographics.marginals_from_persons",
                _frames_match(marginal_demographics, expected_demographics.marginal),
            ),
            _check_true(
                "demographics.associations_from_persons",
                _frames_match(
                    demographic_associations,
                    expected_demographics.associations,
                ),
            ),
            _check_true(
                "demographics.bivariate_from_persons",
                _frames_match(bivariate_demographics, expected_demographics.bivariate),
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
            _check_true(
                "demographics.paper_associations",
                expectations.complete_demographic_records == 0
                or _demographic_associations_match_reference(demographic_associations),
            ),
            _check_equal(
                "demographics.association_pair_count",
                len(demographic_associations),
                15,
            ),
            _check_true(
                "state_sequences.paper_alphabet",
                expectations.workflow != "athens_migrated_reanalysis"
                or set(np.unique(state_sequences).tolist())
                == _expected_unreduced_states(),
            ),
            _check_true(
                "compound_state_sequences.paper_alphabet",
                expectations.workflow != "athens_migrated_reanalysis"
                or set(np.unique(compound_sequences).tolist())
                == _expected_compound_states(),
            ),
            _check_equal(
                "manifest.artifact_paths",
                tuple(sorted(manifest_artifacts)),
                tuple(
                    sorted(
                        name
                        for name, _ in _named_artifact_paths(paths)
                        if name != "manifest"
                    )
                ),
            ),
            *_check_manifest_paths(paths, manifest_artifacts),
        ]
    )
    validation = AthensArtifactValidation(paths.root, tuple(checks))
    validation.raise_if_invalid()
    return validation


def validate_paper_result_reference(
    state_sequences_path: Path,
    dissimilarity_matrix_path: Path,
    diary_summary_path: Path,
    *,
    demographic_associations_path: Path | None = None,
) -> AthensArtifactValidation:
    """Compare candidate numerical artifacts with the archived paper result.

    This validates result identity. It does not establish that the current workflow
    generated the archived result unless the candidate paths came from that workflow.
    """
    reference = _read_json_file(PAPER_RESULT_REFERENCE_PATH)
    sequence_reference = _json_dict(reference, "state_sequences")
    distance_reference = _json_dict(reference, "dissimilarity_matrix")
    observation_reference = _json_dict(reference, "observation_keys")
    clustering_reference = _json_dict(reference, "clustering")
    expected_clusters = _json_dict_list(clustering_reference, "displayed_clusters")
    state_sequences = np.load(state_sequences_path, allow_pickle=False)
    dissimilarity = np.load(dissimilarity_matrix_path, allow_pickle=False)
    diary_summary = pd.read_csv(diary_summary_path)
    identity_checks = (
        _check_equal(
            "paper_reference.state_sequences.file_sha256",
            _file_sha256(state_sequences_path),
            _json_string(sequence_reference, "file_sha256"),
        ),
        _check_equal(
            "paper_reference.state_sequences.shape",
            _array_shape(state_sequences),
            _json_int_tuple(sequence_reference, "shape"),
        ),
        _check_equal(
            "paper_reference.dissimilarity_matrix.file_sha256",
            _file_sha256(dissimilarity_matrix_path),
            _json_string(distance_reference, "file_sha256"),
        ),
        _check_equal(
            "paper_reference.dissimilarity_matrix.shape",
            _array_shape(dissimilarity),
            _json_int_tuple(distance_reference, "shape"),
        ),
        _check_equal(
            "paper_reference.observation_keys.count",
            len(diary_summary),
            _json_int(observation_reference, "count"),
        ),
        _check_equal(
            "paper_reference.observation_keys.sha256",
            _observation_keys_sha256(diary_summary),
            _json_string(observation_reference, "sha256"),
        ),
        *(
            (
                _check_true(
                    "paper_reference.demographics.associations",
                    _demographic_associations_match_reference(
                        pd.read_csv(demographic_associations_path)
                    ),
                ),
            )
            if demographic_associations_path is not None
            else ()
        ),
    )
    if not all(check.passed for check in identity_checks):
        return AthensArtifactValidation(state_sequences_path.parent, identity_checks)
    maximum = float(np.max(dissimilarity))
    maximum_check = _check_true(
        "paper_reference.dissimilarity_matrix.maximum",
        bool(
            np.isclose(
                maximum,
                _json_float(distance_reference, "maximum"),
                rtol=0.0,
                atol=1e-12,
            )
        ),
    )
    if not maximum_check.passed:
        return AthensArtifactValidation(
            state_sequences_path.parent,
            (*identity_checks, maximum_check),
        )
    normalized = dissimilarity / maximum
    linkage_matrix = average_linkage(normalized, optimal_ordering=True)
    leaves = sorted(
        _cut_leaves(cut_dendrogram_tree(linkage_matrix, n_clusters=10)),
        key=lambda node: node.leaf_label or 0,
    )
    actual_cluster_sizes = tuple(len(node.members) for node in leaves)
    expected_cluster_sizes = tuple(
        _json_int(cluster, "size") for cluster in expected_clusters
    )
    actual_cluster_heights = tuple(node.normalized_height for node in leaves)
    expected_cluster_heights = tuple(
        _json_float(cluster, "normalized_height") for cluster in expected_clusters
    )
    actual_member_hashes = tuple(
        _member_indices_sha256(node.members) for node in leaves
    )
    expected_member_hashes = tuple(
        _json_string(cluster, "members_sha256") for cluster in expected_clusters
    )
    semantic_checks = (
        _check_true(
            "paper_reference.clustering.cophenetic_correlations",
            _linkage_correlations_match_reference(
                _linkage_method_comparison(dissimilarity),
                _json_dict(
                    clustering_reference,
                    "candidate_cophenetic_correlations_without_optimal_ordering",
                ),
            ),
        ),
        _check_true(
            "paper_reference.clustering.linkage_sha256",
            sha256(np.asarray(linkage_matrix, dtype="<f8").tobytes())
            .hexdigest()
            .upper()
            == _json_string(
                clustering_reference,
                "normalized_linkage_little_endian_float64_sha256",
            ),
        ),
        _check_equal(
            "paper_reference.clustering.cluster_sizes",
            actual_cluster_sizes,
            expected_cluster_sizes,
        ),
        _check_true(
            "paper_reference.clustering.cluster_heights",
            bool(
                np.allclose(
                    actual_cluster_heights,
                    expected_cluster_heights,
                    rtol=0.0,
                    atol=1e-12,
                )
            ),
        ),
        _check_equal(
            "paper_reference.clustering.memberships",
            actual_member_hashes,
            expected_member_hashes,
        ),
    )
    return AthensArtifactValidation(
        state_sequences_path.parent,
        (*identity_checks, maximum_check, *semantic_checks),
    )


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
    _write_json(paths.scheduling_diagnostics, _scheduling_diagnostics_json(outputs))
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
    _linkage_method_comparison(outputs.dissimilarity_matrix).to_csv(
        paths.linkage_method_comparison, index=False
    )
    _cluster_labels_frame(outputs).to_csv(paths.cluster_labels, index=False)
    outputs.cluster_sizes.to_csv(paths.cluster_summaries, index=False)
    outputs.state_distribution.to_csv(paths.cluster_state_distribution, index=False)
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
    demographics.associations.to_csv(paths.demographic_associations, index=False)
    demographics.bivariate.to_csv(paths.bivariate_demographics, index=False)
    write_marginal_demographic_svg(
        demographics.marginal, paths.marginal_demographic_figure
    )
    write_bivariate_demographic_svg(
        demographics.bivariate, paths.bivariate_demographic_figure
    )
    _write_json(
        paths.manifest,
        _manifest_json(paths, outputs, workflow=workflow, description=description),
    )
    return paths


def main() -> None:
    """Run the migrated reanalysis as a directly executed script."""
    paths = write_reanalysis_artifacts(Path("examples/athens/output/reanalysis"))
    print(f"Wrote migrated reanalysis artifacts to {paths.root}")


def verify_athens_sources(
    source_root: Path,
    *,
    wide_diary_path: Path = DEFAULT_ATHENS_WIDE_DIARY_PATH,
) -> dict[str, JsonValue]:
    """Verify manuscript, upstream input, lock, and revision provenance."""
    source_root = source_root.resolve()
    source_files: dict[str, JsonValue] = {}
    for filename, expected_hash in EXPECTED_ATHENS_SOURCE_HASHES.items():
        path = source_root / filename
        if not path.exists():
            raise FileNotFoundError(f"Required paper source file is missing: {path}")
        actual_hash = _file_sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(
                f"Hash mismatch for {filename}: expected {expected_hash}, got "
                f"{actual_hash}."
            )
        source_files[filename] = {
            "path": filename,
            "sha256": actual_hash,
            "expected_sha256": expected_hash,
            "matches": True,
            "size_bytes": path.stat().st_size,
        }
    zip_members = _verify_zip_members(source_root / "CSuM2026.zip")
    survey_key = "examples/athens/data/raw_diaries_athens_wide.csv"
    input_files = _verify_files(
        source_root,
        {
            name: expected_hash
            for name, expected_hash in EXPECTED_ATHENS_INPUT_HASHES.items()
            if name != survey_key
        },
    )
    input_files[survey_key] = _verified_file_report(
        wide_diary_path.resolve(),
        logical_path=survey_key,
        expected_hash=EXPECTED_ATHENS_INPUT_HASHES[survey_key],
    )
    return {
        "source_root": str(source_root),
        "all_sources_match": True,
        "files": source_files,
        "zip_members": zip_members,
        "inputs": input_files,
        "software": _software_provenance(source_root),
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
        linkage_method_comparison=root / "linkage_method_comparison.csv",
        cluster_labels=root / "cluster_labels.csv",
        cluster_summaries=root / "cluster_summaries.csv",
        cluster_state_distribution=root / "cluster_state_distribution.csv",
        cluster_time_distribution=root / "cluster_time_distribution.csv",
        dendrogram_layout=root / "dendrogram_layout.json",
        dendrogram_figure=root / "figures" / "dendrogram.svg",
        complete_demographic_records=root / "demographics" / "complete_records.csv",
        marginal_demographics=root / "demographics" / "marginal_demographics.csv",
        demographic_associations=(
            root / "demographics" / "demographic_associations.csv"
        ),
        bivariate_demographics=root / "demographics" / "bivariate_demographics.csv",
        marginal_demographic_figure=root / "figures" / "marginal_demographics.svg",
        bivariate_demographic_figure=root / "figures" / "bivariate_demographics.svg",
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
        ("linkage_method_comparison", paths.linkage_method_comparison),
        ("cluster_labels", paths.cluster_labels),
        ("cluster_summaries", paths.cluster_summaries),
        ("cluster_state_distribution", paths.cluster_state_distribution),
        ("cluster_time_distribution", paths.cluster_time_distribution),
        ("dendrogram_layout", paths.dendrogram_layout),
        ("dendrogram_figure", paths.dendrogram_figure),
        ("complete_demographic_records", paths.complete_demographic_records),
        ("marginal_demographics", paths.marginal_demographics),
        ("demographic_associations", paths.demographic_associations),
        ("bivariate_demographics", paths.bivariate_demographics),
        ("marginal_demographic_figure", paths.marginal_demographic_figure),
        ("bivariate_demographic_figure", paths.bivariate_demographic_figure),
    )


def _check_path_exists(name: str, path: Path) -> AthensArtifactCheck:
    if path.exists():
        return AthensArtifactCheck(name, True, f"`{path}` exists.")
    return AthensArtifactCheck(name, False, f"`{path}` is missing.")


def _check_equal[ValueT](
    name: str, actual: ValueT, expected: ValueT
) -> AthensArtifactCheck:
    if actual == expected:
        return AthensArtifactCheck(name, True, f"got expected value {expected!r}.")
    return AthensArtifactCheck(name, False, f"expected {expected!r}, got {actual!r}.")


def _check_true(name: str, condition: bool) -> AthensArtifactCheck:
    if condition:
        return AthensArtifactCheck(name, True, "condition is true.")
    return AthensArtifactCheck(name, False, "condition is false.")


def _check_manifest_paths(
    paths: AthensArtifactPaths, manifest_artifacts: dict[str, JsonValue]
) -> tuple[AthensArtifactCheck, ...]:
    expected_paths = {
        name: path for name, path in _named_artifact_paths(paths) if name != "manifest"
    }
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


def _check_artifact_hashes(
    paths: AthensArtifactPaths, manifest_hashes: dict[str, JsonValue]
) -> tuple[AthensArtifactCheck, ...]:
    return tuple(
        _check_equal(
            f"manifest.artifact_sha256.{name}",
            _file_sha256(path),
            _json_string(manifest_hashes, name),
        )
        for name, path in _named_artifact_paths(paths)
        if name != "manifest"
    )


def _source_hash_contract_checks(
    source_hashes: dict[str, JsonValue],
) -> tuple[AthensArtifactCheck, ...]:
    try:
        source_root = Path(_json_string(source_hashes, "source_root"))
        expected_files: dict[str, JsonValue] = {}
        for name, expected_hash in EXPECTED_ATHENS_SOURCE_HASHES.items():
            path = source_root / name
            actual_hash = _file_sha256(path)
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch for {name}: expected {expected_hash}, got "
                    f"{actual_hash}."
                )
            expected_files[name] = {
                "path": name,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "matches": actual_hash == expected_hash,
                "size_bytes": path.stat().st_size,
            }
        reported_inputs = _json_dict(source_hashes, "inputs")
        expected_inputs: dict[str, JsonValue] = {}
        for name, expected_hash in EXPECTED_ATHENS_INPUT_HASHES.items():
            report = _json_dict(reported_inputs, name)
            expected_inputs[name] = _verified_file_report(
                Path(_json_string(report, "resolved_path")),
                logical_path=name,
                expected_hash=expected_hash,
            )
        expected_zip_members = _verify_zip_members(source_root / "CSuM2026.zip")
        expected_software = _software_provenance(source_root)
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as error:
        message = f"could not verify reported sources independently: {error}"
        return tuple(
            AthensArtifactCheck(f"source_hashes.{section}.contract", False, message)
            for section in ("files", "zip_members", "inputs", "software")
        )
    return (
        _check_equal(
            "source_hashes.files.contract",
            _json_dict(source_hashes, "files"),
            expected_files,
        ),
        _check_equal(
            "source_hashes.zip_members.contract",
            _json_dict(source_hashes, "zip_members"),
            expected_zip_members,
        ),
        _check_equal(
            "source_hashes.inputs.contract",
            reported_inputs,
            expected_inputs,
        ),
        _check_equal(
            "source_hashes.software.contract",
            _json_dict(source_hashes, "software"),
            expected_software,
        ),
    )


def _read_json_file(path: Path) -> dict[str, JsonValue]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"`{path}` must contain a JSON object.")
    result: dict[str, JsonValue] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise ValueError(f"`{path}` contains a non-string JSON object key.")
        result[key] = value
    return result


def _json_dict(data: dict[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = data[key]
    if not isinstance(value, dict):
        raise ValueError(f"JSON key `{key}` must contain an object.")
    result: dict[str, JsonValue] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str):
            raise ValueError(f"JSON key `{key}` contains a non-string nested key.")
        result[nested_key] = nested_value
    return result


def _json_dict_list(data: dict[str, JsonValue], key: str) -> list[dict[str, JsonValue]]:
    value = data[key]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"JSON key `{key}` must contain a list of objects.")
    return [item for item in value if isinstance(item, dict)]


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


def _json_float(data: dict[str, JsonValue], key: str) -> float:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"JSON key `{key}` must contain a number.")
    return float(value)


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


def _cut_leaves(node: CutDendrogramNode) -> tuple[CutDendrogramNode, ...]:
    if node.is_leaf:
        return (node,)
    if node.left is None or node.right is None:
        raise RuntimeError("Expanded cut-dendrogram node is missing a child.")
    return (*_cut_leaves(node.left), *_cut_leaves(node.right))


def _member_indices_sha256(members: tuple[int, ...]) -> str:
    encoded = np.asarray(sorted(members), dtype="<i8").tobytes()
    return sha256(encoded).hexdigest().upper()


def _observation_keys_sha256(diary_summary: pd.DataFrame) -> str:
    keys = [
        [_identifier_text(household_id), _identifier_text(person_id)]
        for household_id, person_id in zip(
            diary_summary["household_id"],
            diary_summary["person_id"],
            strict=True,
        )
    ]
    encoded = json.dumps(keys, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(encoded).hexdigest().upper()


def _identifier_text(value: object) -> str:
    if isinstance(value, int | np.integer):
        return str(int(value))
    if isinstance(value, float | np.floating) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _diary_summary_matches_scheduled_trips(
    diary_summary: pd.DataFrame, scheduled_trips: pd.DataFrame
) -> bool:
    required_trip_columns = {
        "household_id",
        "person_id",
        "trip_sequence",
        "departure_second",
        "arrival_second",
    }
    required_summary_columns = {
        "household_id",
        "person_id",
        "n_trips",
        "first_departure_second",
        "last_arrival_second",
    }
    if not required_trip_columns <= set(scheduled_trips.columns) or not (
        required_summary_columns <= set(diary_summary.columns)
    ):
        return False
    rows: list[dict[str, object]] = []
    for key, trips in scheduled_trips.groupby(
        ["household_id", "person_id"], sort=False
    ):
        household_id, person_id = cast("tuple[object, object]", key)
        ordered = trips.sort_values("trip_sequence")
        rows.append(
            {
                "household_id": household_id,
                "person_id": person_id,
                "n_trips": len(ordered),
                "first_departure_second": ordered.iloc[0]["departure_second"],
                "last_arrival_second": ordered.iloc[-1]["arrival_second"],
            }
        )
    return _frames_match(diary_summary, pd.DataFrame(rows))


def _state_sequences_from_episodes(
    episodes: pd.DataFrame, diary_summary: pd.DataFrame
) -> tuple[tuple[str, ...], ...] | None:
    required = {
        "household_id",
        "person_id",
        "episode_sequence",
        "state",
        "start_second",
        "end_second",
    }
    if not required <= set(episodes.columns):
        return None
    expected_keys = tuple(
        (_identifier_text(household_id), _identifier_text(person_id))
        for household_id, person_id in zip(
            diary_summary["household_id"],
            diary_summary["person_id"],
            strict=True,
        )
    )
    actual_keys: list[tuple[str, str]] = []
    sequences: list[tuple[str, ...]] = []
    try:
        for key, frame in episodes.groupby(["household_id", "person_id"], sort=False):
            household_id, person_id = cast("tuple[object, object]", key)
            ordered = frame.sort_values("episode_sequence")
            if ordered["episode_sequence"].tolist() != list(range(1, len(ordered) + 1)):
                return None
            episode_values = tuple(
                Episode(
                    state=str(state),
                    start_second=int(start_second),
                    end_second=int(end_second),
                )
                for state, start_second, end_second in ordered[
                    ["state", "start_second", "end_second"]
                ].itertuples(index=False, name=None)
            )
            expected_start = 0
            for episode in episode_values:
                if (
                    episode.start_second != expected_start
                    or episode.end_second <= episode.start_second
                ):
                    return None
                expected_start = episode.end_second
            if expected_start != 86_400:
                return None
            actual_keys.append(
                (_identifier_text(household_id), _identifier_text(person_id))
            )
            sequences.append(discretize_episodes(episode_values))
    except (TypeError, ValueError):
        return None
    if tuple(actual_keys) != expected_keys:
        return None
    return tuple(sequences)


def _frames_match(actual: pd.DataFrame, expected: pd.DataFrame) -> bool:
    if (
        tuple(actual.columns) != tuple(expected.columns)
        or actual.shape != expected.shape
    ):
        return False
    for column in actual.columns:
        actual_values = actual[column]
        expected_values = expected[column]
        if pd.api.types.is_numeric_dtype(
            actual_values
        ) and pd.api.types.is_numeric_dtype(expected_values):
            if not np.allclose(
                actual_values.to_numpy(dtype=np.float64),
                expected_values.to_numpy(dtype=np.float64),
                rtol=0.0,
                atol=1e-12,
                equal_nan=True,
            ):
                return False
        elif not np.array_equal(
            actual_values.fillna("<missing>").astype(str).to_numpy(),
            expected_values.fillna("<missing>").astype(str).to_numpy(),
        ):
            return False
    return True


def _canonical_keys_joinable(
    trips: pd.DataFrame,
    persons: pd.DataFrame,
    households: pd.DataFrame,
) -> bool:
    required_trip_columns = {"household_id", "person_id"}
    required_person_columns = {"household_id", "person_id"}
    if (
        not required_trip_columns <= set(trips.columns)
        or not required_person_columns <= set(persons.columns)
        or "household_id" not in households.columns
    ):
        return False
    person_keys = set(
        zip(
            persons["household_id"].map(_identifier_text),
            persons["person_id"].map(_identifier_text),
            strict=True,
        )
    )
    trip_keys = set(
        zip(
            trips["household_id"].map(_identifier_text),
            trips["person_id"].map(_identifier_text),
            strict=True,
        )
    )
    household_keys = set(households["household_id"].map(_identifier_text))
    person_households = set(persons["household_id"].map(_identifier_text))
    return bool(
        len(person_keys) == len(persons)
        and len(household_keys) == len(households)
        and trip_keys <= person_keys
        and person_households <= household_keys
    )


def _canonical_tables_are_valid(
    trips: pd.DataFrame,
    persons: pd.DataFrame,
    households: pd.DataFrame,
) -> bool:
    validation = validate_dataframes(
        trips,
        persons=persons,
        households=households,
        travel_time_function=AthensTravelTimeResolver.from_files(
            missing_sample_policy="strict"
        ),
    )
    return validation.normalized_tables is not None


def _scheduled_trip_timing_is_valid(scheduled_trips: pd.DataFrame) -> bool:
    columns = (
        "trip_sequence",
        "departure_second",
        "arrival_second",
        "travel_time_seconds",
    )
    if not set(columns) <= set(scheduled_trips.columns):
        return False
    numeric = scheduled_trips.loc[:, columns].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        return False
    values = numeric.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
        return False
    if not (
        (numeric["trip_sequence"] > 0).all()
        and (numeric["travel_time_seconds"] > 0).all()
        and (numeric["arrival_second"] > numeric["departure_second"]).all()
        and (
            numeric["arrival_second"] - numeric["departure_second"]
            == numeric["travel_time_seconds"]
        ).all()
    ):
        return False
    for _, frame in scheduled_trips.groupby(["household_id", "person_id"], sort=False):
        ordered = frame.sort_values("trip_sequence")
        if ordered["trip_sequence"].tolist() != list(range(1, len(ordered) + 1)):
            return False
        if len(ordered) <= 1:
            continue
        previous_destinations = ordered["destination"].iloc[:-1].map(_identifier_text)
        next_origins = ordered["origin"].iloc[1:].map(_identifier_text)
        if not np.array_equal(
            previous_destinations.to_numpy(), next_origins.to_numpy()
        ):
            return False
        previous_arrivals = ordered["arrival_second"].iloc[:-1].to_numpy(dtype=np.int64)
        next_departures = ordered["departure_second"].iloc[1:].to_numpy(dtype=np.int64)
        if np.any(next_departures - previous_arrivals < 1_800):
            return False
    return True


def _expected_manifest_method(workflow: str) -> dict[str, JsonValue]:
    return {
        "time_origin_clock": "04:00",
        "observation_window_seconds": 86400,
        "sequence_interval_seconds": 900,
        "minimum_activity_duration_seconds": 1800,
        "linkage": "average",
        "optimal_leaf_ordering": True,
        "unreduced_activity_categories": 7,
        "unreduced_travel_mode_categories": 8,
        "exclusion": (
            "not applicable to the smoke workflow"
            if workflow == "athens_smoke"
            else (
                "person 549 is excluded for a strict non-finite routing sample; "
                "the retained evidence does not establish temporal infeasibility"
            )
        ),
    }


def _cluster_summaries_match_labels(
    summaries: pd.DataFrame,
    labels: pd.DataFrame,
    diary_count: int,
) -> bool:
    required = {"cluster", "n_diaries", "share"}
    if not required <= set(summaries.columns) or "cluster" not in labels.columns:
        return False
    expected = labels["cluster"].value_counts().sort_index()
    actual = summaries.set_index("cluster").sort_index()
    if tuple(actual.index) != tuple(expected.index):
        return False
    return bool(
        np.array_equal(actual["n_diaries"].to_numpy(), expected.to_numpy())
        and np.allclose(
            actual["share"].to_numpy(dtype=np.float64),
            expected.to_numpy(dtype=np.float64) / diary_count,
            rtol=0.0,
            atol=1e-12,
        )
    )


def _linkage_method_comparison(
    dissimilarity: np.ndarray[tuple[int, ...], np.dtype[np.float64]],
) -> pd.DataFrame:
    normalized = dissimilarity / float(np.max(dissimilarity))
    condensed = squareform(normalized, checks=False)
    rows = []
    for method in ("single", "complete", "average", "weighted"):
        candidate = linkage(
            condensed,
            method=method,
            optimal_ordering=False,
        )
        correlation, _ = cophenet(candidate, condensed)
        rows.append(
            {
                "method": method,
                "cophenetic_correlation": float(correlation),
            }
        )
    return pd.DataFrame(rows, columns=["method", "cophenetic_correlation"])


def _average_linkage_is_best(comparison: pd.DataFrame) -> bool:
    required = {"method", "cophenetic_correlation"}
    if not required <= set(comparison.columns):
        return False
    correlations = comparison.set_index("method")["cophenetic_correlation"]
    return bool(
        set(correlations.index) == {"single", "complete", "average", "weighted"}
        and correlations.notna().all()
        and correlations.idxmax() == "average"
        and correlations["average"] > correlations.drop(index="average").max()
    )


def _linkage_correlations_match_reference(
    comparison: pd.DataFrame,
    expected: dict[str, JsonValue],
) -> bool:
    if not {"method", "cophenetic_correlation"} <= set(comparison.columns):
        return False
    actual = comparison.set_index("method")["cophenetic_correlation"].to_dict()
    return set(actual) == set(expected) and all(
        np.isclose(
            float(actual[method]),
            _json_float(expected, method),
            rtol=0.0,
            atol=1e-12,
        )
        for method in actual
    )


def _dendrogram_matches_diaries(
    dendrogram: dict[str, JsonValue],
    diary_summary: pd.DataFrame,
    linkage_matrix: LinkageMatrix,
) -> bool:
    indices = _json_int_tuple(dendrogram, "leaf_indices")
    labels = _json_string_list(dendrogram, "leaf_labels")
    expected_indices = tuple(int(index) for index in leaf_order(linkage_matrix))
    diary_labels = tuple(
        f"{_identifier_text(household_id)}:{_identifier_text(person_id)}"
        for household_id, person_id in zip(
            diary_summary["household_id"],
            diary_summary["person_id"],
            strict=True,
        )
    )
    return indices == expected_indices and labels == tuple(
        diary_labels[index] for index in indices
    )


def _demographic_associations_match_reference(summary: pd.DataFrame) -> bool:
    required = {"variable_x", "variable_y", "cramers_v"}
    if not required <= set(summary.columns):
        return False
    expected = _json_dict(
        _json_dict(_read_json_file(PAPER_RESULT_REFERENCE_PATH), "demographics"),
        "bias_corrected_cramers_v",
    )
    if summary.duplicated(["variable_x", "variable_y"]).any():
        return False
    associations = summary.head(len(expected))
    actual = {
        f"{variable_x}|{variable_y}": float(cast("float", value))
        for variable_x, variable_y, value in zip(
            associations["variable_x"],
            associations["variable_y"],
            associations["cramers_v"],
            strict=True,
        )
    }
    if tuple(actual) != tuple(expected):
        return False
    return all(
        np.isclose(
            actual[key],
            _json_float(expected, key),
            rtol=0.0,
            atol=1e-12,
        )
        for key in actual
    )


def _expected_unreduced_states() -> set[str]:
    activities = {
        "home",
        "work",
        "education",
        "market",
        "recreation",
        "service",
        "other",
    }
    modes = {
        "car",
        "taxi",
        "bus",
        "train",
        "motorcycle",
        "bicycle",
        "walk",
        "escooter",
    }
    return activities | {f"trip_{mode}" for mode in modes}


def _expected_compound_states() -> set[str]:
    reduced_states = {
        "home",
        "rigid",
        "flexible",
        "trip_car",
        "trip_motorcycle",
        "trip_bus",
        "trip_train",
        "trip_micromobility",
        "trip_walk",
    }
    return {f"{state}@p{period}" for state in reduced_states for period in range(1, 5)}


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


def _imputation_horizon_report(
    scheduled_trips: pd.DataFrame,
) -> dict[str, JsonValue]:
    imputed = scheduled_trips[scheduled_trips["is_imputed_return_home"].fillna(False)]
    wholly_cropped = imputed["departure_second"] >= 86_400
    partially_cropped = (imputed["departure_second"] < 86_400) & (
        imputed["arrival_second"] > 86_400
    )
    return {
        "observation_window_seconds": 86_400,
        "wholly_cropped_trips": int(wholly_cropped.sum()),
        "partially_cropped_trips": int(partially_cropped.sum()),
    }


def _routing_fallback_report(
    scheduled_trips: pd.DataFrame, workflow: str
) -> dict[str, JsonValue]:
    if workflow != "athens_migrated_reanalysis":
        return {"applies": False}
    encoded_zones = set(AthensTravelTimeResolver.from_files().zone_encoder)
    origin_zones = scheduled_trips["origin"].map(_identifier_text)
    destination_zones = scheduled_trips["destination"].map(_identifier_text)
    unencoded = ~origin_zones.isin(encoded_zones) | ~destination_zones.isin(
        encoded_zones
    )
    affected = scheduled_trips[unencoded]
    missing_zones = sorted(
        (set(origin_zones) | set(destination_zones)) - encoded_zones,
        key=int,
    )
    return {
        "applies": True,
        "encoded_zones": len(encoded_zones),
        "survey_zones": len(set(origin_zones) | set(destination_zones)),
        "unencoded_zones": missing_zones,
        "affected_trips": len(affected),
        "affected_diaries": len(affected.groupby(["household_id", "person_id"])),
        "affected_imputed_returns": int(
            affected["is_imputed_return_home"].fillna(False).sum()
        ),
        "interzonal_policy": "time-specific network-wide mean",
        "intrazonal_policy": "mean zonal length divided by mode speed",
    }


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
    scheduled_trips = _scheduled_trips_frame(outputs.scheduled.diaries)
    method = _expected_manifest_method(workflow)
    method["routing_fallback"] = _routing_fallback_report(scheduled_trips, workflow)
    return {
        "workflow": workflow,
        "claim_status": (
            "smoke_test"
            if workflow == "athens_smoke"
            else "migrated_reanalysis_not_end_to_end_reproduction"
        ),
        "description": description,
        "artifact_sha256": {
            name: _file_sha256(path)
            for name, path in _named_artifact_paths(paths)
            if name != "manifest"
        },
        "scheduled_diaries": outputs.scheduled.diagnostics.scheduled_diaries,
        "sequence_shape": [len(outputs.sequences), len(outputs.sequences[0])],
        "cluster_count": int(outputs.cluster_sizes.shape[0]),
        "imputed_return_home_trips": _imputed_return_home_count(scheduled_trips),
        "method": method,
        "randomness": {
            "scheduling": {
                "library": "python.random",
                "generator": "Random (MT19937)",
                "seed": 2026,
                "stream": "one stream shared across diaries in canonical order",
                "sampling": "uniform over each refined departure interval",
            },
            "return_home_imputation": {
                "library": "python.random",
                "generator": "Random (MT19937)",
                "seed": 2026,
                "stream": "separate stream shared across eligible diaries",
                "sampling": "purpose-stratified inverse empirical activity duration",
                "horizon": _imputation_horizon_report(scheduled_trips),
            },
        },
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
            "diary_summary": _relative_artifact_path(paths.root, paths.diary_summary),
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
            "linkage_matrix": _relative_artifact_path(paths.root, paths.linkage_matrix),
            "linkage_method_comparison": _relative_artifact_path(
                paths.root, paths.linkage_method_comparison
            ),
            "cluster_labels": _relative_artifact_path(paths.root, paths.cluster_labels),
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
            "demographic_associations": _relative_artifact_path(
                paths.root, paths.demographic_associations
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
        "The checked-in wide diary fixture has the paper source schema but only "
        "three diaries; it is not the full 513-diary CSuM2026 input."
        if input_tables.raw_diaries < 513
        else "The migrated wide diary source contains the 513 raw diaries used by "
        "the migrated reanalysis."
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
                    "Required paper source member is missing from "
                    f"{zip_path.name}: {member_name}"
                )
            data = archive.read(member_name)
            actual_hash = sha256(data).hexdigest().upper()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Hash mismatch for {member_name} inside {zip_path.name}: "
                    f"expected {expected_hash}, got {actual_hash}."
                )
            members[member_name] = {
                "path": member_name,
                "sha256": actual_hash,
                "expected_sha256": expected_hash,
                "matches": True,
                "size_bytes": len(data),
            }
    return members


def _verify_files(
    source_root: Path, expected_hashes: dict[str, str]
) -> dict[str, JsonValue]:
    files: dict[str, JsonValue] = {}
    for relative_path, expected_hash in expected_hashes.items():
        path = source_root / relative_path
        files[relative_path] = _verified_file_report(
            path, logical_path=relative_path, expected_hash=expected_hash
        )
    return files


def _verified_file_report(
    path: Path, *, logical_path: str, expected_hash: str
) -> dict[str, JsonValue]:
    if not path.exists():
        raise FileNotFoundError(f"Required source file is missing: {path}")
    actual_hash = _file_sha256(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"Hash mismatch for {logical_path}: expected {expected_hash}, got "
            f"{actual_hash}."
        )
    return {
        "path": logical_path,
        "resolved_path": str(path.resolve()),
        "sha256": actual_hash,
        "expected_sha256": expected_hash,
        "matches": True,
        "size_bytes": path.stat().st_size,
    }


def _software_provenance(source_root: Path) -> dict[str, JsonValue]:
    lock_path = source_root / "uv.lock"
    if not lock_path.exists():
        raise FileNotFoundError(f"Required lockfile is missing: {lock_path}")
    revision = _git_output(source_root, "rev-parse", "HEAD")
    status = _git_output(source_root, "status", "--porcelain", "--untracked-files=no")
    return {
        "python": platform.python_version(),
        "packages": {
            package: version(package)
            for package in ("athenspop", "numpy", "pandas", "scipy")
        },
        "uv_lock_sha256": _file_sha256(lock_path),
        "git_revision": revision,
        "tracked_worktree_dirty": bool(status),
    }


def _git_output(source_root: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", *arguments],
        cwd=source_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _write_json(path: Path, data: dict[str, JsonValue]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
