# Specification: `structure_id` (v2.0) — Cross-Sectional Structural Variance Accounting

**Version:** 2.0  
**Status:** Active specification (refactored for Gram-Schmidt orthogonalization and stateless execution)

---

## 1. Overview & Purpose

`structure_id` is a **stateless, descriptive Python package** for accounting for structural variance components in cleaned, cross-sectional tabular datasets. It helps analysts decompose both column space and row space before committing to a global predictive model:

1. **Redundant Features:** Coupled column blocks carrying overlapping information.
2. **Orthogonalized Features:** Linearly independent basis of surviving features via Gram-Schmidt orthogonalization with full interpretability reporting.
3. **Clustered Instances:** Dense row sub-populations (`structure_id` ∈ {0, 1, …, k}).
4. **Independent Instances:** Diffuse, unclustered background rows (`structure_id == "independent"`).
5. **Latent Heterogeneity:** Residual structural breaks along interpretable features that persist beyond explicit column and row structure.

### Design Boundaries
* **Stateless Execution:** No built-in `train`/`validation`/`test` partitioning or stateful feature-transform persistence. Analysts slice DataFrames externally and run `structure_id()` independently on any dataset, using `compare_structures(res_a, res_b)` for stage-wise drift or stability comparisons.
* **Exploratory Aid:** Statistical tests (e.g., fluctuation p-values) serve as exploratory discovery diagnostics rather than confirmatory hypothesis gates.
* **Upstream Assumptions:** Input data is cross-sectional (no time-series/panel logic) and already cleaned and numerically featurized upstream.
* **Cross-Sectional Only:** Not intended for time-series, longitudinal, panel, or repeated-measures datasets.

---

## 2. Scope

### 2.1 In Scope

The package shall support:
- Dataset ingestion from tabular data already cleaned and numerically featurized upstream
- Target and task validation
- Explicit feature redundancy filtering via Normalized Mutual Information (NMI) clustering
- Interpretable Gram-Schmidt orthogonalization with feature attribution reporting
- Explicit row clustering / macro-population discovery using orthogonalized features
- Latent structural-break detection using residual-based fluctuation tests on original (non-orthogonalized) features
- Stateless comparison workflows (`compare_structures`) for assessing structural similarity across independent runs
- Output generation for analysts including variance accounting, feature interpretation tables, and cluster profiles

### 2.2 Out of Scope

The package shall not support:
- Dataset downloading or raw ingestion from external repositories
- Cleaning logic for messy source files beyond basic imputation and filtering
- Longitudinal or temporal modeling assumptions
- Within-unit tracking or repeated measurements
- Explicit forecasting or time ordering
- Automatic partition-variable ensemble fitting without a valid structural baseline

### 2.3 Upstream Data Pipeline Assumption

This package is intentionally scoped to the structure-discovery layer. It assumes the upstream data pipeline has already performed dataset acquisition, cleaning, and numeric featurization. The package consumes tabular data with columns already cleaned, typed, and in numeric form suitable for redundancy analysis and downstream modeling, and does not re-implement cleaning or feature engineering.

## 3. Public API

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

## 4. Configuration Parameters (`StructureConfig`)

- `mutual_information_threshold: float = 0.85` — NMI cutoff for redundant feature blocks (accept `correlation_threshold` as deprecated alias)
- `min_cluster_size: int = 15` — HDBSCAN minimum cluster size
- `alpha: float = 0.05` — Bonferroni-adjusted significance threshold for latent breaks
- `std_threshold: float = 1e-5` — minimum standard deviation to retain a numeric column
- `max_missing_ratio: float = 0.20` — maximum allowed missingness per column
- `max_categories: int = 30` — maximum unique levels for categorical columns
- `max_class_concentration: float = 0.98` — maximum dominant category proportion
- `random_state: int = 42` — seed for deterministic NMI estimation and clustering

## 5. Definitions

### 5.1 Dataset

A dataset D is a tabular, row-wise data structure where each row represents one observation, each column represents one variable or feature, and variables are assumed to have already passed upstream cleaning and numeric representation steps.

### 5.2 Target

Y is the variable to be predicted or explained, supplied as a named column in D or as a separate aligned vector.

### 5.3 Task Type

T is the modeling type: either `regression` or `classification`, which determines the baseline model objective and residual interpretation.

### 5.4 Structural Covariates

X is an optional set of variables known to be legitimate structural predictors. These variables are excluded from candidate analysis but may be used in the baseline model.

### 5.5 Candidate Features

Z is the pool of variables evaluated as possible drivers of structure, excluding Y, X, invariant columns, and invalid columns.

### 5.6 Explicit Structure

