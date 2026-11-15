# Tabular Reporting Specification: Orthogonal Feature Interpretation

## Overview

The `StructureResult` object must include a method `get_orthogonal_feature_interpretation_report()` that returns a comprehensive, analyst-ready mapping of how original features combine to form orthogonalized components.

This document specifies the **exact tabular format** and supporting data structures for this reporting interface.

---

## Method Signature

```python
class StructureResult:
    def get_orthogonal_feature_interpretation_report(
        self,
        threshold: float = 0.05,
        include_raw_weights: bool = False,
    ) -> dict[str, Any]:
        """
        Generate interpretable feature attribution report for orthogonalized components.
        
        Parameters
        ----------
        threshold : float, default 0.05
            Minimum relative contribution (as fraction) to include in the report.
            Contributors below this threshold are filtered out.
        include_raw_weights : bool, default False
            If True, include raw weight values (not just percentages) in structured output.
        
        Returns
        -------
        dict[str, Any]
            Dictionary with keys:
            - 'table': pd.DataFrame (tabular view)
            - 'structured': dict (structured/JSON-ready format)
            - 'summary': pd.DataFrame (variance summary)
            - 'metadata': dict (auxiliary info: threshold, n_components, etc.)
        """
```

---

## Output Format 1: Tabular (`report['table']`)

### Schema

```python
import pandas as pd

table = pd.DataFrame({
    'Decorrelated Feature': [str, ...],
    'Contributing Raw Features (Ordered by Strength)': [str, ...],
})
```

### Column Definitions

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `Decorrelated Feature` | str | Name of the orthogonalized component | `"Ortho_Component_0"` or `"Component_1"` |
| `Contributing Raw Features (Ordered by Strength)` | str | Formatted string of contributors, ordered descending by absolute weight, with sign and percentage | `"+Feature_A (48%), -Feature_B (32%), +Feature_C (20%)"` |

### Formatting Rules

1. **Component Names:** Use format `"Ortho_Component_{i}"` where i is 0-indexed position
2. **Feature Ordering:** Sort contributors by absolute weight (highest first)
3. **Sign Convention:**
   - `"+"` prefix if coefficient is positive
   - `"-"` prefix if coefficient is negative
4. **Percentage Format:**
   - Each contributor shown as `FeatureName (XX.X%)` or `FeatureName (XX%)` rounded to 1 decimal place
   - Percentages sum to 100% per component (after threshold filtering)
5. **Threshold Filtering:** Omit contributors with |weight| / Σ|weights| < threshold (default 5%)
6. **Separator:** Comma-space `", "` between contributors
7. **No Line Wrapping:** Keep full string in single cell (let display layer handle wrapping)

### Example Output

```
                 Decorrelated Feature                                    Contributing Raw Features (Ordered by Strength)
0           Ortho_Component_0           +Feature_loan_amount (62.0%), -Feature_annual_revenue (28.0%), +Feature_employees (10.0%)
1           Ortho_Component_1                  +Feature_annual_revenue (51.0%), -Feature_loan_amount (35.0%), +Feature_credit_score (14.0%)
2           Ortho_Component_2                              +Feature_credit_score (78.0%), -Feature_age (22.0%)
3           Ortho_Component_3                                +Feature_sector__manufacturing (100.0%)
```

### Export Options

```python
# CSV export
report['table'].to_csv('ortho_interpretation.csv', index=False)

# Excel export
report['table'].to_excel('ortho_interpretation.xlsx', index=False, sheet_name='Orthogonal Features')

# Markdown export (for documentation)
print(report['table'].to_markdown(index=False))
```

---

## Output Format 2: Structured Dictionary (`report['structured']`)

### Schema

```python
structured = {
    "Ortho_Component_0": {
        "component_index": 0,
        "n_contributors": 3,
        "contributors": [
            {
                "feature": "Feature_loan_amount",
                "weight": 0.62,
                "sign": "+",
                "percentage": 62.0,
            },
            {
                "feature": "Feature_annual_revenue",
                "weight": -0.28,
                "sign": "-",
                "percentage": 28.0,
            },
            {
                "feature": "Feature_employees",
                "weight": 0.10,
                "sign": "+",
                "percentage": 10.0,
            },
        ],
    },
    "Ortho_Component_1": { ... },
    ...
}
```

### Key Details

- **component_index:** 0-based position in orthogonalization
- **n_contributors:** Count of features after threshold filtering
- **contributors:** List of contributor objects, sorted by descending |weight|
  - **feature:** Original feature name (as string)
  - **weight:** Raw coefficient (signed float, not normalized)
  - **sign:** String "+" or "-" derived from sign of weight
  - **percentage:** Normalized percentage, computed as |weight| / Σ|weights| × 100

### JSON Serialization

```python
import json

json_str = json.dumps(report['structured'], indent=2)
print(json_str)

# Can also be saved to file
with open('ortho_interpretation.json', 'w') as f:
    json.dump(report['structured'], f, indent=2)
```

---

## Output Format 3: Summary (`report['summary']`)

### Schema

