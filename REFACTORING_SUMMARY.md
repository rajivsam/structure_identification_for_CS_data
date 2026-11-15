# Refactoring Summary: structure_identification_requirements.md

**Date:** 2026-11-15  
**Version Transition:** v1.0 → v2.0

---

## Overview

The `structure_identification_requirements.md` has been comprehensively refactored to reflect:

1. **Stateless Execution Model:** Removed partition-specific state management; package now operates on single DataFrames independently
2. **Gram-Schmidt Orthogonalization:** Replaced vague orthogonalization references with detailed Modified Gram-Schmidt (unnormalized) specification with explicit feature attribution
3. **Interpretability-First Design:** Added tabular and structured reporting methods for orthogonal feature composition
4. **Cleaner Pipeline Structure:** Condensed 663 lines to 334 lines by removing redundant definitions and clarifying the 4-stage pipeline

---

## Key Changes

### 1. **Architecture: Stateless → Exploratory**

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| **Partition handling** | Implicit train/validation/test state management | Analysts manage partitions externally; package runs stateless on input DataFrame |
| **Feature transforms** | Stateful fitted transformers retained | No fitted state; comparison via `compare_structures()` utility |
| **Reusability** | Train → apply to held-out data | Independent runs on any dataset; drift comparison via `compare_structures()` |

### 2. **Stage 2: Orthogonalization with Full Interpretability**

**New Section 6.2: Basis Orthogonalization (Modified Gram-Schmidt with Interpretability)**

**Key additions:**
- **Algorithm Details:** Explicit Modified Gram-Schmidt (unnormalized) formulation with near-zero guard
- **Scale Preservation Rule:** Do NOT rescale to unit variance (unnormalized) to preserve between-cluster gaps for HDBSCAN
- **Feature Attribution Matrix W:** Extract column vectors showing exact linear combinations of original features
- **Percentage Contribution Formula:** `Contribution_ij = |W_ij| / Σ_k |W_kj|` with 5% threshold filtering
- **Interpretability Reporting Method:** `get_orthogonal_feature_interpretation_report()` with three output formats:
  
  1. **Tabular Format** (NEW):
     - Column 1: Decorrelated Feature ID (e.g., `Ortho_Component_0`)
     - Column 2: Contributing Raw Features (Ordered by Strength)
     - Example: `"+Feature_A (48%), -Feature_B (32%), +Feature_C (20%)"`
  
  2. **Structured Dictionary/JSON:**
     - Mapping component → contributing features, signs (+/-), raw weights, percentages
  
  3. **Summary DataFrame:**
     - Component ID, Retained Variance, Dominant Attribute Group, Top Driver

### 3. **Instance Labeling: "independent" String Label**

**Clear specification for row clustering:**
- Valid HDBSCAN clusters: integer IDs (0, 1, …, k-1)
- HDBSCAN noise (-1): labeled as string `"independent"` (not -1)
- Benefit: Human-readable distinction between clustered and unclustered rows

### 4. **Configuration Parameters (Simplified)**

**Consolidated into Section 4:**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `mutual_information_threshold` | 0.85 | NMI redundancy cutoff |
| `min_cluster_size` | 15 | HDBSCAN minimum cluster |
| `alpha` | 0.05 | Significance threshold (with Bonferroni) |
| `std_threshold` | 1e-5 | Min numeric variance |
| `max_missing_ratio` | 0.20 | Max missingness allowed |
| `max_categories` | 30 | Max unique categorical levels |
| `max_class_concentration` | 0.98 | Max dominant category proportion |
| `random_state` | 42 | Deterministic seed |

### 5. **Result Objects: StructureResult with Interpretation**

**New fields in StructureResult:**
- `orthogonal_interpretation: dict` — Full feature attribution from `get_orthogonal_feature_interpretation_report()`
- `variance_ledger: dict` — High-level accounting (total/dropped/independent features; clustered/independent rows; n_clusters; latent_break_detected)

**Preserved fields:**
- `explicit_column_structures`, `orthogonal_basis`, `representative_features`
- `explicit_row_structures`, `latent_structures`, `diagnostics`
- `report_markdown`, `to_html()`, `save_reports()`

### 6. **Pipeline Stages (Clearer Specification)**

| Stage | Goal | Key Output |
|-------|------|-----------|
| **Stage 0** | Input validation, filtering, imputation | l_provisional (surviving candidates) |
| **Stage 1** | NMI clustering, redundancy collapse | Z_rep (representatives), explicit_column_structures |
| **Stage 2** | Modified Gram-Schmidt orthogonalization | U (orthogonal matrix), W (weight matrix), orthogonal_interpretation |
| **Stage 3** | HDBSCAN clustering on U | structure_id (0/1/…/k/"independent"), cluster profiles in original Z_rep units |
| **Stage 4** | Fluctuation testing on original Z_rep | latent_structures, primary_driver, cutpoint, p-values |

---

## Removed Content

