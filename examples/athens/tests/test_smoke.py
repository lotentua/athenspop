import numpy as np

from examples.athens.smoke import run_example


def test_athens_smoke_example_runs_canonical_pipeline() -> None:
    outputs = run_example()
    assert not outputs.validation_report.has_errors
    assert outputs.scheduled.diagnostics.scheduled_diaries == 3
    assert len(outputs.dataset.diaries) == 3
    assert len(outputs.sequences) == 3
    assert {len(sequence) for sequence in outputs.sequences} == {96}
    assert outputs.dissimilarity_matrix.shape == (3, 3)
    np.testing.assert_allclose(
        outputs.dissimilarity_matrix, outputs.dissimilarity_matrix.T
    )
    np.testing.assert_allclose(np.diag(outputs.dissimilarity_matrix), np.zeros(3))
    assert outputs.linkage_matrix.shape == (2, 4)
    assert outputs.labels.shape == (3,)
    assert outputs.cluster_sizes["n_diaries"].sum() == 3
    assert outputs.state_distribution["count"].sum() == 288
    assert outputs.dendrogram.leaf_labels
