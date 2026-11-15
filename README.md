# structure_id

`structure_id` is a Python package for identifying and characterizing the descriptive structure of a cross-sectional dataset. It is designed for model-development and monitoring workflows where the goal is to understand how the data is organized before committing to a single global model or downstream analytical strategy.

The package can also be used to compare different segments of the same dataset—or different instances of the same data-generating process—to determine whether they are structurally similar. This is useful both:

1. during model development, to assess whether development is occurring in a drifting environment
2. in operational settings, to detect whether drift has emerged over time

Formal statistical testing remains the recommended mechanism for verifying feature drift. Structure assessment is best understood as a diagnostic and interpretive layer: it helps analysts understand the data’s organization and instability, rather than replace formal drift testing.

The package focuses on two complementary forms of structure:

- Explicit structure: redundant feature blocks, dense row clusters, and macro-populations that are directly visible in the feature space
- Latent structure: hidden instability in the predictive relationship that emerges through residual-based structural-break detection

## Intended Use & Application Context

`structure_id` is designed as a descriptive analytical tool for understanding and characterizing the internal structure of a dataset. It is intended to support model-development and monitoring decisions by revealing how the data is organized, where redundancy or heterogeneity is concentrated, and whether important structural changes are emerging over time or across conditions.

This package is not intended to replace formal statistical testing or to serve as a hard gate in automated model workflows. Instead, it provides a structured, analyst-facing view of the data to support interpretation, validation, and decision-making.

### Use Cases

**1. Understanding Sub-Populations in Discovery Data**
`structure_id` helps analysts summarize the populations and structures present in a dataset before committing to a single global modeling approach. It can reveal whether:
- the data violates independent, identically distributed (i.i.d.) assumptions
- distinct sub-populations warrant separate treatment
- a single global model is appropriate or whether stratified modeling is preferable

**2. Comparative Structure Assessment Across Time or Conditions**
The package can compare dataset structures across time windows, operational conditions, or held-out cohorts to:
- characterize the natural range of structural variation for a given model context
- assess whether operational conditions remain within acceptable bounds for performance SLAs
- diagnose performance degradation by identifying structural shifts between stable and degraded periods
- verify that held-out data reflects the same structural patterns as the discovery dataset

**3. Feature Development and Hypothesis Testing**
Discovered structure provides a foundation for more targeted analysis and experimentation. It can be used to:
- test hypotheses about the populations and structure identified in the data
- reason about meaningful feature directions and representations
- design validation studies that explicitly account for heterogeneity
- explore alternative feature-engineering strategies grounded in the observed structure

**4. Evolving Capability**
`structure_id` is intended as a foundation for continued analytical capability. As the tool is applied in real-world settings, feedback from practitioners will inform its refinement and extension. It is best viewed as a living analytical tool that grows with practical use and domain feedback.

### Important Caveats

- **Descriptive, Not Predictive:** Structure analysis is diagnostic, not prescriptive. It informs interpretation and decision-making, but it is not designed to act as a hard automated gate.
- **Variance-Accounting Perspective:** Prepared datasets often contain multiple sources of variance distortion—some direct, such as clustering and macro-population structure, and some indirect, such as feature correlation, redundancy, and latent heterogeneity. This tool is intended to expose those issues clearly so an analyst can recognize them once and carry that understanding forward across future datasets or related problem families without repeating the full diagnostic exercise.
- **Complement to Formal Testing:** Structure assessment is valuable for diagnosis and verification, but it should complement—not replace—rigorous statistical testing for feature drift and performance monitoring.
- **Qualitative Context Matters:** Discovered structure should be interpreted in light of domain knowledge and business context. The value of these patterns depends on analyst judgment, validation, and practical understanding.

## Enterprise use case

In enterprise machine learning workflows, a dataset can appear well behaved at the aggregate level while still containing important internal heterogeneity. A single global model may look acceptable on overall metrics while failing systematically in one or more subgroups.

`structure_id` provides a structured, analyst-friendly view of the dataset so teams can identify:

- redundant or near-duplicate features that do not add incremental information
- stable row clusters or macro-populations that may warrant separate treatment
- latent instability in the relationship between features and the target
- whether held-out data exhibits the same structure as the discovery dataset

The package is intended primarily for descriptive analytics and drift-oriented diagnostics. It is not framed as a strict predictive gate. Instead, it supports a disciplined assessment of whether discovered structure is stable and whether apparent differences between training and evaluation data are likely to reflect drift or other data changes.

## Scope and positioning

`structure_id` is a downstream structure-discovery tool. It assumes that upstream data preparation has already occurred and that the data entering this package is in a cleaned, numeric, analysis-ready tabular form.

This package does not replace the upstream KMDS pipeline responsibilities for:

- dataset acquisition and verification
- raw parsing and cleaning
- numeric featurization and preparation

It is intentionally designed to consume prepared tabular data and operate at the structure-discovery layer, where the goal is to understand the organization of the data rather than to transform it.

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
