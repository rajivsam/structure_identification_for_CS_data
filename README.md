# structure_id

`structure_id` is a lightweight Python package for helping KMDS users answer a practical question: does this dataset contain meaningful heterogeneity, and if so, what is the explicit accounting for it?

The package is designed for cross-sectional datasets and focuses on identifying both:

- explicit structure: redundant feature blocks, dense macro-clusters of observations, and obvious sub-populations
- latent structure: hidden instability in the predictive relationship, revealed through residual-based structural-break detection

This helps analysts decide whether a single global model is appropriate or whether the data should be treated as a mixture of distinct subgroups with different behavior.

## Why this matters

In many applied datasets, a single model can look reasonable overall while quietly failing in important subgroups. `structure_id` gives a structured view of the data architecture so users can see:

- which features are effectively redundant
- whether rows form dense clusters or macro-populations
- whether model errors change systematically across candidate variables
- where a dataset is likely to be heterogeneous before modeling decisions are finalized

## What it detects

- redundant feature blocks using correlation-based screening
- explicit row clustering for macro-population discovery
- residual-based latent heterogeneity tests for structural breaks
- partition-aware training/validation/test workflows that preserve leakage boundaries
- analyst-facing summaries for downstream reporting and model review

## Quick start

```python
from structure_id import structure_id

result = structure_id(
    data=df,
    target="loan_status_r",
    task_type="classification",
    structural_covariates=["grossapproval"],
)

print(result.summary())
```

## Typical workflow

1. validate the dataset, target, and task type
2. screen out invalid or degenerate variables
3. detect redundant feature blocks and sparse/overrepresented categories
4. cluster rows to find explicit subpopulations
5. test for latent structural breaks using model residuals
6. summarize the results for modeling and reporting

## Partition-aware modeling

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

The package keeps the train/validation/test boundary explicit so structure discovered from training data can be applied without leakage into held-out partitions.

## Scope

This package is intended for cross-sectional data and is not designed for time-series, longitudinal, or panel workflows.

## Notes

The implementation follows the repository requirements for explicit and latent structure discovery while keeping the code modular, testable, and suitable for analyst-facing reporting.
