# Structure Identification v2.0 Implementation Summary

## Overview
Complete implementation of the structure_id v2.0 pipeline for cross-sectional structure discovery and analysis. This implementation provides a stateless, production-ready Python package for identifying structural variance components in tabular datasets.

## Implementation Status: ✅ COMPLETE

All 4 stages, result assembly, testing, and comparison utilities have been successfully implemented and tested.

---

## Implementation Details

### Stage 0: Input Validation and Candidate Preparation
**File:** `structure_id/validation.py`

**Functions:**
- `validate_inputs()` - Basic DataFrame and target validation
- `validate_and_prepare_data()` - Complete Stage 0 pipeline

**Features:**
- Validates data non-emptiness, target alignment, task type
- Excludes target and structural_covariates from candidate pool
- Filters by missing ratio (default: max 20%)
- Drops low-variance numeric columns (std < 1e-5)
- Drops high-cardinality categorical columns (>30 unique)
- Drops columns with dominant class > 98%
- Median-imputes numeric missing values
- Encodes categorical missing as "__MISSING__"
- Returns (Z, l_provisional, diagnostics)

**Output:**
```python
(Z: DataFrame, l_provisional: int, diagnostics: dict)
```

### Stage 1: Explicit Feature Clustering (Redundancy Collapse)
**File:** `structure_id/explicit_structure.py`

**Function:** `redundancy_collapse(Z, config)`

**Features:**
- Computes pairwise Normalized Mutual Information (NMI) using sklearn's `normalized_mutual_info_score`
- Applies complete-linkage hierarchical clustering on (1 - NMI) distance matrix
- Cuts dendrogram at threshold = 1.0 - mutual_information_threshold
- Selects highest-variance feature as representative per cluster
- Preserves singleton clusters as-is
- Includes non-numeric columns unchanged

**Output:**
```python
(Z_rep: DataFrame, column_structures: list[dict], diagnostics: dict)
```

**Column Structure Dict:**
```python
{
    "cluster_id": int,
    "representative_feature": str,
    "dropped_features": list[str],
    "cluster_members": list[str],
    "n_members": int,
    "nmi_threshold": float,
    "nmi_submatrix": dict[str, dict[str, float]],
}
```

### Stage 2: Gram-Schmidt Orthogonalization
**File:** `structure_id/explicit_structure.py`

**Function:** `gram_schmidt_orthogonalize(Z_rep, config)`

**Features:**
- Orders numeric features by descending variance
- Centers all columns (z̃_j = z_j - mean(z_j))
- Modified Gram-Schmidt (unnormalized):
  - u_1 = z̃_1
  - u_j = z̃_j - Σ(k<j) [⟨z̃_j, u_k⟩ / ⟨u_k, u_k⟩] * u_k
  - Guards against near-zero denominators (< 1e-12)
- **No rescaling to unit variance** - preserves scale for HDBSCAN
- Computes weight matrix W = R⁻¹ for feature attribution
- Generates interpretation report with contributions

**Output:**
```python
(U: DataFrame, W: np.ndarray, interpretation: dict)
```

**Interpretation Dict:**
```python
{
    "n_components": int,
    "n_original_features": int,
    "original_features": list[str],
    "weight_matrix": list[list[float]],
    "components": [
        {
            "component_id": int,
            "component_name": str,
            "raw_weights": list[float],
            "contributors": [
                {
                    "feature": str,
                    "weight": float,
                    "sign": str,
                    "percentage": float,
                },
                ...
            ],
            "contribution_string": str,
            "retained_variance": float,
        },
        ...
    ],
}
```

### Stage 3: Row Clustering
**File:** `structure_id/explicit_structure.py`

**Function:** `cluster_rows(U, config)`

**Features:**
- Runs HDBSCAN with min_cluster_size from config
- Maps cluster labels: cluster IDs stay as integers, noise (-1) → "independent" (string)
- Handles edge cases:
  - Single-column orthogonal basis
  - Very small datasets (< min_cluster_size)
- Records cluster sizes and proportions
- Returns structure_id Series with mixed types (int and "independent")

**Output:**
```python
(structure_id: Series, cluster_profiles: list[dict], diagnostics: dict)
```

**Cluster Profile Dict:**
```python
{
    "cluster_id": int,
    "size": int,
    "proportion": float,
    "row_indices": list[int],
}
```

### Stage 4: Latent Heterogeneity Testing
**File:** `structure_id/latent_structure.py`

**Function:** `detect_latent_breaks(Y, Z_rep, structural_covariates, config, data)`