### Sections Eliminated (Redundancy/Clarity):

1. **Old Sections 3-4 (Definitions & Inputs):** Consolidated into new Sections 3-5
2. **Partition-Aware Workflows (Section 5.1.6):** Removed partition selection methods; now external to package
3. **Stateful Feature Application Methods:** Removed `apply_training_features()`, `apply_validation_features()`, `apply_test_features()`
4. **Convenience Selection Methods:** Removed `select_featurized_attributes()`
5. **Stage 1-4 Functional Requirements Details:** Refactored into unified **Pipeline Specification** section

**Net reduction:** ~329 lines of redundant definitions and partition-specific logic

---

## Acceptance Criteria Updates

### New Criteria (v2.0):

✅ Criterion 4: `get_orthogonal_feature_interpretation_report()` returns both tabular and structured interpretations  
✅ Criterion 5: Tabular interpretation includes (1) Decorrelated Feature ID, (2) Contributing Raw Features Ordered by Strength  
✅ Criterion 9: All type hints follow Python 3.10+ conventions and NumPy-style docstrings  

### Preserved Criteria:

- Orthogonal columns have near-zero pairwise correlation
- Linear combinations using reported weights reconstruct transformed columns
- Multicollinearity/zero-variance handling
- HDBSCAN clustering with `"independent"` labeling
- Bonferroni-adjusted fluctuation testing on original features
- `compare_structures()` for cross-run comparison

---

## Edge Cases Clarified

| Edge Case | v1.0 | v2.0 |
|-----------|------|------|
| **Perfect multicollinearity** | Vague | Detected in Stage 1; one representative retained |
| **Zero-variance columns** | Mentioned | Detected in Stage 0; dropped before processing |
| **Wide datasets (p > n)** | Not addressed | Clear `ValueError` after Stage 1 |
| **All instances independent** | Not addressed | All rows labeled `"independent"`; n_clusters = 0 |

---

## Design Decisions Formalized

### Section 12: Known Design Decisions to Preserve

1. **Leakage Boundary:** No refitting on held-out data
2. **Orthogonal Scale:** Unnormalized Gram-Schmidt (no unit-variance rescaling)
3. **Original Units for Latent Tests:** Residuals sorted by un-orthogonalized features for direct cutpoint interpretation
4. **Noise Label String:** Use `"independent"` (not -1) for clarity
5. **Interpretability First:** Human-readable feature attribution over black-box outputs

---

## Module Layout (Refined)

```text
structure_id/
├── __init__.py              # Exports structure_id, compare_structures, StructureConfig
├── api.py                   # Orchestrates Stages 0–4 and assembles StructureResult
├── config.py                # StructureConfig dataclass and defaults
├── validation.py            # Stage 0 input validation, filtering, imputation
├── explicit_structure.py    # Stage 1 NMI + Stage 2 Gram-Schmidt + Stage 3 HDBSCAN
│                           # + get_orthogonal_feature_interpretation_report()
├── latent_structure.py      # Stage 4 baseline model, fluctuation test, Bonferroni
├── comparison.py            # Stateless compare_structures(result_a, result_b)
├── reporting.py             # Variance ledger, Markdown & HTML report generators
└── types.py                 # Typed dataclasses for blocks, clusters, breaks, results, interpretation
```

---

## Specification Follow-Up Questions

For implementation, three design questions remain open (Section 13):

1. **Test Plan:** Pytest suite specification for Gram-Schmidt orthogonality and `"independent"` labeling?
2. **Visualization:** Optional dendrogram plots or orthogonalization weight heatmaps?
3. **Caching:** Stateless only, or add optional stateful `fit()`/`transform()` API for large datasets (violates spec)?

---

## Validation Checklist

- ✅ Refactored to v2.0 format (stateless + Gram-Schmidt)
- ✅ Stage 2 orthogonalization fully specified (algorithm, attribution, reporting)
- ✅ Tabular interpretation format defined (2-column: Decorrelated Feature, Contributing Raw Features)
- ✅ Edge cases clarified
- ✅ Module layout updated
- ✅ Acceptance criteria revised
- ✅ Design decisions formalized
- ✅ Line count reduced: 663 → 334 (49.6% compression via clarity)

---

## Next Steps

1. **Implementation:** Use Section 6 (Pipeline Specification) as the authoritative reference for coding each stage
2. **Reporting:** Use Section 7 (Result Objects) to design `StructureResult` dataclass and `get_orthogonal_feature_interpretation_report()` method
3. **Testing:** Use Section 11 (Deliverables) and Section 9 (Acceptance Criteria) to build pytest suite
4. **Documentation:** Use Section 3 (Public API) as the user-facing entry point

---

## Files Modified

- **Path:** `/home/rajiv/programming/structure_identification_for_CS_data/structure_identification_requirements.md`
- **Lines:** 663 → 334
- **Sections:** 1–13 (refactored from 1–5+)
- **Status:** Ready for implementation