Explicit structures are observable and directly measurable in the feature space:
- Redundant feature blocks (collinear numeric variables detected via NMI clustering)
- Dense row clusters or macro-populations (discovered via HDBSCAN on orthogonalized features)

### 5.7 Latent Structure

Latent structures describe hidden changes in the predictive relationship inferred from model residual behavior. A latent structure is a statistically significant break or instability along a candidate variable detected via ordered fluctuation testing.

## 6. Pipeline Specification

### Stage 0: Validation & Candidate Preparation

1. **Input Validation (Fail Fast):** Raise `ValueError` if:
   - `data` is empty
   - `target` is missing or misaligned
   - `task_type` is not `"regression"` or `"classification"`
   - `structural_covariates` contains missing columns

2. **Exclusions:** Exclude `target` (Y) and `structural_covariates` (X) from candidate pool Z.

3. **Filtering:**
   - Drop columns where missing ratio > `max_missing_ratio`
   - Impute remaining numeric missing values with column median (emit warning)
   - Encode remaining categorical missing values as `"__MISSING__"`
   - Drop numeric columns with ≤1 unique value or std < `std_threshold`
   - Drop categorical columns with > `max_categories` unique values or dominant class frequency > `max_class_concentration`
   - Raise `ValueError` if no valid candidate columns survive

4. **Record Count:** Store surviving candidate count as `l_provisional`.

---

### Stage 1: Explicit Feature Clustering (Redundancy Collapse)

**Goal:** Identify redundant feature blocks and select a single interpretable representative per block.

1. **Redundancy Matrix:** For all surviving numeric candidate columns in Z, compute pairwise Normalized Mutual Information (NMI ∈ [0, 1]) and convert to distance D_ij = 1 - NMI_ij.

2. **Hierarchical Clustering:** Apply complete-linkage agglomerative clustering on D and cut at height = 1.0 - `mutual_information_threshold`.

3. **Representative Selection:**
   - For singleton clusters: retain the feature as-is
   - For multi-feature clusters: select the feature with highest variance as `representative_feature` and mark all others as `dropped_features`

4. **Output:**
   - Record `explicit_column_structures` (cluster ID, representative feature, dropped features, pairwise NMI submatrix, threshold)
   - Define surviving feature set Z_rep and post-filter candidate count l = |Z_rep|

---

### Stage 2: Basis Orthogonalization (Modified Gram-Schmidt with Interpretability)

**Goal:** Remove linear overlap among surviving features Z_rep prior to row clustering without compressing multi-modal cluster separation.

1. **Ordering:** Order numeric columns in Z_rep by **descending variance** (z₍₁₎, z₍₂₎, …, z₍ₗ₎).

2. **Centering:** Subtract the sample mean from each column: z̃₍ⱼ₎ = z₍ⱼ₎ - z̄₍ⱼ₎.

3. **Modified Gram-Schmidt (Unnormalized):**
   - Set u₁ = z̃₍₁₎
   - For j = 2…l:
     ```
     u_j = z̃_(j) - Σ(k=1 to j-1) [⟨z̃_(j), u_k⟩ / ⟨u_k, u_k⟩] * u_k
     ```
   - Guard against near-zero denominators ⟨u_k, u_k⟩ < 10⁻¹²

4. **Scale Preservation Rule:** **Do not** rescale u_j to unit variance (avoid ZCA/global whitening), so large between-cluster gaps in multi-modal data remain intact for HDBSCAN.

5. **Feature Attribution & Weighting:**
   - Extract the orthogonalization weight matrix W where column j represents the exact linear combination of original features forming orthogonal component j
   - Compute relative percentage contributions: Contribution_ij = |W_ij| / Σ_k |W_kj|
   - Filter out negligible contributors below configurable `threshold = 0.05` (5%)
   - Store raw weights, signs, and normalized percentages for each component

6. **Interpretability Reporting Method:** Implement `get_orthogonal_feature_interpretation_report()` returning:
   - **Tabular representation:** For each orthogonalized component, a table showing:
     - **Column 1: Decorrelated Feature** (e.g., `Ortho_Component_0`)
     - **Column 2: Contributing Raw Features (Ordered by Strength)** (formatted string showing feature name, sign, and percentage contribution, ordered descending by absolute weight)
     - Example: `"+Feature_A (48%), -Feature_B (32%), +Feature_C (20%)"`
   - **Structured Dictionary/JSON:** Mapping each component to contributing original features, signs (+/-), raw weights, and relative percentages
   - **Summary DataFrame:** Component ID, Retained Variance, Dominant Attribute Group, Top Driver

