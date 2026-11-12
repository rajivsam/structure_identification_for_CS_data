# Copilot project bootstrap for structure_id

## Project goal
This repository implements a Python package, `structure_id`, for identifying explicit and latent structure in cross-sectional datasets. The package is focused on:

- redundant feature-block detection using Spearman correlation and complete-linkage clustering
- row-level macro-cluster discovery using HDBSCAN
- latent structural-break detection from residual-based heterogeneity tests
- partition-aware train/validation/test workflows with leakage-safe feature application
- analyst-facing training-cluster profiling and report export

## Repository map
- `structure_id/` — main package code
- `tests/` — focused regression tests
- `notebooks/` — analysis notebook demonstrating the full workflow
- `data/` — prepared dataset files
- `reports/` — generated markdown/html reports
- `README.md` — package overview and quickstart
- `structure_identification_requirements.md` — formal requirements spec

## Key package files
- `structure_id/api.py` — public entry point (`structure_id(...)`)
- `structure_id/dataset.py` — partition-aware dataset and featurized-attribute logic
- `structure_id/explicit_structure.py` — explicit column and row clustering logic
- `structure_id/reporting.py` — analyst-facing text reports and training-cluster profile export
- `structure_id/types.py` — result objects and metadata containers
- `structure_id/config.py` — configuration defaults and validation rules

## Current implementation status
This project has already implemented the following requirements and behavior:

- partition-aware selection for train/validation/test rows
- duplicate partition-column validation (`dataset_partition` / `dataset_split`)
- feature application methods for training/validation/test partitions
- selection of featurized attributes by explicit list
- redundant feature detection using Spearman distance and complete-linkage clustering
- cluster member metadata including merge history and pairwise correlations
- instance-level `structure_id` assignment with noise handling (`"noise"`)
- training cluster profile generation with a basic/interpretive summary
- markdown and HTML export for the training cluster profile

## Important project conventions
- Use the project-local virtual environment: `.venv`
- Python version target in `pyproject.toml`: `>=3.10`
- Package is installed in editable/uv-friendly form via `pyproject.toml`
- Tests are focused and run with pytest
- The notebook uses the project root to resolve the dataset, even when executed from the `notebooks/` directory

## How to run validation
From the repo root:

```bash
. .venv/bin/activate
pytest -q tests/test_partitioned_dataset.py
```

## Notebook workflow
The notebook at `notebooks/sba_structure_ident.ipynb` is the primary working demonstration.

It does the following:
1. loads the prepared SBA data
2. confirms partition consistency between duplicated partition columns
3. splits data into train/validation/test
4. runs structure identification on the training set
5. emits analyst-readable reporting
6. exports the training cluster profile to markdown and HTML files

## Generated outputs
- `reports/training_cluster_profile.md`
- `reports/training_cluster_profile.html`

These are the exported analyst-facing summaries for the discovered training clusters.

## Typical data workflow
The intended project workflow is:

1. choose/train partition using dataset partition logic
2. discover explicit redundant feature blocks on training data
3. keep representative features only
4. cluster rows in the reduced feature space
5. assign `structure_id`
6. generate the training cluster profile and report
7. use the selected features for downstream model validation/test workflows without re-estimating from held-out data

## Known design decisions to preserve
- preserve the training-vs-validation/test leakage boundary
- do not refit the model on validation/test partitions when applying training-derived feature logic
- allow noise rows to be labeled as the string `"noise"` in `structure_id`
- keep cluster diagnostics explicit and readable for analysts
- prefer interpretable structure summaries over purely black-box model outputs

## Next-session resume guidance
When continuing work in a new session:

- start from the package API in `structure_id/api.py`
- use the notebook as the end-to-end example
- keep changes aligned with `structure_identification_requirements.md`
- validate with the focused pytest suite before broader work

## Useful entry points
```python
from structure_id import structure_id, export_cluster_profile_report

result = structure_id(
    data=train_df,
    target="loan_status_r",
    task_type="classification",
    structural_covariates=[],
)

print(result.summary())
report_paths = export_cluster_profile_report(result, output_dir="reports")
```
