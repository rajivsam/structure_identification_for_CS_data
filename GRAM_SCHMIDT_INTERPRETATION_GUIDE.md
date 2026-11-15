# Gram-Schmidt Orthogonalization Interpretation Guide

## Overview

After Stage 2 of the `structure_id` pipeline completes, you have:
- **U**: An orthogonalized feature matrix (linearly independent, near-zero pairwise correlation)
- **W**: A weight matrix encoding the exact linear combinations of original features that form each orthogonal component
- **Interpretation Report**: Tabular, structured, and summary representations of how original features map to orthogonal components

---

## The Tabular Interpretation Format

This is the primary interface for analysts to understand orthogonal feature composition.

### Table Structure

| Decorrelated Feature | Contributing Raw Features (Ordered by Strength) |
|---|---|
| `Ortho_Component_0` | `+Feature_loan_amount (62%), -Feature_annual_revenue (28%), +Feature_employees (10%)` |
| `Ortho_Component_1` | `+Feature_annual_revenue (51%), -Feature_loan_amount (35%), +Feature_credit_score (14%)` |
| `Ortho_Component_2` | `+Feature_credit_score (78%), -Feature_age (22%)` |

### Interpretation

**Row 1 example:**
- **Decorrelated Feature:** `Ortho_Component_0` (1st orthogonalized component from Modified Gram-Schmidt)
- **Composition:** 
  - **+62%** from `Feature_loan_amount` (positive contribution)
  - **-28%** from `Feature_annual_revenue` (negative/inverse contribution)
  - **+10%** from `Feature_employees` (positive contribution)
- **Meaning:** Ortho_Component_0 is dominated by loan amount, partially offset by annual revenue. It captures size/scale primarily.

**Row 2 example:**
- **Decorrelated Feature:** `Ortho_Component_1` (2nd orthogonalized component)
- **Composition:**
  - **+51%** from `Feature_annual_revenue` (primary driver)
  - **-35%** from `Feature_loan_amount` (offset effect)
  - **+14%** from `Feature_credit_score` (minor driver)
- **Meaning:** Ortho_Component_1 captures revenue effects after loan amount is accounted for. It isolates revenue-specific variance.

**Row 3 example:**
- **Decorrelated Feature:** `Ortho_Component_2` (3rd orthogonalized component)
- **Composition:**
  - **+78%** from `Feature_credit_score` (dominant)
  - **-22%** from `Feature_age` (inverse effect)
- **Meaning:** Ortho_Component_2 is primarily credit-driven with an age offset (older applicants → lower credit effect, or vice versa).

---

## Understanding the Weight Matrix W

The tabular interpretation is derived from the weight matrix **W = R⁻¹**, where R is from QR decomposition:

$$U = X_{\text{centered}} \cdot W$$

**Column j of W** contains the coefficients used to combine original features into orthogonal component j:

```
W[:, 0] = [w₁, w₂, w₃, ...]  # coefficients for Ortho_Component_0
W[:, 1] = [v₁, v₂, v₃, ...]  # coefficients for Ortho_Component_1
...
```

### Percentage Contribution

Each entry in the tabular report is computed as:

$$\text{Contribution}_{i,j} = \frac{|W_{i,j}|}{\sum_k |W_{k,j}|} \times 100\%$$

- **Absolute values** ensure magnitude/strength is captured (negative coefficients still contribute strength)
- **Normalized by sum** creates percentage shares summing to 100% per component
- **Threshold filtering** removes negligible contributors below 5% (configurable)

### Sign Convention

- **+** in the table means the feature's coefficient is positive (in the same direction as the orthogonal component)
- **-** in the table means the feature's coefficient is negative (in the opposite direction)

**Example:**
```python
W[Feature_loan_amount, Ortho_Component_0] = +0.62  # positive coefficient → "+" sign
W[Feature_annual_revenue, Ortho_Component_0] = -0.28  # negative coefficient → "-" sign
```

---

## Multiple Output Formats Available

The `get_orthogonal_feature_interpretation_report()` method returns three complementary formats:

### Format 1: Tabular (Pandas DataFrame)