```python
summary = pd.DataFrame({
    'Component ID': [str, ...],
    'Retained Variance': [float, ...],
    'Dominant Attribute Group': [str, ...],
    'Top Driver': [str, ...],
})
```

### Column Definitions

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `Component ID` | str | Component name | `"Ortho_Component_0"` |
| `Retained Variance` | float | Fraction of variance explained by this component (0-1) | `0.45` |
| `Dominant Attribute Group` | str | Human-readable label of primary driver(s) | `"Loan-Amount-led"` or `"Revenue-&-Scale"` |
| `Top Driver` | str | Single feature with highest absolute weight | `"Feature_loan_amount"` |

### Variance Calculation

Retained variance for component i:
$$\text{Var}_i = \frac{\text{Var}(U_i)}{\sum_j \text{Var}(U_j)}$$

where U_i is the i-th column of the orthogonalized matrix, and variance is computed over all rows.

### Dominant Attribute Group Labeling

Create a human-readable label combining the top 1–3 contributors:

```python
# Pseudocode
if n_contributors >= 3:
    top_3_features = contributors[:3]
    label = " & ".join([f["feature"].replace("Feature_", "") for f in top_3_features])
    label = label + "-group"
else:
    top_feature = contributors[0]["feature"].replace("Feature_", "")
    label = top_feature + "-led"

return label
```

**Examples:**
- `"Loan_Amount & Annual_Revenue & Credit_Score-group"`
- `"Annual_Revenue-led"`
- `"Credit_Score-led"`

### Example Output

```
              Component ID  Retained Variance   Dominant Attribute Group             Top Driver
0           Ortho_Component_0            0.4510   Loan_Amount & Revenue & Employees   Feature_loan_amount
1           Ortho_Component_1            0.2801   Annual_Revenue & Loan_Amount       Feature_annual_revenue
2           Ortho_Component_2            0.1805   Credit_Score & Age                 Feature_credit_score
3           Ortho_Component_3            0.0884   Sector_Manufacturing               Feature_sector__manufacturing
```

---

## Output Format 4: Metadata (`report['metadata']`)

### Schema

```python
metadata = {
    "n_components": 4,
    "n_original_features": 6,
    "threshold": 0.05,
    "total_variance_explained": 1.0,
    "generation_timestamp": "2026-11-15T06:03:47.692+05:30",
    "include_raw_weights": False,
    "algorithm": "Modified Gram-Schmidt (Unnormalized QR Decomposition)",
}
```

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `n_components` | int | Number of orthogonal components (= l, post-Stage 1) |
| `n_original_features` | int | Number of features after Stage 1 redundancy collapse |
| `threshold` | float | Contribution threshold used for filtering |
| `total_variance_explained` | float | Sum of all retained variances (should be ≈ 1.0) |
| `generation_timestamp` | str | ISO 8601 timestamp when report was generated |
| `include_raw_weights` | bool | Whether raw weights are included in structured output |
| `algorithm` | str | Description of orthogonalization method |

---

## Complete Example Return Value

```python
report = result.get_orthogonal_feature_interpretation_report(threshold=0.05)

# Structure
{
    'table': pd.DataFrame(...),
    'structured': {
        'Ortho_Component_0': {...},
        'Ortho_Component_1': {...},
        ...
    },
    'summary': pd.DataFrame(...),
    'metadata': {
        'n_components': 4,
        'n_original_features': 6,
        'threshold': 0.05,
        'total_variance_explained': 1.0,
        'generation_timestamp': '2026-11-15T06:03:47.692+05:30',
        'include_raw_weights': False,
        'algorithm': 'Modified Gram-Schmidt (Unnormalized QR Decomposition)',
    }
}
```

---

## Integration Points

### 1. **StructureResult Class**

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class StructureResult:
    variance_ledger: dict
    explicit_column_structures: list
    orthogonal_basis: pd.DataFrame
    orthogonal_interpretation: dict  # <-- This should match report['structured']
    representative_features: pd.DataFrame
    explicit_row_structures: list
    latent_structures: Any
    diagnostics: dict
    report_markdown: str
    
    def get_orthogonal_feature_interpretation_report(
        self,
        threshold: float = 0.05,
        include_raw_weights: bool = False,
    ) -> dict[str, Any]:
        """Generate interpretation report (see this spec)."""
        # Implementation returns { 'table', 'structured', 'summary', 'metadata' }
```

### 2. **Reporting Module**

The module `structure_id/reporting.py` should expose:

```python
def generate_orthogonal_interpretation(
    weight_matrix: np.ndarray,
    feature_names: list[str],
    orthogonal_matrix: np.ndarray,
    threshold: float = 0.05,
    include_raw_weights: bool = False,
) -> dict[str, Any]:
    """
    Core function to compute the interpretation report from weight matrix W.
    
    This is called by StructureResult.get_orthogonal_feature_interpretation_report().
    """
```

### 3. **Exports & Convenience**

```python
# In StructureResult or reporting.py
def export_interpretation_table(
    report: dict,
    output_path: str | Path,
    format: Literal['csv', 'excel', 'markdown', 'json'] = 'csv',
) -> Path:
    """Export interpretation report to various formats."""
