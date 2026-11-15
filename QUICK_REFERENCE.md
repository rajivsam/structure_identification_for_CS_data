# structure_id v2.0 — Quick Reference Card

## Public API Signature

```python
from structure_id import structure_id, compare_structures

result = structure_id(
    data: pd.DataFrame,
    target: str | pd.Series | np.ndarray,
    task_type: Literal["regression", "classification"],
    structural_covariates: list[str] | None = None,
    config: dict | StructureConfig | None = None,
) -> StructureResult

comparison = compare_structures(
    result_a: StructureResult,
    result_b: StructureResult,
) -> ComparisonResult
```

---

## Configuration Defaults

```python
StructureConfig(
    mutual_information_threshold=0.85,      # NMI cutoff for redundancy
    min_cluster_size=15,                    # HDBSCAN minimum
    alpha=0.05,                             # Significance (Bonferroni-adjusted)
    std_threshold=1e-5,                     # Min numeric variance
    max_missing_ratio=0.20,                 # Max missingness
    max_categories=30,                      # Max categorical unique values
    max_class_concentration=0.98,           # Max dominant category
    random_state=42,                        # Deterministic seed
)
```

---

## Pipeline: 4 Stages

| Stage | Input | Output | Key Algorithm |
|-------|-------|--------|---|
| **0: Validation** | Raw DataFrame | l_provisional candidates | Filter variance, missingness, cardinality |
| **1: Redundancy** | Z (l_provisional features) | Z_rep (l representatives) | NMI clustering, highest-variance selection |
| **2: Orthogonalization** | Z_rep (l features) | U (l orthogonal components) | Modified Gram-Schmidt (unnormalized) |
| **3: Clustering** | U (orthogonal matrix) | structure_id column | HDBSCAN: cluster IDs (0,1,...,k) + "independent" |
| **4: Latent Testing** | Y residuals vs Z_rep | latent_structures | Ordered fluctuation test, Bonferroni correction |

---

## Stage 2: Gram-Schmidt Orthogonalization

### Algorithm Overview

1. **Order:** Sort Z_rep by descending variance
2. **Center:** Subtract column means: z̃ = z - z̄
3. **Orthogonalize (Modified):**
   ```
   u₁ = z̃₁
   For j=2..l:
     u_j = z̃_j - Σ(k<j) [⟨z̃_j, u_k⟩/⟨u_k,u_k⟩] * u_k
   ```
4. **Scale:** DO NOT normalize to unit variance (preserve cluster gaps)
5. **Interpret:** Extract W = R⁻¹; compute contributions |W_ij| / Σ|W_kj|

### Tabular Interpretation Report

**Method:**
```python
report = result.get_orthogonal_feature_interpretation_report(
    threshold=0.05,         # minimum 5% contribution to include
    include_raw_weights=False
)
```

**Output Format (report['table']):**

| Decorrelated Feature | Contributing Raw Features (Ordered by Strength) |
|---|---|
| Ortho_Component_0 | `+Feature_A (48%), -Feature_B (32%), +Feature_C (20%)` |
| Ortho_Component_1 | `+Feature_B (51%), -Feature_A (35%), +Feature_C (14%)` |
| Ortho_Component_2 | `+Feature_C (78%), -Feature_A (22%)` |

**Other Formats:**
- `report['structured']` — Nested dict with weights, signs, percentages (JSON-ready)
- `report['summary']` — DataFrame with variance fractions and dominant attribute groups
- `report['metadata']` — Generation info, thresholds, variance accounting

---

## Stage 3: Row Clustering & Instance Labeling

### HDBSCAN Output Mapping

| HDBSCAN Label | structure_id Value | Meaning |
|---|---|---|
| 0, 1, 2, ... | 0, 1, 2, ... (integer) | Dense cluster |
| -1 (noise) | "independent" (string) | Unclustered instance |

### Cluster Profiling

- Statistics computed in **original feature units** (Z_rep, not U)
- Mean, median, IQR per cluster
- Top distinguishing features vs. overall distribution

---

## Stage 4: Latent Heterogeneity Testing

### Fluctuation Test Workflow

1. **Baseline:** Fit model predicting Y from structural_covariates (or intercept-only)
2. **Residuals:** Extract e = Y - Ŷ
3. **For each feature z ∈ Z_rep:**
   - Sort e by ascending z
   - Compute cumulative process W_n(t)
   - Test statistic: λ = max|W_n(t)|
   - P-value: asymptotic Brownian bridge
4. **Bonferroni:** p_adj = min(p_raw × l, 1.0) where l = |Z_rep|
5. **Selection:** Primary driver = min p_adj; record cutpoint in original z units

---

## StructureResult Output

### Main Attributes

```python
result.variance_ledger          # dict: accounting summary
result.explicit_column_structures  # list[FeatureBlock]: redundancy info
result.orthogonal_basis         # DataFrame: U + structure_id column
result.orthogonal_interpretation  # dict: from get_orthogonal_feature_interpretation_report()
result.representative_features  # DataFrame: Z_rep + structure_id column
result.explicit_row_structures  # list[RowClusterProfile]: cluster summaries
result.latent_structures        # LatentBreakResult: fluctuation test results
result.diagnostics              # dict: dropped columns, warnings, config
result.report_markdown          # str: narrative summary
```

### Methods

```python
result.get_orthogonal_feature_interpretation_report(
    threshold=0.05,
    include_raw_weights=False
) → dict[str, Any]

result.to_html() → str

result.save_reports(output_dir: str | Path) → dict[str, Path]
```

---

## Variance Ledger Structure

