# Structure_ID v2.0 Quick Start Guide

## Installation

```bash
cd structure_identification_for_CS_data
source .venv/bin/activate
# Dependencies already installed: pandas, numpy, scipy, scikit-learn, hdbscan
```

## Basic Usage

```python
from structure_id import structure_id, StructureIDConfig
import pandas as pd

# Load data
data = pd.read_csv('data/model_ready_numeric_data.csv')

# Create config (optional - uses defaults if omitted)
config = StructureIDConfig(
    mutual_information_threshold=0.85,  # NMI threshold for redundancy collapse
    min_cluster_size=15,                # HDBSCAN minimum cluster size
    alpha=0.05,                         # Significance level for latent tests
)

# Run complete pipeline
result = structure_id(
    data,
    target='loan_status_r',    # Target column
    task_type='regression',     # or 'classification'
    config=config
)
```

## Accessing Results

```python
# Variance accounting
print(result.variance_ledger)
# {
#   'total_input_features': 21,
#   'provisional_candidate_features': 17,
#   'features_after_redundancy_collapse': 15,
#   'dropped_redundant_features': 2,
#   'orthogonal_basis_dimension': 13,
#   'n_clusters': 84,
#   'clustered_rows': 4064,
#   'independent_rows': 936,
#   ...
# }

# Orthogonalized features (Stage 2 output)
print(result.orthogonal_basis.head())
# Ortho_0  Ortho_1  Ortho_2  ...  Ortho_12  structure_id
# [orthogonal matrix] ... 0 or "independent"

# Representative features (Stage 1 survivors)
print(result.representative_features.shape)
# (5000, 16) - 15 features + structure_id column

# Row clusters (Stage 3 output)
for cluster in result.explicit_row_structures[:3]:
    print(f"Cluster {cluster['cluster_id']}: {cluster['size']} rows")
# Cluster 0: 16 rows
# Cluster 1: 60 rows
# Cluster 2: 70 rows

# Latent structure (Stage 4 output)
print(result.latent_structures)
# {
#   'primary_driver': None or 'feature_name',
#   'cutpoint': None or float_value,
#   'latent_break_detected': False or True,
# }
```

## Feature Interpretation

```python
# Get formatted interpretation report
report = result.get_orthogonal_feature_interpretation_report()

# Table: Component contributions
print(report['table'])
#    Decorrelated Feature       Contributing Raw Features
# 0             Ortho_0  +grossapproval (100.0%)
# 1             Ortho_1  +jobssupported (65%), -businessage (35%)
# ...

# Summary: Variance per component
print(report['summary'])
#   Component ID Component Name  Retained Variance  Top Driver
# 0            0        Ortho_0   ...              grossapproval
# ...

# Structured: Dictionary mapping
print(report['structured'])
# {
#   'Ortho_0': {
#     'contributors': [...],
#     'contribution_string': '...',
#     'retained_variance': ...
#   },
#   ...
# }
```

## Generating Reports

```python
# Save HTML and CSV reports
result.save_reports('reports/')
# Saves:
#   - structure_report.html
#   - orthogonal_interpretation.csv
#   - component_summary.csv
#   - orthogonal_basis.csv
#   - representative_features.csv

# Generate HTML directly
html = result.to_html()
with open('my_report.html', 'w') as f:
    f.write(html)
```

## Comparing Two Runs

```python
from structure_id import compare_structures

# Run on two datasets
result_a = structure_id(data_subset_a, 'target', 'regression')
result_b = structure_id(data_subset_b, 'target', 'regression')

# Compare structures
comparison = compare_structures(result_a, result_b)

# Column similarity (Jaccard index)
print(f"Jaccard: {comparison['column_similarity']['jaccard_index']:.3f}")
# Closer to 1.0 = more similar features selected

# Row structure shift
print(f"Clustered %: A={comparison['row_structure_shift']['clustered_proportion_a']:.1%}, "
      f"B={comparison['row_structure_shift']['clustered_proportion_b']:.1%}")

# Latent structure agreement
if comparison['latent_structure_agreement']['drivers_match']:
    print("✓ Same latent driver detected")
else:
    print("✗ Different or missing latent drivers")
```

## Running Tests

```bash
# Run all tests
pytest tests/test_structure_id_v2.py -v

# Run specific test
pytest tests/test_structure_id_v2.py::test_stage2_orthogonality -v

# Expected: 31 PASSED tests
```

## Key Parameters

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `mutual_information_threshold` | 0.85 | [0, 1] | NMI cutoff for feature clustering |
| `min_cluster_size` | 15 | > 0 | HDBSCAN minimum cluster size |
| `alpha` | 0.05 | (0, 1] | Significance level for latent tests |
| `std_threshold` | 1e-5 | > 0 | Minimum variance to retain feature |
| `max_missing_ratio` | 0.20 | [0, 1] | Maximum missingness per column |
| `max_categories` | 30 | > 0 | Maximum unique values per categorical |
| `max_class_concentration` | 0.98 | [0, 1] | Maximum dominant class proportion |

## Output Structure

```
result: StructureResult
├── target                          # Target column name
├── task_type                       # "regression" or "classification"
├── variance_ledger                 # Feature/row accounting dict
├── explicit_column_structures      # Stage 1: Redundancy info
├── orthogonal_basis                # Stage 2: Ortho features + structure_id
├── orthogonal_interpretation       # Stage 2: Formatted report
├── representative_features         # Stage 1: Survivors + structure_id
├── explicit_row_structures         # Stage 3: Cluster profiles
├── latent_structures              # Stage 4: Latent break info
└── diagnostics                     # All stage diagnostics
```

## Common Patterns

### Pattern 1: Standard Analysis
```python
result = structure_id(data, 'target', 'regression')
print(f"Found {len(result.explicit_row_structures)} clusters")
print(f"Orthogonal components: {result.variance_ledger['orthogonal_basis_dimension']}")
report = result.get_orthogonal_feature_interpretation_report()
result.save_reports('output/')
```

### Pattern 2: Batch Processing
```python
config = StructureIDConfig(min_cluster_size=20)
results = {}

for subset_name in ['train', 'test', 'validation']:
    subset_data = data[data['partition'] == subset_name]
    results[subset_name] = structure_id(subset_data, 'target', 'regression', config=config)

# Compare results
comparison = compare_structures(results['train'], results['test'])
```

### Pattern 3: Feature Selection
```python
# Get recommended features
rep_features = result.representative_features.columns.tolist()
rep_features.remove('structure_id')
print(f"Use these {len(rep_features)} features: {rep_features}")

# For ML model
X = result.orthogonal_basis[[c for c in result.orthogonal_basis.columns if c.startswith('Ortho_')]]
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "No valid candidate features survived" | Too many columns dropped | Relax `std_threshold`, `max_missing_ratio` |
| "Cannot create writable memory view" | Old hdbscan version | Update: `pip install --upgrade hdbscan` |
| Very slow Stage 1 | Many features | Increase `mutual_information_threshold` |
| All rows "independent" | Features too noisy | Increase `min_cluster_size` |
| Orthogonal columns still correlated | Numerical instability | Reduce precision requirements in tests |

## Documentation

- **Full Technical Spec:** `structure_identification_requirements.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY_V2.md`
- **Completion Report:** `IMPLEMENTATION_COMPLETE.md`
- **Test Suite:** `tests/test_structure_id_v2.py` (31 tests, well-documented)

---

**For production use, see IMPLEMENTATION_COMPLETE.md**
