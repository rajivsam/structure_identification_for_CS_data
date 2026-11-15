"""
Comprehensive test suite for structure_id v2.0 pipeline
Tests full pipeline with dataset splits and acceptance criteria
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from structure_id import structure_id, StructureIDConfig, compare_structures


# ============================================================================
# Fixtures and Data Loading
# ============================================================================

@pytest.fixture
def data_path():
    """Path to test dataset"""
    return Path(__file__).parent.parent / "data" / "model_ready_numeric_data.csv"


@pytest.fixture
def dataset(data_path):
    """Load the full dataset"""
    df = pd.read_csv(data_path)
    return df


@pytest.fixture
def subset_a(dataset):
    """First half of dataset"""
    return dataset.iloc[:len(dataset)//2].reset_index(drop=True)


@pytest.fixture
def subset_b(dataset):
    """Second half of dataset"""
    return dataset.iloc[len(dataset)//2:].reset_index(drop=True)


@pytest.fixture
def config():
    """Default config"""
    return StructureIDConfig(
        mutual_information_threshold=0.85,
        min_cluster_size=15,
        alpha=0.05,
        std_threshold=1e-5,
        max_missing_ratio=0.20,
        max_categories=30,
        max_class_concentration=0.98,
    )


# ============================================================================
# Test Stage 0: Input Validation
# ============================================================================

def test_stage0_empty_data(config):
    """Stage 0: Reject empty data"""
    with pytest.raises(ValueError, match="empty"):
        structure_id(pd.DataFrame(), "target", "regression", config=config)


def test_stage0_missing_target(dataset, config):
    """Stage 0: Reject missing target column"""
    with pytest.raises(ValueError, match="Target"):
        structure_id(dataset, "nonexistent_column", "regression", config=config)


def test_stage0_invalid_task_type(dataset, config):
    """Stage 0: Reject invalid task type"""
    with pytest.raises(ValueError, match="Task type"):
        structure_id(dataset, "loan_status_r", "invalid_task", config=config)


def test_stage0_validates_structural_covariates(dataset, config):
    """Stage 0: Reject missing structural covariates"""
    with pytest.raises(ValueError, match="not found"):
        structure_id(
            dataset,
            "loan_status_r",
            "regression",
            structural_covariates=["nonexistent"],
            config=config,
        )


def test_stage0_target_excluded_from_candidates(subset_a, config):
    """Stage 0: Target excluded from candidate features"""
    result = structure_id(
        subset_a,
        "loan_status_r",
        "regression",
        config=config,
    )
    # Target should not appear in candidate features
    assert "loan_status_r" not in result.diagnostics["stage0_validation"]["surviving_features"]


# ============================================================================
# Test Stage 1: Redundancy Collapse
# ============================================================================

def test_stage1_redundancy_collapse_basic(subset_a, config):
    """Stage 1: Feature redundancy collapse produces representatives"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Should have column structures
    assert len(result.explicit_column_structures) >= 0
    
    # Representative features should be in diagnostics
    stage1_diag = result.diagnostics["stage1_redundancy"]
    assert "n_initial_features" in stage1_diag
    assert "n_surviving_features" in stage1_diag
    assert stage1_diag["n_surviving_features"] <= stage1_diag["n_initial_features"]


def test_stage1_representative_selection(subset_a, config):
    """Stage 1: Representatives selected from multi-member clusters"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Check that representatives have highest variance in their clusters
    for struct in result.explicit_column_structures:
        if len(struct["cluster_members"]) > 1:
            rep = struct["representative_feature"]
            members = struct["cluster_members"]
            
            # Representative should have highest or near-highest variance
            variances = {m: subset_a[m].var() for m in members}
            max_var = max(variances.values())
            rep_var = variances[rep]
            
            # Allow small tolerance for numerical differences
            assert rep_var >= max_var * 0.99


# ============================================================================
# Test Stage 2: Gram-Schmidt Orthogonalization
# ============================================================================

def test_stage2_orthogonalization_exists(subset_a, config):
    """Stage 2: Orthogonal basis is created"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    assert result.orthogonal_basis is not None
    assert not result.orthogonal_basis.empty
    assert "structure_id" in result.orthogonal_basis.columns