```python
{
    'total_features': 15,              # Z (after Stage 0)
    'dropped_redundant_features': 3,   # Redundant to representatives
    'independent_basis_features': 12,  # Z_rep = l (after Stage 1)
    'total_rows': 1000,
    'clustered_rows': 850,             # Assigned to cluster 0..k-1
    'independent_rows': 150,           # HDBSCAN noise → "independent"
    'n_clusters': 5,                   # Valid clusters (0..4)
    'latent_break_detected': True,     # Any feature pass Bonferroni?
}
```

---

## Comparison Utility

```python
comparison = compare_structures(result_a, result_b)

comparison.column_similarity          # Jaccard of Z_rep sets
comparison.row_structure_shift        # Δ in cluster proportions
comparison.latent_structure_agreement # Same primary driver?
```

---

## Key Design Decisions

1. **Stateless:** No fitted state stored; each run is independent
2. **Unnormalized Gram-Schmidt:** No unit-variance rescaling → preserves cluster geometry
3. **Original Units for Latent Tests:** Fluctuation testing uses Z_rep (not U) for direct interpretation
4. **"independent" String Label:** Human-readable vs. numeric -1
5. **Bonferroni on Full Feature Count:** Adjust for all l features tested, not just those with low p-values

---

## Edge Cases & Handling

| Case | Detected In | Behavior |
|------|-------------|----------|
| Perfect multicollinearity | Stage 1 | Select highest-variance representative |
| Zero-variance columns | Stage 0 | Drop before processing |
| All rows independent | Stage 3 | n_clusters = 0, all labeled "independent" |
| No latent breaks | Stage 4 | primary_driver = None, latent_break_detected = False |
| p > n (wide data) | After Stage 1 | Raise ValueError ("underdetermined orthogonalization") |

---

## Documentation Map

| Document | Purpose | Audience |
|---|---|---|
| [structure_identification_requirements.md](./structure_identification_requirements.md) | Specification (v2.0) | Developers, architects |
| [GRAM_SCHMIDT_INTERPRETATION_GUIDE.md](./GRAM_SCHMIDT_INTERPRETATION_GUIDE.md) | Practical interpretation | Data scientists, analysts |
| [TABULAR_REPORTING_SPECIFICATION.md](./TABULAR_REPORTING_SPECIFICATION.md) | API specification | Implementation team |
| [REFACTORING_SUMMARY.md](./REFACTORING_SUMMARY.md) | Change log v1.0→v2.0 | Project stakeholders |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | This card | Everyone |

---

## Example Workflow

```python
import pandas as pd
from structure_id import structure_id

# 1. Load data (assumed cleaned & featurized)
df = pd.read_csv('data.csv')

# 2. Run structure identification
result = structure_id(
    data=df,
    target='loan_status',
    task_type='classification',
    config={'mutual_information_threshold': 0.85}
)

# 3. Inspect variance accounting
print(result.variance_ledger)
#  {
#    'total_features': 15,
#    'dropped_redundant_features': 3,
#    'independent_basis_features': 12,
#    'clustered_rows': 850,
#    'independent_rows': 150,
#    'n_clusters': 5,
#    ...
#  }

# 4. Interpret orthogonalized features
interp = result.get_orthogonal_feature_interpretation_report()
print(interp['table'])
#    Decorrelated Feature  Contributing Raw Features (Ordered by Strength)
# 0  Ortho_Component_0    +Feature_X (62%), -Feature_Y (28%), ...

# 5. Examine cluster composition
for cluster_id, profile in enumerate(result.explicit_row_structures):
    print(f"Cluster {cluster_id}: {profile.n_rows} rows, top features: {profile.distinguishing_features}")

# 6. Check for latent breaks
if result.latent_structures.primary_driver:
    print(f"Primary structural break: {result.latent_structures.primary_driver}")
    print(f"Cutpoint: {result.latent_structures.cutpoint}")

# 7. Export reports
paths = result.save_reports(output_dir='reports/')
print(f"Saved: {paths}")
```

---

## Testing Checklist

- [ ] Orthogonal columns have pairwise correlation ≈ 0
- [ ] Linear combinations using reported weights reconstruct U
- [ ] Percentages sum to 100% per component
- [ ] Features ordered by descending |weight| in tabular report
- [ ] Threshold filtering removes sub-5% contributors
- [ ] Variance summary sums to ≈ 1.0
- [ ] Row structure_id column has integers 0..k and strings "independent"
- [ ] Redundant features correctly identified and collapsed
- [ ] HDBSCAN clustering produces expected cluster count
- [ ] Fluctuation test correctly applies Bonferroni correction

---

## Performance Notes

- **Typical Datasets:** Runs in seconds to minutes for <100 features, <100k rows
- **Wide Datasets (p > n):** Raises error after Stage 1; not supported
- **Memory:** Stores full Z_rep, U, and W matrices; scales with features² for NMI computation
- **Parallel Opportunity:** Stage 1 NMI pairwise computation can be parallelized

---

## Common Mistakes to Avoid

❌ **Don't** rescale orthogonalized features to unit variance (breaks cluster geometry)  
❌ **Don't** use orthogonalized features for latent break testing (use original Z_rep)  
❌ **Don't** refit on validation/test data (stateless design; rerun structure_id independently)  
❌ **Don't** skip Stage 0 filtering (missing/invariant columns cause issues downstream)  
❌ **Don't** confuse "independent" string label with numeric -1 or missing values  

✅ **Do** use orthogonalized U for clustering (multicollinearity-free)  
✅ **Do** report cluster stats in original feature units (interpretable to stakeholders)  
✅ **Do** run compare_structures on independent structure_id() results (stateless comparison)  
✅ **Do** preserve the interpretation report for documentation  
✅ **Do** validate on actual data to ensure domain assumptions hold  

---

**Last Updated:** 2026-11-15 | **Version:** 2.0 | **Status:** Ready for Implementation
