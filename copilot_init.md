# Copilot project bootstrap for structure_id v2.0

## Project goal
This repository implements a **stateless, descriptive analytical tool** (`structure_id` v2.0) for identifying explicit and latent structure in cross-sectional datasets. The package is focused on:

- **Redundant feature-block detection** using normalized mutual information (NMI) and complete-linkage clustering
- **Gram-Schmidt orthogonalization** (unnormalized) with interpretable feature attribution and percentage contribution reporting
- **Row-level macro-cluster discovery** using HDBSCAN with "independent" labels for unclustered rows
- **Latent structural-break detection** from residual-based fluctuation testing with Bonferroni correction
- **Stateless execution**: No fitted transforms persisted; drift comparison via `compare_structures()` utility
- **Analyst-facing interpretation**: Three output formats (tabular, structured/JSON, summary) for orthogonal components
- **Production-ready reporting** with markdown/HTML export

## Repository map (v2.0)
- `structure_id/` — main package code (11 modules)
  - `api.py` — main entry point with full orchestration
  - `validation.py` — Stage 0: Input validation & filtering
  - `explicit_structure.py` — Stages 1-3: NMI clustering, Gram-Schmidt, HDBSCAN
  - `latent_structure.py` — Stage 4: Fluctuation testing
  - `comparison.py` — Drift detection utility (NEW)
- `visualization.py` — Plotting utilities for all 4 stages (NEW)
- `tests/` — comprehensive test suite (31 tests, all passing)
  - `test_structure_id_v2.py` — NEW: 31 comprehensive tests covering all stages
- `notebooks/` — analysis and demonstration
- `data/` — prepared dataset files
- `reports/` — generated markdown/html reports
- `README.md` — package overview, intended use, quickstart
- `structure_identification_requirements.md` — v2.0 specification (refactored, 334 lines)
- `USAGE_GUIDE.md` — comprehensive user manual (21 KB)
- `QUICK_REFERENCE.md` — one-page cheat sheet
- `TEST_REPORT.md` — formal test results and validation
- `IMPLEMENTATION_COMPLETE.md` — architecture overview and technical decisions

## Key package files (v2.0)
- **`structure_id/api.py`** — public entry point (`structure_id(...)`) with full 4-stage orchestration
  - Returns `StructureResult` with `variance_ledger`, `orthogonal_interpretation`, etc.
  - Method: `get_orthogonal_feature_interpretation_report()` for three output formats
- **`structure_id/validation.py`** — Stage 0: Input validation, missing value handling, filtering
- **`structure_id/explicit_structure.py`** — Stages 1-3:
  - NMI-based redundancy clustering and feature collapse
  - Modified Gram-Schmidt orthogonalization with weight matrix extraction
  - HDBSCAN clustering with "independent" string labels
  - Interpretation report generation (tabular, structured, summary)
- **`structure_id/latent_structure.py`** — Stage 4: Fluctuation testing with Bonferroni correction
- **`structure_id/comparison.py`** — `compare_structures()` utility for drift detection (NEW)
- **`structure_id/types.py`** — `StructureResult` dataclass with all outputs
- **`structure_id/config.py`** — `StructureIDConfig` with all parameters
- **`visualization.py`** — Complete visualization module (dendrogram, orthogonality heatmap, cluster dist, variance, contributions) (NEW)

## Current implementation status (v2.0 - COMPLETE ✅)
All requirements implemented and tested:

✅ **Stage 0 (Validation & Preprocessing)**
- Input validation, missing value handling, zero-variance filtering
- Target and structural covariate exclusion

✅ **Stage 1 (Redundancy Collapse)**
- NMI-based feature clustering with complete linkage
- Feature block detection and reduction (17 → 15 features on SBA data)
- Representative feature selection (highest variance per block)

✅ **Stage 2 (Gram-Schmidt Orthogonalization)**
- Modified Gram-Schmidt (unnormalized, preserves scale)
- Weight matrix extraction (W = R⁻¹)
- Perfect orthogonality (max pairwise correlation ≈ 0)
- Three interpretation formats:
  1. **Tabular**: 2-column format (Feature ID | Contributing Raw Features)
  2. **Structured**: Dictionary/JSON with weights, signs, percentages
  3. **Summary**: Variance accounting per component
- Percentage contribution calculation: |W_ij| / Σ_k |W_kj|
- Threshold filtering (configurable, default 5%)

✅ **Stage 3 (Row Clustering)**
- HDBSCAN clustering on orthogonal basis
- "independent" string labels for unclustered rows (not -1)
- Cluster profile computation
- Clustering consistency verified (948-983 clusters on SBA data)

✅ **Stage 4 (Latent Structure)**
- Ordered fluctuation testing on original features
- Asymptotic Brownian bridge p-values
- Bonferroni multiple testing correction
- Primary driver identification

✅ **Stateless Execution**
- No fitted transforms persisted
- Each run independent and reproducible
- Perfect for drift comparison

✅ **Comparison Utility**
- `compare_structures()` for independent run comparison
- Column similarity (Jaccard index)
- Row structure shift detection
- Latent structure agreement verification

✅ **Production Quality**
- 100% type hints on public APIs
- NumPy-style docstrings throughout
- Clear error handling and messages
- All edge cases handled (multicollinearity, zero-variance, p>n)

✅ **Comprehensive Testing**
- 31 unit & integration tests
- 100% success rate (64.29 seconds)
- Real-world validation: SBA dataset (116K rows)
- Structure consistency verified across subsets (Jaccard = 1.0000)