```

---

## Display & Visualization

### Jupyter / IPython Display

```python
# Auto-render as pretty table in Jupyter
from IPython.display import display
display(report['table'])

# Or Markdown
from IPython.display import Markdown
display(Markdown(report['table'].to_markdown(index=False)))
```

### Terminal Display

```python
# Simple text table
print(report['table'].to_string(index=False))

# Or with nice formatting library
from tabulate import tabulate
print(tabulate(report['table'], headers='keys', tablefmt='grid'))
```

### HTML Export

```python
# Standalone HTML table
html = report['table'].to_html(index=False)

# Or embed in markdown for documentation
markdown_html = f"""
# Orthogonal Feature Interpretation

{report['table'].to_markdown(index=False)}

## Variance Summary

{report['summary'].to_markdown(index=False)}
"""
```

---

## Implementation Checklist

- [ ] Implement `get_orthogonal_feature_interpretation_report()` in `StructureResult`
- [ ] Extract weight matrix W during Stage 2 (Modified Gram-Schmidt)
- [ ] Compute percentage contributions: `|W_ij| / Σ_k |W_kj|`
- [ ] Format tabular string: `"+Feature_X (YY.Y%), -Feature_Z (XX.X%)"`
- [ ] Build structured dictionary with 'feature', 'weight', 'sign', 'percentage' per contributor
- [ ] Compute variance fractions for summary: `Var(U_i) / Var(U_total)`
- [ ] Generate human-readable attribute group labels
- [ ] Return dict with keys: 'table', 'structured', 'summary', 'metadata'
- [ ] Add `export_interpretation_table()` convenience function
- [ ] Include method in docstrings with examples
- [ ] Add tests verifying:
  - Percentages sum to 100% per component
  - Features ordered by descending |weight|
  - Threshold filtering removes sub-5% contributors
  - Variance summary sums to ≈ 1.0

---

## Testing Guidance

### Unit Test: Percentage Normalization

```python
def test_interpretation_percentages_sum_to_100():
    report = result.get_orthogonal_feature_interpretation_report()
    
    for component_name, contributors in report['structured'].items():
        percentages = [c['percentage'] for c in contributors['contributors']]
        assert abs(sum(percentages) - 100.0) < 0.1  # allow floating-point tolerance
```

### Unit Test: Feature Ordering

```python
def test_interpretation_features_ordered_by_strength():
    report = result.get_orthogonal_feature_interpretation_report()
    
    for component_name, contributors in report['structured'].items():
        weights = [abs(c['weight']) for c in contributors['contributors']]
        assert weights == sorted(weights, reverse=True)  # descending order
```

### Unit Test: Threshold Filtering

```python
def test_interpretation_threshold_filtering():
    report = result.get_orthogonal_feature_interpretation_report(threshold=0.05)
    
    for component_name, contributors in report['structured'].items():
        for contributor in contributors['contributors']:
            assert contributor['percentage'] >= 5.0  # all above threshold
```

### Integration Test: Reconstruction

```python
def test_interpretation_weights_reconstruct_orthogonal():
    report = result.get_orthogonal_feature_interpretation_report()
    
    # Verify: U = X_centered @ W
    U_reconstructed = X_centered @ weight_matrix
    assert_allclose(U_reconstructed, result.orthogonal_basis.values)
```

---

## Example Usage Scenarios

### Scenario 1: Analyst Exports Report to CSV

```python
result = structure_id(data=df, target='y', task_type='regression')
report = result.get_orthogonal_feature_interpretation_report()

# Export for stakeholder review
report['table'].to_csv('ortho_features.csv', index=False)
report['summary'].to_csv('ortho_variance_summary.csv', index=False)
```

### Scenario 2: Data Scientist Interprets Component

```python
report = result.get_orthogonal_feature_interpretation_report()

# Query: Which original features drive Ortho_Component_1?
component_key = 'Ortho_Component_1'
contributors = report['structured'][component_key]['contributors']

for c in contributors:
    print(f"{c['feature']:30} {c['sign']}{c['percentage']:6.1f}%")

# Output:
# Feature_annual_revenue          +51.0%
# Feature_loan_amount             -35.0%
# Feature_credit_score            +14.0%
```

### Scenario 3: Documentation Generation

```python
import json

report = result.get_orthogonal_feature_interpretation_report()

# Write markdown report with embedded tables and JSON
with open('STRUCTURE_REPORT.md', 'w') as f:
    f.write("# Feature Structure Report\n\n")
    f.write("## Orthogonal Feature Composition\n\n")
    f.write(report['table'].to_markdown(index=False))
    f.write("\n\n## Variance Summary\n\n")
    f.write(report['summary'].to_markdown(index=False))
    f.write("\n\n## Detailed Weights (JSON)\n\n")
    f.write("```json\n")
    f.write(json.dumps(report['structured'], indent=2))
    f.write("\n```\n")
```

---

## Performance Considerations

- **Computation:** O(l × p) where l = number of components, p = number of original features
- **Memory:** Dict with l components × p features = manageable for typical datasets
- **Caching:** Pre-compute and store in `StructureResult.orthogonal_interpretation` during pipeline execution to avoid recomputation