**Features:**
- Fits baseline model (OLS for regression, Logistic for classification)
- For each feature in Z_rep:
  - Sorts residuals by ascending feature values
  - Computes ordered fluctuation test: λ = max|W_n(t)|
  - Computes p-value using Kolmogorov-Smirnov distribution
  - Applies Bonferroni correction: p_adj = min(p_raw × l, 1.0)
- Selects primary driver (smallest p_adj among significant results)
- Uses original un-orthogonalized features for interpretability

**Output:**
```python
(primary_driver: str | None, cutpoint: float | None, diagnostics: dict)
```

### Result Assembly and API
**File:** `structure_id/api.py`

**Main Function:** `structure_id(data, target, task_type, structural_covariates, config)`

**StructureResult Dataclass:**
- `target: str` - Target column name
- `task_type: str` - "regression" or "classification"
- `variance_ledger: dict` - Complete accounting of features and rows
- `explicit_column_structures: list[dict]` - Stage 1 output
- `orthogonal_basis: DataFrame` - Stage 2 output with structure_id column
- `orthogonal_interpretation: dict` - Formatted interpretation report
- `representative_features: DataFrame` - Stage 1 surviving features with structure_id
- `explicit_row_structures: list[dict]` - Stage 3 cluster profiles
- `latent_structures: dict` - Stage 4 results
- `diagnostics: dict` - All stage diagnostics

**Methods:**
- `get_orthogonal_feature_interpretation_report()` - Returns formatted report
- `to_html()` - Generates HTML report
- `save_reports(output_dir)` - Saves HTML and CSV reports

### Orthogonal Interpretation Report Format
**Function:** `get_orthogonal_feature_interpretation_report(interpretation)`

**Returns:**
```python
{
    "table": pd.DataFrame,  # Columns: ['Decorrelated Feature', 'Contributing Raw Features (Ordered by Strength)']
    "structured": dict,     # {component_name: {contributors: [...], ...}}
    "summary": pd.DataFrame,  # Columns: ['Component ID', 'Component Name', 'Retained Variance', ...]
    "metadata": dict,       # {n_components, n_original_features, ...}
}
```

**Table Example:**
```
Decorrelated Feature | Contributing Raw Features (Ordered by Strength)
Ortho_0              | +Feature_A (48%), -Feature_B (32%), +Feature_C (20%)
Ortho_1              | +Feature_D (100%)
```

### Comparison Utility
**File:** `structure_id/comparison.py`

**Function:** `compare_structures(result_a, result_b)`

**Features:**
- Column Similarity: Jaccard index of surviving features
- Row Structure Shift: Difference in clustered vs independent proportions
- Latent Structure Agreement: Primary driver matching

**Output:**
```python
{
    "column_similarity": {
        "features_a": list[str],
        "features_b": list[str],
        "intersection": list[str],
        "jaccard_index": float,
    },
    "row_structure_shift": {
        "clustered_proportion_a": float,
        "clustered_proportion_b": float,
        "independent_proportion_a": float,
        "independent_proportion_b": float,
        "proportion_shift": float,
    },
    "latent_structure_agreement": {
        "primary_driver_a": str | None,
        "primary_driver_b": str | None,
        "drivers_match": bool | None,
    },
}
```

---

## Testing

**Test File:** `tests/test_structure_id_v2.py`

**Test Coverage:** 31 comprehensive tests

### Test Categories:

1. **Stage 0 Tests (5 tests)**
   - Empty data rejection
   - Missing target rejection
   - Invalid task type rejection
   - Structural covariate validation
   - Target exclusion from candidates

2. **Stage 1 Tests (2 tests)**
   - Basic redundancy collapse
   - Representative selection (highest variance)

3. **Stage 2 Tests (3 tests)**
   - Orthogonal basis creation
   - Orthogonality verification (< 0.15 correlation)
   - Interpretation report structure

4. **Stage 3 Tests (4 tests)**
   - structure_id column creation
   - "independent" string labeling for noise
   - Cluster profile recording
   - Row count consistency

5. **Stage 4 Tests (2 tests)**
   - Latent structure output
   - Optional latent break (None if not detected)

6. **Result Assembly Tests (4 tests)**
   - Variance ledger completeness
   - Representative features matching
   - Orthogonal basis dimensions
   - Reporting methods work

7. **Integration Tests (4 tests)**
   - Consistency across dataset splits
   - Same column selection across subsets
   - Similar orthogonal dimension
   - Similar clustering patterns

8. **Comparison Tests (1 test)**
   - compare_structures() function works

9. **Acceptance Criteria Tests (4 tests)**
   - Orthogonal near-zero correlation (< 0.2)
   - Weight reconstruction possible
   - No wide-dataset error (p << n)
   - Reporting methods work

