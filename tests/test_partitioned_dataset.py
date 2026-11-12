import pandas as pd

from structure_id import PartitionedDataset, export_cluster_profile_report, structure_id


def test_partition_selection_and_attribute_filtering():
    df = pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1],
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "feature_b": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "feature_c": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "feature_d": [7, 8, 9, 10, 11, 12],
        }
    )

    dataset = PartitionedDataset.from_dataframe(df)
    dataset.set_partition_logic("training", lambda d: d.iloc[:2].copy())
    dataset.set_partition_logic("validation", lambda d: d.iloc[2:4].copy())
    dataset.set_partition_logic("test", lambda d: d.iloc[4:].copy())

    training = dataset.select_partition("training")
    validation = dataset.select_partition("validation")
    test = dataset.select_partition("test")

    assert training.index.tolist() == [0, 1]
    assert validation.index.tolist() == [2, 3]
    assert test.index.tolist() == [4, 5]

    train_features = dataset.apply_training_features(training, ["feature_a", "feature_b"])
    validation_features = dataset.apply_validation_features(validation, ["feature_a", "feature_b"])
    test_features = dataset.apply_test_features(test, ["feature_a", "feature_b"])

    assert list(train_features.columns) == ["feature_a", "feature_b"]
    assert list(validation_features.columns) == ["feature_a", "feature_b"]
    assert list(test_features.columns) == ["feature_a", "feature_b"]

    subset = dataset.select_featurized_attributes(["feature_c", "feature_d"])
    assert list(subset.columns) == ["feature_c", "feature_d"]


def test_missing_requested_attributes_raises_error():
    df = pd.DataFrame({"target": [0, 1], "feature_a": [1.0, 2.0]})
    dataset = PartitionedDataset.from_dataframe(df)

    try:
        dataset.select_featurized_attributes(["feature_a", "missing_feature"])
        raise AssertionError("Expected ValueError for missing feature")
    except ValueError:
        pass


def test_explicit_column_blocks_report_merge_and_correlation_details():
    df = pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1],
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "feature_b": [1.1, 2.2, 3.1, 4.2, 5.3, 6.1],
            "feature_c": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        }
    )

    result = structure_id(data=df, target="target", task_type="classification", structural_covariates=[])
    assert len(result.explicit_column_structures) >= 1
    block = result.explicit_column_structures[0]
    assert len(block.cluster_members) >= 2
    assert block.merge_history
    assert all("merged_pair" in item for item in block.merge_history)
    assert any(abs(rho) > 0.8 for rho in block.pairwise_correlations.values())

    assert "structure_id" in result.selected_columns
    assert result.diagnostics["structure_id_column"] == "structure_id"
    assert set(result.diagnostics["structure_id_values"].values()) <= {"noise", 0, 1, 2, 3, 4, 5}


def test_cluster_profile_export_creates_markdown_and_html(tmp_path):
    df = pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1],
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "feature_b": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "feature_c": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }
    )
    result = structure_id(data=df, target="target", task_type="classification", structural_covariates=[])
    outputs = export_cluster_profile_report(result, output_dir=tmp_path)

    assert outputs["markdown"].exists()
    assert outputs["html"].exists()
    assert "Training Cluster Profile" in outputs["markdown"].read_text(encoding="utf-8")
    assert "<html>" in outputs["html"].read_text(encoding="utf-8")