## Important project conventions (v2.0)
- Use the project-local virtual environment: `.venv`
- Python version target in `pyproject.toml`: `>=3.9`
- Package is installed in editable form via `pyproject.toml`
- Tests are comprehensive and run with pytest: `pytest tests/test_structure_id_v2.py -v`
- **Stateless design**: No global state, no fitted transforms persisted between runs
- **Unnormalized Gram-Schmidt**: Preserves scale differences for HDBSCAN effectiveness
- **"independent" string labels**: Not -1 integers; human-readable and unambiguous
- All features are assumed to be numeric; categorical handling via upstream preprocessing

## Intended Use (v2.0)
This package is a **descriptive analytical tool**, not a predictive gate. Key use cases:

1. **Understand sub-populations** in discovery data (iid violations, stratification needs)
2. **Compare structures** across time/conditions (drift detection, operational stability)
3. **Foundation for feature development** (hypothesis testing, targeted analysis)
4. **Evolving capability** based on adoption and feedback

See README.md "Intended Use & Application Context" for full details.

## How to run validation (v2.0)
From the repo root:

```bash
source .venv/bin/activate
pytest tests/test_structure_id_v2.py -v
```

Expected output: **31 passed in 64.29s** ✅

## Notebook workflow (v2.0)
The primary demonstration is via the Python API (not a specific notebook):

```python
import pandas as pd
from structure_id import structure_id, compare_structures

# Load prepared data
df = pd.read_csv('data/model_ready_numeric_data.csv')

# Run structure identification (all 4 stages)
result = structure_id(
    data=df,
    target='loan_status_r',
    task_type='classification',
)

# Inspect results
print(result.variance_ledger)  # Accounting summary
interp = result.get_orthogonal_feature_interpretation_report()
print(interp['table'])        # Tabular interpretation
print(interp['structured'])   # Structured (JSON)
print(interp['summary'])      # Summary

# Export reports
paths = result.save_reports(output_dir='reports/')

# Compare independent runs (drift detection)
result_a = structure_id(data=df_subset_a, target='loan_status_r', task_type='classification')
result_b = structure_id(data=df_subset_b, target='loan_status_r', task_type='classification')
comparison = compare_structures(result_a, result_b)
print(comparison)
```

## Generated outputs (v2.0)
- Markdown and HTML reports via `result.save_reports()`
- Three interpretation formats: tabular, structured, summary
- Variance ledger with detailed accounting
- Orthogonal basis with structure_id labels
- Cluster profiles and latent structure results

## Typical data workflow (v2.0)
1. Prepare data (cleaned, numeric, analysis-ready) upstream
2. Call `structure_id(data, target, task_type)` — full 4-stage execution
3. Inspect `result.variance_ledger` for accounting
4. Get interpretation via `result.get_orthogonal_feature_interpretation_report()`
5. Compare structures across conditions via `compare_structures(result_a, result_b)`
6. Export reports via `result.save_reports(output_dir)`
7. Use insights to inform modeling decisions or detect drift

## Known design decisions to preserve (v2.0)
- **Stateless execution**: No global state, no fitted transforms between runs
- **Unnormalized Gram-Schmidt**: Preserves scale for HDBSCAN effectiveness
- **"independent" string labels**: Not -1; human-readable and clear semantics
- **Weight matrix for interpretation**: W = R⁻¹ enables exact feature attribution
- **Three interpretation formats**: Tabular (analysis), Structured (programmatic), Summary (variance)
- **Percentage contributions**: Use absolute values to capture "strength" regardless of sign
- **Threshold filtering**: Default 5%, configurable per call
- **Drift detection**: Compare independent runs, not fitted state

## Next-session resume guidance (v2.0)
When continuing work in a new session:

- Start from the specification: `structure_identification_requirements.md` (v2.0)
- Review intended use in README.md "Intended Use & Application Context"
- Understand the 4-stage pipeline: validation, redundancy collapse, Gram-Schmidt, clustering
- Use `structure_id/api.py` as the entry point
- Validation: Run `pytest tests/test_structure_id_v2.py -v` (expect 31/31 ✅)
- Real-world reference: See `TEST_REPORT.md` for SBA dataset results
- Keep changes aligned with `structure_identification_requirements.md` v2.0
- Use `USAGE_GUIDE.md` for user-facing changes
- Document in `GRAM_SCHMIDT_INTERPRETATION_GUIDE.md` for methodology changes

## Useful entry points (v2.0)
```python
from structure_id import structure_id, compare_structures

# Single run: Understand dataset structure
result = structure_id(
    data=df,
    target='target_column',
    task_type='classification',  # or 'regression'
)

# Access results
variance_summary = result.variance_ledger
interpretation = result.get_orthogonal_feature_interpretation_report()
orthogonal_df = result.orthogonal_basis  # Decorrelated features

# Drift detection: Compare two runs
result_a = structure_id(data=df_subset_a, target='y', task_type='classification')
result_b = structure_id(data=df_subset_b, target='y', task_type='classification')
comparison = compare_structures(result_a, result_b)

# Export reports
paths = result.save_reports(output_dir='reports/')
```

## Key documentation (v2.0)
- **README.md**: Overview, intended use, quickstart (primary entry point)
- **USAGE_GUIDE.md**: Comprehensive user manual with examples
- **QUICK_REFERENCE.md**: One-page visual reference
- **structure_identification_requirements.md**: v2.0 specification
- **GRAM_SCHMIDT_INTERPRETATION_GUIDE.md**: Methodology guide
- **TEST_REPORT.md**: Test results and real-world validation
- **IMPLEMENTATION_COMPLETE.md**: Architecture and technical decisions
- **COMMIT_LOG.md**: Release documentation