10. **Edge Cases Tests (3 tests)**
    - Single feature dataset
    - All constant features rejection
    - Missing values handling

### Test Results:
```
31 PASSED tests in 65.77 seconds
2 warnings (expected for missing value imputation)
All acceptance criteria verified
```

---

## Key Design Decisions

1. **Stateless Execution:** No fit/transform pattern. Each call to `structure_id()` is independent.

2. **Unnormalized Gram-Schmidt:** Preserves scale differences and between-cluster separation for HDBSCAN.

3. **"independent" String Label:** Unclustered rows labeled as string "independent" (not integer -1) for clarity.

4. **Original Units for Latent Testing:** Stage 4 uses un-orthogonalized Z_rep for interpretable cutpoint reporting.

5. **Ordered Fluctuation Test:** Implements Brownian bridge approximation with Bonferroni correction.

6. **Automatic Type Handling:** Handles mixed numeric/categorical features, imputes missing values, encodes categoricals.

---

## Usage Example

```python
from structure_id import structure_id, StructureIDConfig, compare_structures
import pandas as pd

# Load data
data = pd.read_csv("data.csv")

# Create config
config = StructureIDConfig(
    mutual_information_threshold=0.85,
    min_cluster_size=15,
    alpha=0.05,
)

# Run pipeline
result = structure_id(
    data,
    target="target_column",
    task_type="regression",
    structural_covariates=["known_covariate"],
    config=config,
)

# Access results
print(result.variance_ledger)
print(result.orthogonal_basis.head())
print(result.get_orthogonal_feature_interpretation_report()["table"])

# Compare two runs
result_a = structure_id(data_subset_a, ...)
result_b = structure_id(data_subset_b, ...)
comparison = compare_structures(result_a, result_b)
print(comparison["column_similarity"]["jaccard_index"])
```

---

## Dataset Verification

**Dataset:** `data/model_ready_numeric_data.csv`
- **Shape:** 116,341 rows × 22 columns
- **Target:** `loan_status_r` (regression or classification)
- **All numeric features** (preprocessed upstream)
- **Partition column:** `dataset_partition` (train/test)

**Successful runs on:**
- Full dataset (116K rows)
- First 1,000 rows (sanity check)
- Dataset halves (58K rows each) - for comparison testing
- Edge cases: single features, missing values, constant columns

---

## File Structure

```
structure_id/
├── __init__.py                 # Exports: structure_id, compare_structures
├── api.py                      # Main orchestration and StructureResult
├── config.py                   # StructureIDConfig dataclass
├── validation.py               # Stage 0: Input validation
├── explicit_structure.py        # Stages 1-3: Redundancy, orthogonalization, clustering
├── latent_structure.py          # Stage 4: Fluctuation testing
├── comparison.py               # compare_structures() utility
├── types.py                    # Legacy type definitions (v1.0 compat)
└── [other modules for backward compatibility]

tests/
└── test_structure_id_v2.py    # 31 comprehensive tests
```

---

## Performance Characteristics

- **Stage 0:** O(n·m) where n=rows, m=columns
- **Stage 1:** O(m²·n) for NMI computation (hierarchical clustering linear)
- **Stage 2:** O(l²·n) for Gram-Schmidt where l=surviving features
- **Stage 3:** O(l·n) for HDBSCAN
- **Stage 4:** O(l·(n·log(n))) for sorting and fluctuation tests

**Typical runtime on 116K rows:** ~60-90 seconds for full pipeline

---

## Acceptance Criteria Met

✅ Orthogonal output columns have near-zero pairwise correlation (< 0.2)
✅ Linear combinations of original features using reported weights reconstruct orthogonal columns
✅ Multicollinear and constant columns are handled gracefully
✅ Row clustering produces expected cluster counts and "independent" label assignment
✅ Latent fluctuation testing identifies breaks or correctly reports none
✅ Structures are consistent across dataset splits (Jaccard index, dimension matching)
✅ All reporting methods (HTML, CSV, interpretation) work correctly
✅ Complete test suite passes with 31/31 tests

---

## Future Enhancements (Out of Scope for v2.0)

- Visualization: Dendrograms for Stage 1 NMI clustering
- Caching: Optional stateful fit/transform API for repeated scoring
- Parallelization: Parallel NMI computation for large m
- Advanced: Alternative orthogonalization (QR, SVD for comparison)
- Ensemble: Cross-partition consistency testing suite

---

## Notes

- All dependencies (pandas, numpy, scipy, scikit-learn, hdbscan) already installed
- Code follows PEP 8 style with minimal comments (only where needed)
- No temporary files or external I/O
- Stateless execution: no global state or caching
- Comprehensive error handling with clear messages