```python
report = result.get_orthogonal_feature_interpretation_report()
print(report['table'])
#
# Output:
#                Decorrelated Feature          Contributing Raw Features (Ordered by Strength)
# 0         Ortho_Component_0  +Feature_loan_amount (62%), -Feature_annual_revenue (28%), +Feature_employees (10%)
# 1         Ortho_Component_1  +Feature_annual_revenue (51%), -Feature_loan_amount (35%), +Feature_credit_score (14%)
# 2         Ortho_Component_2  +Feature_credit_score (78%), -Feature_age (22%)
```

**Use case:** Analyst-friendly reporting, export to CSV/Excel, presentation materials

---

### Format 2: Structured Dictionary/JSON

```python
report = result.get_orthogonal_feature_interpretation_report()
print(report['structured'])
#
# Output:
# {
#   "Ortho_Component_0": {
#     "contributors": [
#       {
#         "feature": "Feature_loan_amount",
#         "weight": 0.62,
#         "sign": "+",
#         "percentage": 62.0
#       },
#       {
#         "feature": "Feature_annual_revenue",
#         "weight": -0.28,
#         "sign": "-",
#         "percentage": 28.0
#       },
#       {
#         "feature": "Feature_employees",
#         "weight": 0.10,
#         "sign": "+",
#         "percentage": 10.0
#       }
#     ]
#   },
#   "Ortho_Component_1": { ... },
#   ...
# }
```

**Use case:** Programmatic access, machine-readable for downstream pipelines, API responses

---

### Format 3: Summary DataFrame

```python
report = result.get_orthogonal_feature_interpretation_report()
print(report['summary'])
#
# Output:
#  Component ID  Retained Variance  Dominant Attribute Group        Top Driver
# Ortho_Component_0            0.45   Feature_loan_amount-led        Feature_loan_amount
# Ortho_Component_1            0.28   Feature_annual_revenue-led     Feature_annual_revenue
# Ortho_Component_2            0.18   Feature_credit_score-led       Feature_credit_score
# Ortho_Component_3            0.09   Feature_age-led                Feature_age
```

**Use case:** Quick variance summary, identifying which component captures what information, variance decomposition

---

## Why This Matters for Downstream Analysis

### 1. **Feature Interpretation**
- Each orthogonal component has a clear human-readable interpretation in terms of original features
- Analysts understand what each orthogonalized basis vector "represents" in business terms

### 2. **Cluster Profiling**
- Stage 3 uses orthogonal features for density clustering (HDBSCAN)
- Stage 3 reports cluster statistics in **original feature units** (not orthogonalized)
- But you now know which orthogonal components distinguish clusters (via the interpretation table)

### 3. **Latent Heterogeneity Detection**
- Stage 4 scans for structural breaks along **original features** (not orthogonalized)
- The interpretation table helps you understand which combinations of original features are involved in breaks

### 4. **Model Building**
- Downstream models can use either:
  - **Orthogonalized features U** (multicollinearity-free, but less interpretable)
  - **Original features Z_rep** (interpretable, but potentially overlapping)
  - **Hybrid:** Key orthogonal components + selective original features (best of both)

---

## Worked Example: SBA Loan Data

Suppose `structure_id()` runs on SBA loan application data:

```
Raw Features: loan_amount, annual_revenue, employees, credit_score, age, sector
After Stage 1 (redundancy): loan_amount, annual_revenue, employees, credit_score, age, sector (no redundancy)
```

**Modified Gram-Schmidt (Stage 2) orders by variance:**
1. `annual_revenue` (highest variance)
2. `loan_amount`
3. `credit_score`
4. `employees`
5. `age`
6. `sector` (categorical, one-hot encoded)

**Orthogonalization weights (simplified example):**

| Feature | Ortho_0 | Ortho_1 | Ortho_2 | Ortho_3 |
|---------|---------|---------|---------|---------|
| annual_revenue | +0.45 | +0.82 | -0.05 | +0.02 |
| loan_amount | +0.35 | -0.12 | +0.78 | -0.08 |
| credit_score | +0.10 | +0.05 | +0.15 | +0.91 |
| employees | +0.08 | +0.02 | +0.08 | -0.02 |
| age | +0.02 | +0.01 | -0.04 | +0.04 |