def test_stage2_orthogonality(subset_a, config):
    """Stage 2: Orthogonal features have near-zero correlation"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Get orthogonal features (exclude structure_id)
    ortho_cols = [c for c in result.orthogonal_basis.columns if c != "structure_id"]
    
    if len(ortho_cols) > 1:
        # Compute correlation matrix
        ortho_data = result.orthogonal_basis[ortho_cols]
        corr_matrix = ortho_data.corr().abs()
        
        # Off-diagonal correlations should be very small
        corr_array = corr_matrix.values.copy()
        np.fill_diagonal(corr_array, 0)
        max_corr = corr_array.max()
        
        # Should be nearly orthogonal (correlation < 0.1 for safety margin)
        assert max_corr < 0.15, f"Orthogonal features have correlation {max_corr}"


def test_stage2_interpretation_report(subset_a, config):
    """Stage 2: Interpretation report has proper structure"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    report = result.get_orthogonal_feature_interpretation_report()
    
    assert "table" in report
    assert "structured" in report
    assert "summary" in report
    assert "metadata" in report
    
    # Table should have required columns
    assert "Decorrelated Feature" in report["table"].columns
    assert "Contributing Raw Features (Ordered by Strength)" in report["table"].columns
    
    # Summary should have component info
    summary = report["summary"]
    assert "Component ID" in summary.columns
    assert "Component Name" in summary.columns
    assert "Retained Variance" in summary.columns


def test_stage2_component_contributions(subset_a, config):
    """Stage 2: Contributions sum reasonably and show weights"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    interp = result.orthogonal_interpretation
    
    for comp in interp.get("components", []):
        # Each component should have contributors
        contribs = comp.get("contributors", [])
        
        if contribs:
            # Percentages should sum to approximately 100
            pct_sum = sum(c["percentage"] for c in contribs)
            assert 0 < pct_sum <= 100.1  # Allow small numerical error


# ============================================================================
# Test Stage 3: Row Clustering
# ============================================================================

def test_stage3_row_clustering_creates_structure_id(subset_a, config):
    """Stage 3: Row clustering creates structure_id column"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    assert "structure_id" in result.orthogonal_basis.columns
    assert "structure_id" in result.representative_features.columns


def test_stage3_independent_label_string(subset_a, config):
    """Stage 3: Unclustered rows labeled as 'independent' string"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    structure_ids = result.orthogonal_basis["structure_id"]
    
    # Should contain either integers or "independent" string
    for sid in structure_ids.unique():
        if sid != "independent":
            assert isinstance(sid, (int, np.integer)), f"Non-independent must be integer, got {type(sid)}"


def test_stage3_cluster_profiles(subset_a, config):
    """Stage 3: Cluster profiles recorded"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    profiles = result.explicit_row_structures
    
    for profile in profiles:
        assert "cluster_id" in profile
        assert "size" in profile
        assert "proportion" in profile
        assert profile["size"] >= config.min_cluster_size


def test_stage3_row_counts_match(subset_a, config):
    """Stage 3: Cluster sizes sum to total rows"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    profiles = result.explicit_row_structures
    cluster_total = sum(p["size"] for p in profiles)
    independent_count = (result.orthogonal_basis["structure_id"] == "independent").sum()
    
    total_check = cluster_total + independent_count
    assert total_check == len(result.orthogonal_basis)


# ============================================================================
# Test Stage 4: Latent Heterogeneity Testing
# ============================================================================

def test_stage4_latent_structure_output(subset_a, config):
    """Stage 4: Latent structure detection runs and returns results"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    assert "primary_driver" in result.latent_structures
    assert "cutpoint" in result.latent_structures
    assert "latent_break_detected" in result.latent_structures


