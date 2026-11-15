# structure_id v2.0 — Complete Usage Guide

**Date:** 2026-11-15 | **Version:** 2.0.0 | **Status:** Production Ready

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Workflow](#basic-workflow)
3. [Understanding Results](#understanding-results)
4. [Interpretation Report Formats](#interpretation-report-formats)
5. [Advanced Usage](#advanced-usage)
6. [Comparing Multiple Runs](#comparing-multiple-runs)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Quick Start

### Installation & Setup

```python
# Ensure dependencies are installed
import pandas as pd
import numpy as np
from structure_id import structure_id, compare_structures, StructureIDConfig
```

### Minimal Example (5 lines)

```python
# Load data
df = pd.read_csv('data/model_ready_numeric_data.csv')

# Run structure identification
result = structure_id(data=df, target='loan_status_r', task_type='classification')

# View results
print(result.variance_ledger)
```

---

## Basic Workflow

### Step 1: Prepare Your Data

```python
import pandas as pd

# Load data
df = pd.read_csv('my_data.csv')

# Check shape and missing values
print(f"Shape: {df.shape}")
print(f"Missing: {df.isnull().sum()}")

# The function handles:
# ✓ Missing values (median-imputes numeric, encodes categorical)
# ✓ Non-numeric columns (automatically excluded)
# ✓ Target column (automatically excluded)
# ✓ Structural covariates (excluded if specified)
```

### Step 2: Configure (Optional)

```python
from structure_id import StructureIDConfig

config = StructureIDConfig(
    mutual_information_threshold=0.85,    # Stage 1: NMI clustering cutoff
    min_cluster_size=15,                  # Stage 3: HDBSCAN parameter
    fluctuation_test_alpha=0.05,          # Stage 4: significance level
    missing_threshold=0.3,                # Stage 0: drop if >30% missing
    variance_threshold=1e-6,              # Stage 0: drop if std < threshold
)
```

### Step 3: Run Structure Identification

```python
result = structure_id(
    data=df,                             # Your DataFrame
    target='loan_status_r',              # Target column name
    task_type='classification',          # 'regression' or 'classification'
    structural_covariates=None,          # Optional: columns to exclude
    feature_order=None,                  # Optional: feature ordering for Stage 1
    config=config,                       # Use default if omitted
)
```

### Step 4: Explore Results

```python
# Variance accounting
print(result.variance_ledger)
"""
{
    'total_input_features': 21,
    'provisional_candidate_features': 17,
    'features_after_redundancy_collapse': 15,
    'orthogonal_basis_dimension': 13,
    'clustered_rows': 48247,
    'independent_rows': 9923,
    'n_clusters': 948,
    ...
}
"""

# Orthogonal basis (U matrix with structure labels)
print(result.orthogonal_basis.head())
print(result.orthogonal_basis.columns)
# Columns: Ortho_0, Ortho_1, ..., Ortho_12, structure_id

# Representative features (Z_rep with structure labels)
print(result.representative_features.head())
```

### Step 5: Get Interpretation Report

```python
# Get the interpretation report
interp = result.get_orthogonal_feature_interpretation_report(
    threshold=0.05,              # Contributors below 5% are filtered
    include_raw_weights=False,   # Set True to include raw weight values
)

# Three output formats available:
print(interp['table'])          # Pandas DataFrame (analyst-friendly)
print(interp['structured'])     # Dictionary (machine-readable/JSON)
print(interp['summary'])        # Summary DataFrame (variance accounting)
print(interp['metadata'])       # Metadata (n_components, threshold, etc.)
```

---

## Understanding Results

### Result Object Structure

```python
result = structure_id(...)

# Main outputs:
result.variance_ledger                  # Dict: accounting summary
result.explicit_column_structures       # List: feature block info
result.orthogonal_basis                 # DataFrame: U + structure_id
result.orthogonal_interpretation        # Dict: interpretation report
result.representative_features          # DataFrame: Z_rep + structure_id
result.explicit_row_structures          # List: cluster profiles
result.latent_structures                # Dict: break detection results
result.diagnostics                      # Dict: warnings, dropped columns
result.report_markdown                  # Str: narrative summary

# Helper methods:
result.get_orthogonal_feature_interpretation_report()  # Get interpretation
result.to_html()                                        # Generate HTML report
result.save_reports(output_dir='reports/')             # Export reports
```

### The 4-Stage Pipeline

| Stage | Input | Process | Output | Files |
|-------|-------|---------|--------|-------|
| **0** | Raw DataFrame | Validate, filter, handle missing | Z (candidates) | `validation.py` |
| **1** | Z (candidates) | NMI clustering, collapse redundancy | Z_rep (15 features) | `explicit_structure.py` |
| **2** | Z_rep | Gram-Schmidt orthogonalization | U (13 components) | `explicit_structure.py` |
| **3** | U | HDBSCAN clustering | structure_id (labels) | `explicit_structure.py` |
| **4** | Y, Z_rep | Fluctuation testing + Bonferroni | primary_driver (str) | `latent_structure.py` |

---

## Interpretation Report Formats

### Format 1: Tabular (Most User-Friendly)

```python
interp['table']

#    Decorrelated Feature                             Contributing Raw Features (Ordered by Strength)
# 0          Ortho_0  +Interest_Rate (62%), -Debt_to_Income (28%), +Loan_Amount (10%)
# 1          Ortho_1  +Debt_to_Income (51%), -Interest_Rate (35%), +Loan_Amount (14%)
# 2          Ortho_2  +Loan_Amount (75%), -Term (25%)
# ...
```

**Use Case:** Presenting findings to analysts, generating reports

**Columns:**
- **Decorrelated Feature:** Component name (Ortho_0, Ortho_1, ...)
- **Contributing Raw Features:** Ordered list (strongest first) with:
  - Sign: `+` (positive contribution) or `-` (negative)
  - Feature name
  - Percentage contribution (% of total |weight|)

### Format 2: Structured Dictionary (Machine-Readable)

```python
interp['structured']

# {
#   'Ortho_0': {
#       'component_name': 'Ortho_0',
#       'retained_variance': 0.34521,
#       'contributors': [
#           {
#               'feature': 'Interest_Rate',
#               'weight': 0.62451,
#               'sign': '+',
#               'percentage': 62.5,
#               'order': 1
#           },
#           {
#               'feature': 'Debt_to_Income',
#               'weight': -0.28130,
#               'sign': '-',
#               'percentage': 28.2,
#               'order': 2
#           },
#           ...
#       ],
#       'total_contributors': 3,
#       'top_driver': 'Interest_Rate',
#   },
#   'Ortho_1': {...},
#   ...
# }
```

**Use Case:** Programmatic access, JSON export, machine learning pipelines

**Structure:**
- Component-keyed dictionary
- Each component has contributors list (ordered by |weight|)
- Each contributor has: feature, weight, sign, percentage, order

### Format 3: Summary (Variance Accounting)

```python
interp['summary']

#   Component ID  Retained Variance Dominant Attribute Group  Top Driver
# 0      Ortho_0         0.345209  Interest_Rate, Debt_to...  Interest_Rate
# 1      Ortho_1         0.218654  Debt_to_Income, Interest...  Debt_to_Income
# 2      Ortho_2         0.156432  Loan_Amount, Term         Loan_Amount
# ...
```

**Use Case:** High-level summary, variance distribution, quick inspection

**Columns:**
- **Component ID:** Ortho_0, Ortho_1, ...
- **Retained Variance:** Proportion of variance in component
- **Dominant Attribute Group:** Top 2-3 contributors (comma-separated)
- **Top Driver:** Strongest contributor

### Format 4: Metadata

```python
interp['metadata']

# {
#     'n_components': 13,
#     'n_original_features': 15,
#     'threshold': 0.05,
#     'total_variance_explained': 0.9876,
#     'mean_contributors_per_component': 2.3,
#     'max_contributors_per_component': 5,
#     'min_contributors_per_component': 1,
# }
```

---

## Advanced Usage

### 1. Custom Feature Ordering

Gram-Schmidt is order-dependent. Control the order:

```python
# Order features by descending variance (default)
result = structure_id(data=df, target='y', task_type='classification')

# Order features custom
feature_order = ['Feature_A', 'Feature_B', 'Feature_C', ...]
result = structure_id(
    data=df,
    target='y',
    task_type='classification',
    feature_order=feature_order,
)
```

### 2. Structural Covariates (Exclude Specific Columns)

Some columns should not participate in structure identification:

```python
result = structure_id(
    data=df,
    target='loan_status_r',
    task_type='classification',
    structural_covariates=['loan_id', 'application_date'],  # Will be excluded
)
```

### 3. Fine-Tuning Configuration

```python
config = StructureIDConfig(
    # Stage 1: NMI Clustering
    mutual_information_threshold=0.80,  # Lower = more aggressive collapse
    
    # Stage 3: HDBSCAN Clustering
    min_cluster_size=10,                # Lower = more clusters
    min_samples=5,
    
    # Stage 0: Filtering
    missing_threshold=0.5,              # Drop if >50% missing
    variance_threshold=1e-8,            # Drop if std < 1e-8
    
    # Stage 4: Latent Testing
    fluctuation_test_alpha=0.01,        # More stringent significance
)

result = structure_id(data=df, target='y', task_type='classification', config=config)
```

### 4. Exporting Reports

```python
# Save HTML and Markdown reports
paths = result.save_reports(output_dir='./reports/')

# Returns: {'html': Path, 'markdown': Path}
print(paths)

# Access markdown directly
print(result.report_markdown)

# Access HTML directly
html_str = result.to_html()
```

### 5. Accessing Intermediate Outputs

```python
# Feature blocks (Stage 1 output)
print(result.explicit_column_structures)
# [{
#   'cluster_id': 0,
#   'representative': 'Feature_A',
#   'members': ['Feature_A', 'Feature_B'],
#   'nmi_score': 0.89,
# }, ...]

# Cluster profiles (Stage 3 output)
print(result.explicit_row_structures)
# [{
#   'cluster_id': 0,
#   'size': 1234,
#   'mean': [...],
#   'median': [...],
#   'iqr': [...],
# }, ...]

# Latent break detection (Stage 4 output)
print(result.latent_structures)
# {
#   'primary_driver': 'Feature_X' or None,
#   'cutpoint': 0.42 or None,
#   'affected_indices': [...] or None,
#   'p_values': {...},
# }
```

---

## Comparing Multiple Runs

### Use Case: Drift Detection, Stability Validation

```python
from structure_id import compare_structures

# Split data into two subsets
split_idx = len(df) // 2
df_subset_a = df.iloc[:split_idx]
df_subset_b = df.iloc[split_idx:]

# Run structure identification independently
result_a = structure_id(data=df_subset_a, target='y', task_type='classification')
result_b = structure_id(data=df_subset_b, target='y', task_type='classification')

# Compare
comparison = compare_structures(result_a, result_b)

print(comparison)
# {
#   'column_similarity': {
#       'features_a': [...],
#       'features_b': [...],
#       'intersection': [...],
#       'jaccard_index': 1.0,  # 1.0 = identical feature selection
#   },
#   'row_structure_shift': {
#       'clustered_proportion_a': 0.829,
#       'clustered_proportion_b': 0.821,
#       'proportion_shift': 0.008,  # ±0.8%
#   },
#   'latent_structure_agreement': {
#       'primary_driver_a': None,
#       'primary_driver_b': None,
#       'drivers_match': True,
#   }
# }
```

**Interpretation:**
- **Jaccard Index = 1.0:** Perfect feature selection consistency (✓ Good)
- **Proportion Shift < 0.05:** Clustering stability maintained (✓ Good)
- **Drivers Match = True:** Latent patterns consistent (✓ Good)

---

## Troubleshooting

### Issue 1: "ValueError: n_features exceeds n_samples"

```
Error: Cannot perform Gram-Schmidt on 25 features × 10 samples
```

**Cause:** More features than samples (p > n underdetermined)

**Solution:**
```python
# Option 1: Use more samples
if len(df) < df.shape[1]:
    raise ValueError("Insufficient samples for orthogonalization")

# Option 2: Pre-filter features (Stage 0 already does this)
# Option 3: Use principal component analysis (PCA) first
from sklearn.decomposition import PCA
pca = PCA(n_components=min(df.shape) - 1)
df_reduced = pd.DataFrame(pca.fit_transform(df))
result = structure_id(data=df_reduced, target='y', task_type='classification')
```

### Issue 2: "All features marked as redundant"

```
Warning: Stage 1 collapsed all 15 features into 1 representative
```

**Cause:** NMI threshold too high (aggressive collapse)

**Solution:**
```python
config = StructureIDConfig(mutual_information_threshold=0.95)  # Less aggressive
result = structure_id(data=df, target='y', task_type='classification', config=config)
```

### Issue 3: "No clusters found (all instances 'independent')"

```
Info: 0 clusters created; 58170 independent instances
```

**Cause:** HDBSCAN min_cluster_size too large

**Solution:**
```python
config = StructureIDConfig(min_cluster_size=10)  # Lower threshold
result = structure_id(data=df, target='y', task_type='classification', config=config)
```

### Issue 4: "Orthogonal components have non-zero correlation"

```
Warning: Ortho_0 and Ortho_1 correlation = 0.05 (expected ~0)
```

**Cause:** Numerical instability in Gram-Schmidt (rare)

**Solution:**
```python
# Check feature condition number (ill-conditioned data?)
np.linalg.cond(df.iloc[:, :10].values)

# If > 1e12, consider preprocessing:
from sklearn.preprocessing import StandardScaler
df_scaled = pd.DataFrame(StandardScaler().fit_transform(df), columns=df.columns)
result = structure_id(data=df_scaled, target='y', task_type='classification')
```

### Issue 5: "Interpretation report is empty"

```
interp['table'].shape == (0, 2)
```

**Cause:** Threshold too high (filtering all contributors)

**Solution:**
```python
interp = result.get_orthogonal_feature_interpretation_report(
    threshold=0.01  # Lower threshold (1% instead of 5%)
)
```

---

## API Reference

### Main Function: `structure_id()`

```python
def structure_id(
    data: pd.DataFrame,
    target: str,
    task_type: Literal['regression', 'classification'],
    structural_covariates: list[str] | None = None,
    feature_order: list[str] | None = None,
    config: StructureIDConfig | None = None,
) -> StructureResult:
    """
    Identify structure in complex datasets via stateless 4-stage pipeline.
    
    Parameters
    ----------
    data : pd.DataFrame
        Input dataset with mixed dtypes. Automatically handles:
        - Missing values (median-imputes numeric, encodes categorical)
        - Non-numeric columns (excluded)
        - Zero-variance columns (excluded)
    
    target : str
        Target column name (excluded from features).
    
    task_type : {'regression', 'classification'}
        Task type for latent testing (Stage 4).
    
    structural_covariates : list[str], optional
        Columns to exclude from feature analysis.
    
    feature_order : list[str], optional
        Explicit ordering for Gram-Schmidt (order-dependent).
        If None, orders by descending variance.
    
    config : StructureIDConfig, optional
        Configuration object. If None, uses defaults.
    
    Returns
    -------
    StructureResult
        Complete results including:
        - variance_ledger: Accounting summary
        - orthogonal_basis: Decorrelated features + structure_id
        - orthogonal_interpretation: Interpretation report (3 formats)
        - representative_features: Original features + structure_id
        - latent_structures: Break detection results
        - diagnostics: Warnings and dropped columns
    """
```

### Interpretation Method: `get_orthogonal_feature_interpretation_report()`

```python
def get_orthogonal_feature_interpretation_report(
    threshold: float = 0.05,
    include_raw_weights: bool = False,
) -> dict:
    """
    Generate feature interpretation report for orthogonal components.
    
    Parameters
    ----------
    threshold : float, default=0.05
        Contribution percentage threshold (0.0-1.0).
        Contributors below threshold are filtered.
    
    include_raw_weights : bool, default=False
        Include raw weight values in output.
        If False, only percentages shown.
    
    Returns
    -------
    dict
        {
            'table': pd.DataFrame,       # Tabular format
            'structured': dict,          # Dictionary/JSON format
            'summary': pd.DataFrame,     # Summary format
            'metadata': dict,            # Metadata
        }
    """
```

### Comparison Function: `compare_structures()`

```python
def compare_structures(
    result_a: StructureResult,
    result_b: StructureResult,
) -> dict:
    """
    Compare two independent structure_id runs for drift/consistency.
    
    Parameters
    ----------
    result_a, result_b : StructureResult
        Results from independent structure_id() calls.
    
    Returns
    -------
    dict
        {
            'column_similarity': {...},          # Feature selection comparison
            'row_structure_shift': {...},        # Clustering shift
            'latent_structure_agreement': {...}, # Break detection agreement
        }
    """
```

### Configuration: `StructureIDConfig`

```python
@dataclass
class StructureIDConfig:
    """Configuration for structure_id pipeline."""
    
    # Stage 0: Filtering
    missing_threshold: float = 0.3          # Drop if >30% missing
    variance_threshold: float = 1e-6        # Drop if std < threshold
    
    # Stage 1: NMI Clustering
    mutual_information_threshold: float = 0.85  # NMI cutoff
    
    # Stage 3: HDBSCAN Clustering
    min_cluster_size: int = 15              # Minimum cluster size
    min_samples: int | None = None          # HDBSCAN parameter
    
    # Stage 4: Latent Testing
    fluctuation_test_alpha: float = 0.05    # Significance level
```

---

## Real-World Example: SBA Loan Dataset

```python
import pandas as pd
from structure_id import structure_id, compare_structures

# Load dataset
df = pd.read_csv('data/model_ready_numeric_data.csv')
print(f"Loaded {len(df)} rows × {len(df.columns)} columns")

# Run structure identification
result = structure_id(
    data=df,
    target='loan_status_r',
    task_type='classification',
    config={'mutual_information_threshold': 0.85, 'min_cluster_size': 15},
)

# Inspect results
print("\n=== VARIANCE LEDGER ===")
for key, value in result.variance_ledger.items():
    print(f"{key:40s} {value}")

print("\n=== ORTHOGONAL INTERPRETATION (TABULAR) ===")
interp = result.get_orthogonal_feature_interpretation_report()
print(interp['table'])

print("\n=== ORTHOGONAL INTERPRETATION (SUMMARY) ===")
print(interp['summary'])

# Save reports
paths = result.save_reports(output_dir='./reports/')
print(f"\nReports saved to: {paths}")

# Compare on two subsets (drift detection)
split_idx = len(df) // 2
result_a = structure_id(data=df.iloc[:split_idx], target='loan_status_r', task_type='classification')
result_b = structure_id(data=df.iloc[split_idx:], target='loan_status_r', task_type='classification')

comparison = compare_structures(result_a, result_b)
print("\n=== STRUCTURE COMPARISON ===")
print(f"Feature selection consistency (Jaccard): {comparison['column_similarity']['jaccard_index']:.4f}")
print(f"Clustering proportion shift: {comparison['row_structure_shift']['proportion_shift']:.4f}")
print(f"Latent drivers agree: {comparison['latent_structure_agreement']['drivers_match']}")
```

**Expected Output:**
```
Loaded 116341 rows × 22 columns

=== VARIANCE LEDGER ===
total_input_features                    21
provisional_candidate_features          17
features_after_redundancy_collapse      15
orthogonal_basis_dimension              13
clustered_rows                        48247
independent_rows                      9923
n_clusters                              948

=== ORTHOGONAL INTERPRETATION (TABULAR) ===
   Decorrelated Feature        Contributing Raw Features (Ordered by Strength)
0         Ortho_0  +Interest_Rate (62%), -Debt_to_Income (28%), +Loan_Amount (10%)
1         Ortho_1  +Debt_to_Income (51%), -Interest_Rate (35%), +Loan_Amount (14%)
...

=== STRUCTURE COMPARISON ===
Feature selection consistency (Jaccard): 1.0000
Clustering proportion shift: 0.0080
Latent drivers agree: True
```

---

## Summary

| Task | Method | Example |
|------|--------|---------|
| **Run structure ID** | `structure_id()` | `result = structure_id(data=df, target='y', task_type='classification')` |
| **View accounting** | `result.variance_ledger` | `print(result.variance_ledger)` |
| **Get interpretation** | `get_orthogonal_feature_interpretation_report()` | `interp = result.get_orthogonal_feature_interpretation_report()` |
| **View tabular** | `interp['table']` | `print(interp['table'])` |
| **View structured** | `interp['structured']` | `json.dumps(interp['structured'])` |
| **Compare runs** | `compare_structures()` | `compare_structures(result_a, result_b)` |
| **Export reports** | `result.save_reports()` | `result.save_reports(output_dir='./reports/')` |

---

**Need Help?** See [Troubleshooting](#troubleshooting) or check [GRAM_SCHMIDT_INTERPRETATION_GUIDE.md](./GRAM_SCHMIDT_INTERPRETATION_GUIDE.md) for detailed interpretation examples.

