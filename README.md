# structure_id

`structure_id` is a Python package for identifying the descriptive structure in a cross-sectional dataset. This is the primary intent of the package. It is useful during model development to understand the structure present in the data before committing to a single global model or downstream workflow. This is a sophisticated use case for applied analytics and model development.

The package can also be used to compare different segments of the same dataset, or different instances of the dataset, to determine whether they are structurally similar. This can be done at:

1. model development time to check whether development is being performed in a drifting environment
2. operational time to see whether drift has occurred

Both of these cases can be checked using rigorous statistical testing for feature drift. This is the suggested approach for verifying feature drift. Structure assessment on potentially drifting datasets is primarily a diagnostic and verification modality rather than a replacement for formal drift testing.

The package focuses on two complementary forms of structure:

- Explicit structure: redundant feature blocks, dense row clusters, and macro-populations that are directly visible in the feature space.
- Latent structure: hidden instability in the predictive relationship that appears through residual-based structural-break detection.

## Intended Use & Application Context

**This package is designed as a descriptive analytical tool** for understanding and characterizing internal structure in datasets. It is intended to support decision-making about data and models, not to replace formal statistical testing or serve as a hard gate in automated workflows.


### Use Cases

**1. Understanding Sub-Populations in Discovery Data**
Use `structure_id` to gain a summary view of the populations and structures present in your dataset before modeling. This can inform critical modeling decisions, such as:
- Identifying whether independent, identically distributed (i.i.d.) assumptions are violated
- Recognizing whether separate treatment of distinct sub-populations is warranted
- Assessing whether a single global model is appropriate or whether stratified approaches are needed

**2. Comparative Structure Assessment Across Time or Conditions**
Compare dataset structures at different points in time or under different operational conditions to:
- Understand the natural range of structural variation encountered with the same model
- Assess whether operational structures remain within expected bounds (those for which the model meets performance SLAs)
- Diagnose performance degradation by identifying structural shifts between high-performing and degraded periods
- Validate that held-out test data reflects the same structural patterns as training data

**3. Foundation for Feature Development & Hypothesis Testing**
Use discovered structures as a foundation for targeted analysis:
- Test specific hypotheses about the structures and populations identified
- Reason about different feature directions and representations
- Design validation experiments that account for structural heterogeneity
- Explore alternative feature engineering approaches grounded in the discovered structure

**4. Evolving Capability**
This package provides a foundation that will evolve based on adoption and practical use:
- Feedback from real-world applications will guide feature development
- New capabilities will be added to address emerging use cases
- The package should be viewed as a living tool that adapts to user needs

### Important Caveats

- **Descriptive, Not Predictive:** Structure assessment is diagnostic in nature. It supports decision-making but is not framed as a strict automated gate.
- **Complement to Formal Testing:** While structure analysis is useful for diagnostics and verification, it should complement—not replace—rigorous statistical testing for feature drift and performance monitoring.
- **Qualitative Context Matters:** Use discovered structures in light of domain knowledge and business context. Structure patterns require analyst interpretation and validation.

## Enterprise use case

In enterprise machine learning workflows, a dataset often appears to be well behaved at the aggregate level while still containing important internal heterogeneity. A single global model may look acceptable in overall performance metrics but fail systematically in one or more subgroups.

`structure_id` provides a structured, analyst-friendly view of the dataset so teams can identify:

- redundant or near-duplicate features that do not add incremental information
- stable row clusters or macro-populations that may require separate treatment
- latent instability in the relationship between features and the target
- whether held-out data exhibits the same structure as the discovery dataset

The package is intended primarily for descriptive analytics and drift-oriented diagnostics. It is not framed as a strict predictive gate. Instead, it supports a disciplined assessment of whether the discovered structure is stable and whether apparent differences between training and test data are likely to reflect drift or other data changes.

## Scope and positioning

`structure_id` is a downstream structure-discovery tool. It assumes that upstream data preparation has already occurred and that the data entering this package is in a cleaned, numeric, analysis-ready tabular form.

This package does not replace the upstream KMDS pipeline responsibilities for:

- dataset acquisition and verification
- raw parsing and cleaning
- numeric featurization and preparation

It is intentionally designed to consume prepared tabular data and operate on the structure-discovery layer.

## Upstream pipeline assumptions

This package expects the upstream pipeline to have already performed the following steps:

1. Dataset acquisition and verification using the KMDS dataset utility stack, such as the workflows provided in https://github.com/rajivsam/kmds-dataset-util
2. Parsing and cleaning using explicit cleaning workflows, such as those in https://github.com/rajivsam/dd-parser-cleaner
3. Numeric representation and featurization using the established numeric workflow, such as those in https://github.com/rajivsam/featurization

Under this assumption, `structure_id` consumes a tabular dataset where rows and columns are already valid, typed, and suitable for downstream structure analysis.

## What the package detects

`structure_id` identifies and reports:

- redundant feature blocks using normalized mutual information (NMI) screening on prepared numeric features
- explicit row clusters or macro-populations using density-aware clustering
- latent structural breaks using residual-based fluctuation tests
- structure stability between a discovery dataset and a held-out comparison dataset
- analyst-facing summary artifacts for documentation, model review, and downstream diagnostics

## Installation

Install from the repository root:

```bash
pip install -e .
```

Or, if using a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Dependencies

The package currently depends on:

- numpy
- pandas
- scipy
- scikit-learn
- hdbscan