**Normalized percentages (sum absolute weights per column):**
- Ortho_0 total: 0.45 + 0.35 + 0.10 + 0.08 + 0.02 = 1.0 → (45%, 35%, 10%, 8%, 2%)
- Ortho_1 total: 0.82 + 0.12 + 0.05 + 0.02 + 0.01 = 1.02 → (80%, 12%, 5%, 2%, 1%) [approximately]

**Tabular Output:**

| Decorrelated Feature | Contributing Raw Features |
|---|---|
| Ortho_Component_0 | `+annual_revenue (45%), +loan_amount (35%), +credit_score (10%), +employees (8%), +age (2%)` |
| Ortho_Component_1 | `+annual_revenue (80%), -loan_amount (12%), +credit_score (5%), +employees (2%), +age (1%)` |
| Ortho_Component_2 | `+loan_amount (78%), +credit_score (15%), +employees (8%), -annual_revenue (5%), -age (4%)` |
| Ortho_Component_3 | `+credit_score (91%), +employees (2%), +age (4%), -loan_amount (8%), +annual_revenue (2%)` |

**Interpretation:**
- **Ortho_0:** Overall business scale (all features contribute positively; dominated by revenue and loan size)
- **Ortho_1:** Revenue-specific effect after loan variation is removed (revenue dominates; loan is now negative contributor)
- **Ortho_2:** Loan-vs-revenue trade-off (loan dominates; revenue and other factors create small offset)
- **Ortho_3:** Credit quality (credit dominates; others are noise/minor adjustments)

---

## Practical Usage in Analysis Workflow

1. **Fit & Transform:**
   ```python
   from structure_id import structure_id
   
   result = structure_id(
       data=df,
       target='loan_status',
       task_type='classification',
   )
   ```

2. **Get Interpretation Report:**
   ```python
   interp = result.get_orthogonal_feature_interpretation_report()
   
   # Export tabular version
   interp['table'].to_csv('ortho_interpretation.csv', index=False)
   
   # Print structured version for documentation
   import json
   print(json.dumps(interp['structured'], indent=2))
   
   # Show variance summary
   print(interp['summary'])
   ```

3. **Understand Cluster Differences:**
   ```python
   # From Stage 3 output
   cluster_profiles = result.explicit_row_structures
   
   # For each cluster, check which orthogonal components distinguish it
   # by cross-referencing the interpretation table
   ```

4. **Model Selection:**
   ```python
   # Option A: Use orthogonalized features (multicollinearity-free)
   X_ortho = result.orthogonal_basis.drop('structure_id', axis=1)
   
   # Option B: Use original representative features (interpretable)
   X_repr = result.representative_features.drop('structure_id', axis=1)
   
   # Option C: Use top orthogonal components (hybrid)
   top_ortho_cols = interp['summary'].head(3)['Component ID'].tolist()
   X_hybrid = result.orthogonal_basis[top_ortho_cols]
   ```

---

## Troubleshooting Interpretation

### Issue: A component has many small contributors
**Meaning:** The component is capturing residual/noise variation  
**Action:** Check if below-5% threshold filtering helps; consider dropping this component if not needed for clustering/modeling

### Issue: A component is dominated by a single feature
**Meaning:** That feature is largely orthogonal (independent) from others  
**Action:** This is expected if the feature has low collinearity; useful for downstream modeling

### Issue: Weights are negative for all major contributors
**Meaning:** The component represents an inverse relationship (e.g., "not-A, not-B, not-C")  
**Action:** This is valid; sign convention shows direction relative to the orthogonal component value

### Issue: The interpretation doesn't match domain knowledge
**Meaning:** Features may have non-obvious statistical relationships  
**Action:** Review the actual correlation structure; unexpected collinearity patterns may indicate data quality issues or legitimate complex relationships

---

## References

- **Stage 2 Specification:** Section 6, Stage 2 of `structure_identification_requirements.md`
- **Algorithm:** Modified Gram-Schmidt orthogonalization (unnormalized) via QR decomposition
- **Weight Matrix:** W = R⁻¹ where Q, R = qr(X_centered)
- **Percentage Formula:** Contribution_ij = |W_ij| / Σ_k |W_kj|
- **Threshold:** 5% (configurable via StructureConfig)