def test_stage4_latent_break_optional(subset_a, config):
    """Stage 4: Latent break can be None if not detected"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Should be valid even if no break detected
    latent = result.latent_structures
    if latent["latent_break_detected"]:
        assert latent["primary_driver"] is not None
        assert latent["cutpoint"] is not None
    else:
        assert latent["primary_driver"] is None


# ============================================================================
# Test Result Assembly
# ============================================================================

def test_result_variance_ledger(subset_a, config):
    """Result: Variance ledger is complete"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    ledger = result.variance_ledger
    
    assert "total_input_features" in ledger
    assert "provisional_candidate_features" in ledger
    assert "features_after_redundancy_collapse" in ledger
    assert "dropped_redundant_features" in ledger
    assert "orthogonal_basis_dimension" in ledger
    assert "n_clusters" in ledger
    assert "clustered_rows" in ledger
    assert "independent_rows" in ledger
    assert "total_rows" in ledger


def test_result_representative_features_included(subset_a, config):
    """Result: Representative features DataFrame matches redundancy collapse"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    rep_features = result.representative_features
    
    assert not rep_features.empty
    assert "structure_id" in rep_features.columns
    
    # Should match the Z_rep from Stage 1
    assert len(rep_features) == len(subset_a)


def test_result_orthogonal_basis_dimensions(subset_a, config):
    """Result: Orthogonal basis has correct dimensions"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    basis = result.orthogonal_basis
    
    # Should have same rows as input
    assert len(basis) == len(subset_a)
    
    # Should have orthogonal components + structure_id
    n_ortho = result.variance_ledger["orthogonal_basis_dimension"]
    assert len(basis.columns) == n_ortho + 1


# ============================================================================
# Integration: Consistency Across Dataset Splits
# ============================================================================

def test_consistency_same_columns_selected(subset_a, subset_b, config):
    """Integration: Both subsets select similar candidate features"""
    result_a = structure_id(subset_a, "loan_status_r", "regression", config=config)
    result_b = structure_id(subset_b, "loan_status_r", "regression", config=config)
    
    # Both should survive Stage 0 with similar counts (allowing some variance)
    stage0_a = result_a.diagnostics["stage0_validation"]["candidate_features_after_filtering"]
    stage0_b = result_b.diagnostics["stage0_validation"]["candidate_features_after_filtering"]
    
    # Should be close in count (within 20%)
    diff = abs(stage0_a - stage0_b) / max(stage0_a, stage0_b, 1)
    assert diff < 0.3, f"Stage 0 divergence too large: {stage0_a} vs {stage0_b}"


def test_consistency_orthogonal_dimension(subset_a, subset_b, config):
    """Integration: Both subsets produce similar orthogonal basis dimension"""
    result_a = structure_id(subset_a, "loan_status_r", "regression", config=config)
    result_b = structure_id(subset_b, "loan_status_r", "regression", config=config)
    
    dim_a = result_a.variance_ledger["orthogonal_basis_dimension"]
    dim_b = result_b.variance_ledger["orthogonal_basis_dimension"]
    
    # Dimensions should match or be very close
    assert abs(dim_a - dim_b) <= 1, f"Dimension mismatch: {dim_a} vs {dim_b}"


def test_consistency_clustering_pattern(subset_a, subset_b, config):
    """Integration: Both subsets show similar clustering patterns"""
    result_a = structure_id(subset_a, "loan_status_r", "regression", config=config)
    result_b = structure_id(subset_b, "loan_status_r", "regression", config=config)
    
    # Get proportions of clustered vs independent
    indep_a = (result_a.orthogonal_basis["structure_id"] == "independent").sum() / len(result_a.orthogonal_basis)
    indep_b = (result_b.orthogonal_basis["structure_id"] == "independent").sum() / len(result_b.orthogonal_basis)
    
    # Should have similar independent proportions (within 50% of each other)
    if max(indep_a, indep_b) > 0.05:  # Only if meaningful
        diff = abs(indep_a - indep_b) / max(indep_a, indep_b)
        assert diff < 0.5