These are used for feature screening, clustering, residual modeling, and numerical analysis.

## Quick start

```python
import pandas as pd
from structure_id import structure_id

# Data is expected to be already cleaned and numerically prepared upstream.
df = pd.read_csv("prepared_dataset.csv")

result = structure_id(
    data=df,
    target="target_variable",
    task_type="classification",
    structural_covariates=["known_structural_feature"],
)

print(result.diagnostics["report"])
```

The package returns a structured result object that includes:

- explicit feature blocks
- explicit row clusters
- latent structural break findings
- selected and provisional columns
- diagnostics and reporting artifacts

## Typical workflow

A standard usage pattern is:

1. Validate the dataset, target column, and task type.
2. Exclude invalid, invariant, missing-heavy, or otherwise unusable columns.
3. Screen the remaining numeric features for redundancy using normalized mutual information.
4. Detect dense row clusters or macro-populations.
5. Fit a baseline model and test residual behavior for latent structural breaks.
6. Produce an analyst-facing report and cluster profile outputs.

This is a discovery-first workflow designed to reveal the internal architecture of the dataset before more prescriptive modeling steps are taken.

## Partition-aware analysis

The package supports explicit training/validation/test-style partitioning so that structure is discovered from the training or analysis data while withholding held-out partitions for stability checks.

```python
from structure_id import PartitionedDataset

base = PartitionedDataset.from_dataframe(df)
base.set_partition_logic("training", lambda d: d.iloc[:800])
base.set_partition_logic("validation", lambda d: d.iloc[800:950])
base.set_partition_logic("test", lambda d: d.iloc[950:])

train_df = base.select_partition("training")
validation_df = base.select_partition("validation")
test_df = base.select_partition("test")
```

This supports the intended model-development workflow:

- discover structure on the training or discovery dataset
- assess whether the same structure is stable on validation or test partitions
- interpret differences as structural drift or instability diagnostics, rather than as a hard failure by default

## Descriptive analytics and drift assessment

The package is intentionally designed around descriptive analytics. The training or discovery dataset is treated as the primary dataset for learning the structure of the population. The test dataset is used as a structural stability check to see whether the discovered structure remains similar.

When the structure differs between the training and test data, the package reports the descriptive differences in cluster distributions, noise rates, and residual structure so the analyst can inspect potential drift, distributional change, covariate shift, or other upstream data changes. This is a diagnostic workflow for understanding whether the operating population has changed, rather than a hard pass/fail gate.

This framing is appropriate for enterprise analytics teams that need to answer questions such as:

- Is the data internally heterogeneous?
- Are there sub-populations that need separate treatment?
- Is the discovered structure stable across held-out data?
- If not, what appears to have changed?

## Data assumptions

`structure_id` assumes the following:

- the data is cross-sectional and not longitudinal or time-indexed
- cleaning and parsing are already complete upstream
- the features are in a numeric or numerically usable representation
- the target and task type are explicitly provided
- the analyst or data engineering pipeline has already managed validation/test partitioning logic

The package is designed for analytical clarity and enterprise reproducibility, not for raw-data reconstruction or source ingest workflows.

## API overview

The package exposes:

```python
from structure_id import structure_id
```

The main function signature is:

```python
result = structure_id(
    data=df,
    target="target_column",
    task_type="classification",
    structural_covariates=None,
    config=None,
)
```

The result object contains the discovered structure and reporting data, including:

- `target`
- `task_type`
- `provisional_columns`
- `selected_columns`
- `explicit_column_structures`
- `explicit_row_clusters`
- `latent_break`
- `diagnostics`

## Reporting

The package generates analyst-facing summaries and can export training cluster profiles as markdown or HTML reports. These outputs are designed to support internal review, model governance, and downstream analysis documentation.

## Design principles

The implementation follows a few core design principles:

- preserve leakage boundaries between discovery and validation/test data
- operate on cleaned, prepared numeric data rather than duplicating upstream processing
- keep structure discovery descriptive and explainable
- support analyst review through explicit summaries and diagnostics
- maintain a clear distinction between explicit and latent sources of heterogeneity

## Limitations

`structure_id` is intentionally narrow in scope. It is designed for:

- cross-sectional tabular data
- prepared numeric feature representations
- descriptive discovery and drift diagnostics

It is not intended to replace:

- raw-data cleaning pipelines
- source acquisition or verification workflows
- longitudinal or panel analysis tooling
- full forecasting or time-series infrastructure

## Repository structure

```text
structure_id/
    api.py
    config.py
    dataset.py
    explicit_structure.py
    latent_structure.py
    reporting.py
    types.py
    validation.py
notebooks/
    sba_structure_ident.ipynb
reports/
    ...
tests/
    ...
```

## Contributing

Contributions should remain aligned with the package’s purpose:

- preserve the upstream/downstream responsibility boundary
- keep the implementation interpretable and reproducible
- maintain a strict distinction between data preparation and structure discovery
- ensure held-out validation remains a structure stability check rather than a hidden redefinition of the structure

## Summary

`structure_id` provides a disciplined, enterprise-oriented approach to structure discovery for prepared cross-sectional datasets. It helps analysts identify where a dataset is internally heterogeneous, where model behavior may be unstable, and whether the discovered structure remains stable in held-out data.

It is a tool for understanding the architecture of data before finalizing modeling decisions, not a replacement for upstream data engineering or raw-data preparation.