7. **Output:** Store the orthogonalized feature matrix U for Stage 3 clustering, while retaining the un-orthogonalized Z_rep for Stage 3 profiling and Stage 4 break scanning.

---

### Stage 3: Explicit Row Clustering & Independent Instance Accounting

**Goal:** Partition dataset instances into dense macro-clusters versus diffuse independent rows.

1. **Density Clustering:** Run HDBSCAN (`min_cluster_size=config.min_cluster_size`) on the Stage 2 orthogonalized matrix U (incorporating one-hot encoded categorical survivors if present).

2. **Instance Assignment (`structure_id` column):**
   - Rows assigned to a valid HDBSCAN cluster receive integer cluster IDs (0, 1, …, k-1)
   - Rows assigned -1 (noise) by HDBSCAN receive the label `"independent"`

3. **Human-Readable Cluster Profiling:**
   - Compute cluster sizes, proportion of clustered vs. `"independent"` instances, and per-cluster summary statistics (mean, median, IQR)
   - Map statistics back onto the **original un-orthogonalized features** Z_rep
   - Identify top distinguishing features per cluster relative to overall dataset distribution

---

### Stage 4: Latent Heterogeneity Analysis (Residual Fluctuation Testing)

**Goal:** Detect hidden instability in the predictive relationship P(Y | X) along surviving features.

1. **Baseline Model:**
   - Fit a global baseline model predicting Y using `structural_covariates` X (or intercept-only if X is empty)
   - **regression:** OLS / Ridge linear model → raw residuals e_i = y_i - ŷ_i
   - **classification:** Logistic regression → deviance or Pearson residuals e_i

2. **Ordered Fluctuation Scan:**
   - For each feature z ∈ Z_rep (using **original un-orthogonalized values** so cutpoints remain directly interpretable):
     - Sort residuals e₍₁₎, …, e₍ₙ₎ by ascending values of z
     - Compute normalized cumulative sum process W_n(t) for t ∈ [0, 1]
     - Compute supremum test statistic λ = max_t |W_n(t)| and asymptotic Brownian bridge p-value p_raw

3. **Multiple Testing Adjustment:**
   - Apply Bonferroni correction using l = |Z_rep|:
     ```
     p_adjusted = min(p_raw × l, 1.0)
     ```

4. **Selection:** Flag candidates with p_adjusted < α, recording the primary driver (smallest p_adjusted), cutpoint value in z's original units, and affected observation indices. If none pass, set `primary_driver = None`.


## 7. Result Objects & Reporting

### `StructureResult` Fields

- `variance_ledger: dict` — High-level accounting summary:
  - `total_features`, `dropped_redundant_features`, `independent_basis_features`
  - `total_rows`, `clustered_rows`, `independent_rows`, `n_clusters`
  - `latent_break_detected: bool`
- `explicit_column_structures: list[FeatureBlock]` — Cluster ID, representative feature, dropped features, pairwise NMI submatrix, threshold
- `orthogonal_basis: pd.DataFrame` — Stage 2 orthogonalized feature matrix U with `structure_id` column appended
- `orthogonal_interpretation: dict` — Feature attribution mapping from `get_orthogonal_feature_interpretation_report()`
- `representative_features: pd.DataFrame` — Stage 1 surviving features Z_rep with `structure_id` column appended
- `explicit_row_structures: list[RowClusterProfile]` — Per-cluster summary statistics and top distinguishing features
- `latent_structures: LatentBreakResult` — Primary driver, cutpoint, p-values, affected observation indices
- `diagnostics: dict` — Dropped columns & reasons, `l_provisional`, `l`, warnings, applied config
- `report_markdown: str` — Human-readable narrative summary + cluster profiles
- Methods: `to_html() -> str` and `save_reports(output_dir: str | Path) -> dict[str, Path]`

### `compare_structures(result_a, result_b) -> ComparisonResult`

Stateless comparison utility returning:
- **Column Structure Similarity:** Jaccard similarity of `representative_features` and redundant feature block groupings
- **Row Structure Shift:** Delta in clustered vs. `"independent"` instance proportions and cluster count (n_clusters_a vs. n_clusters_b)
- **Latent Structure Agreement:** Whether both runs identify the same `primary_driver` and direction/cutpoint shift
- **Orthogonal Basis Drift:** Stability of orthogonalized component composition (optional detailed check)

---

## 8. Module Layout