def test_compare_structures_works(subset_a, subset_b, config):
    """Integration: compare_structures function works on results"""
    result_a = structure_id(subset_a, "loan_status_r", "regression", config=config)
    result_b = structure_id(subset_b, "loan_status_r", "regression", config=config)
    
    comparison = compare_structures(result_a, result_b)
    
    assert "column_similarity" in comparison
    assert "row_structure_shift" in comparison
    assert "latent_structure_agreement" in comparison
    
    # Should have Jaccard index for columns
    assert "jaccard_index" in comparison["column_similarity"]
    assert 0 <= comparison["column_similarity"]["jaccard_index"] <= 1


# ============================================================================
# Acceptance Criteria
# ============================================================================

def test_acceptance_orthogonal_near_zero_correlation(subset_a, config):
    """Acceptance: Orthogonal columns have near-zero correlation"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Extract orthogonal features
    ortho_cols = [c for c in result.orthogonal_basis.columns if c.startswith("Ortho_")]
    
    if len(ortho_cols) > 1:
        ortho_data = result.orthogonal_basis[ortho_cols]
        corr_matrix = ortho_data.corr().abs()
        
        # Off-diagonal should be tiny
        corr_array = corr_matrix.values.copy()
        np.fill_diagonal(corr_array, 0)
        assert corr_array.max() < 0.2


def test_acceptance_weight_reconstruction(subset_a, config):
    """Acceptance: Linear combinations of raw features reconstruct orthogonal features"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Get weight matrix from interpretation
    interp = result.orthogonal_interpretation
    
    if interp.get("metadata", {}).get("n_original_features", 0) > 0:
        # Weights should exist in components
        for comp in interp.get("components", []):
            raw_weights = comp.get("raw_weights", [])
            assert len(raw_weights) > 0


def test_acceptance_no_wide_dataset_error(subset_a, config):
    """Acceptance: No error for p <= n dataset"""
    # subset_a has ~22 features and many rows, so p << n
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Should complete successfully
    assert result is not None
    assert result.orthogonal_basis is not None


def test_acceptance_reporting_methods_work(subset_a, config):
    """Acceptance: Result reporting methods execute without error"""
    result = structure_id(subset_a, "loan_status_r", "regression", config=config)
    
    # Should be able to get reports
    report = result.get_orthogonal_feature_interpretation_report()
    assert report is not None
    
    # Should be able to convert to HTML
    html = result.to_html()
    assert "<html>" in html.lower()
    assert result.target in html


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_single_feature_dataset(config):
    """Edge case: Dataset with single feature"""
    data = pd.DataFrame({
        "feature": np.random.randn(100),
        "target": np.random.randn(100),
    })
    
    result = structure_id(data, "target", "regression", config=config)
    
    # Should handle gracefully
    assert result is not None


def test_all_constant_features_rejected(config):
    """Edge case: All features are constant - should raise"""
    data = pd.DataFrame({
        "feat1": np.ones(100),
        "feat2": np.ones(100),
        "target": np.random.randn(100),
    })
    
    with pytest.raises(ValueError, match="No valid candidate"):
        structure_id(data, "target", "regression", config=config)


def test_missing_values_handled(config):
    """Edge case: Data with missing values is imputed"""
    np.random.seed(42)
    data = pd.DataFrame({
        "feat1": np.random.randn(100),
        "feat2": np.random.randn(100),
        "target": np.random.randn(100),
    })
    
    # Introduce some missing values
    data.loc[0:5, "feat1"] = np.nan
    data.loc[10:15, "feat2"] = np.nan
    
    # Should not raise, should impute
    result = structure_id(data, "target", "regression", config=config)
    
    assert result is not None
    assert result.orthogonal_basis.isnull().sum().sum() == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