```text
structure_id/
├── __init__.py              # Exports structure_id, compare_structures, StructureConfig
├── api.py                   # Orchestrates Stages 0–4 and assembles StructureResult
├── config.py                # StructureConfig dataclass and defaults
├── validation.py            # Stage 0 input validation, filtering, imputation
├── explicit_structure.py    # Stage 1 NMI clustering, Stage 2 Modified Gram-Schmidt with interpretation,
│                           # Stage 3 HDBSCAN, and reporting methods
├── latent_structure.py      # Stage 4 baseline model, fluctuation test, Bonferroni adjustment
├── comparison.py            # Stateless compare_structures(result_a, result_b)
├── reporting.py             # Variance accounting ledger, Markdown & HTML report generators
└── types.py                 # Typed dataclasses for blocks, clusters, breaks, results, and interpretation
```

---

## 9. Acceptance Criteria

1. ✅ `structure_id()` runs end-to-end on a single DataFrame with no partition state required
2. ✅ Redundant numeric features (NMI ≥ threshold) are collapsed to highest-variance representatives in Stage 1
3. ✅ Surviving features undergo variance-ordered Modified Gram-Schmidt orthogonalization **without unit-variance rescaling** in Stage 2
4. ✅ `get_orthogonal_feature_interpretation_report()` returns both tabular and structured interpretations showing original feature contributions, signs, and percentages for each orthogonal component
5. ✅ Tabular interpretation includes columns: (1) Decorrelated Feature ID, (2) Contributing Raw Features Ordered by Strength (formatted string)
6. ✅ HDBSCAN runs on the orthogonalized basis in Stage 3, labeling valid clusters 0…k-1 and unclustered rows `"independent"`, while reporting cluster profiles in original feature units
7. ✅ Stage 4 scans residuals sorted by original un-orthogonalized representative features and applies Bonferroni adjustment over l = |Z_rep|
8. ✅ `compare_structures(res_a, res_b)` accurately summarizes structural differences across two independent runs
9. ✅ All type hints follow Python 3.10+ conventions and NumPy-style docstrings are provided for all public methods

---

## 10. Edge Cases to Handle

1. **Perfect Multicollinearity:** Dataset contains duplicate or linearly dependent columns → detected in Stage 1; redundant features dropped; one representative retained
2. **Zero-Variance Columns:** Dataset contains constant features (all zeros after mean-centering) → detected in Stage 0; dropped before processing
3. **Unseen Test Data (via `compare_structures`):** Applying structures learned on one dataset to another independent dataset must not require refitting → `compare_structures()` is stateless and descriptive only
4. **Wide Datasets (p > n):** Raise clear `ValueError` if the number of features exceeds the number of samples after Stage 1, as full orthogonalization is mathematically underdetermined
5. **Zero Latent Breaks:** No features pass the fluctuation test → `primary_driver = None` and `latent_break_detected = False`
6. **All Instances Independent:** HDBSCAN assigns all rows to noise → all rows labeled `"independent"`, `n_clusters = 0`, `clustered_rows = 0`

---

## 11. Deliverables

1. Complete, production-ready Python module (`structure_id/`) implementing the full pipeline
2. Comprehensive pytest unit test suite verifying:
   - Orthogonal output columns have near-zero pairwise correlation (≈ 0)
   - Linear combinations of original features using reported weights reconstruct transformed columns
   - Multicollinear and constant columns are handled gracefully
   - Row clustering produces expected cluster counts and `"independent"` label assignment
   - Latent fluctuation testing identifies known breaks or correctly reports none
3. End-to-end working demonstration in `notebooks/sba_structure_ident.ipynb`
4. Example usage showing `structure_id()`, orthogonal interpretation reporting, and `compare_structures()` on synthetic correlated datasets

---

## 12. Known Design Decisions to Preserve

- **Leakage Boundary:** Preserve the training-vs-validation/test leakage boundary; do not refit on held-out data
- **Orthogonal Scale:** Do not rescale orthogonalized features to unit variance (unnormalized Gram-Schmidt) to preserve between-cluster separation for HDBSCAN
- **Original Units for Latent Tests:** Always scan residuals sorted by original un-orthogonalized features so cutpoint interpretation remains direct and actionable
- **Noise Label String:** Allow noise rows to be labeled as the string `"independent"` (not integer -1) in `structure_id` for clarity
- **Interpretability First:** Prioritize human-readable feature attribution over black-box model outputs

---

## 13. Specification Follow-Up Questions for Implementation

- **Test Plan:** Would a pytest suite specification for each stage (especially Gram-Schmidt orthogonality verification and `"independent"` labeling) be useful during implementation?
- **Visualization:** Should the reporting module optionally generate dendrogram plots for Stage 1 NMI clustering or heatmaps of the orthogonalization weights?
- **Caching:** For large datasets, should Stage 2 orthogonalization weights be cached and re-usable via a `fit()`/`transform()` stateful API (violating statelessness) or kept strictly stateless as specified?
