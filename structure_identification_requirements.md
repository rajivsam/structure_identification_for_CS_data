# Requirements Specification: Structure Identification in Cross-Sectional Datasets (structure_id)

Version: 1.0
Status: Proposed specification

## 1. Purpose

The purpose of the structure_id package is to identify and describe the internal architecture of a cross-sectional dataset by separating:

- Explicit structures: observable patterns in the prepared feature space, including redundant feature blocks and dense macro-clusters of observations.
- Latent structures: hidden instability in the predictive relationship, revealed through model residual behavior and structural-break detection.

The package shall support data analysts and machine learning practitioners in understanding where a dataset appears to be composed of distinct sub-populations and where a global predictive model is likely to break down.

The package shall be treated primarily as a descriptive structure-discovery tool. Its core purpose is to identify the descriptive structure in a dataset and to support model-development work by helping analysts understand the architecture of the data before finalizing a global modeling strategy. This is a sophisticated and highly relevant use case for applied machine-learning workflows.

The package shall also support comparison workflows in which different segments of a dataset, or different instances of a dataset, are compared to assess whether they are structurally similar. This capability is useful in two principal settings:

1. At model-development time, to determine whether the development environment is drifting.
2. At operational time, to determine whether drift has occurred.

In both cases, rigorous statistical testing for feature drift shall be the recommended formal verification method. Structure assessment on potentially drifting datasets shall therefore be treated primarily as a diagnostic and verification modality, not as a replacement for formal drift testing. The discovery dataset — typically the training partition or the primary analysis dataset — is the dataset on which the structure is learned and described. Held-out partitions are then used as a structural stability check, and the package shall report descriptive differences in cluster distributions, noise rates, and residual structure so the analyst can inspect potential shifts without imposing a hard pass/fail rule.

The package is intended for cross-sectional data only and is not designed for time-series, longitudinal, panel, or repeated-measures datasets.

## 2. Scope

### 2.1 In Scope

The package shall support:

- dataset ingestion from tabular data that has already passed cleaning and numeric featurization
- target and task validation
- explicit feature redundancy filtering on preprocessed numeric features
- explicit row clustering / macro-population discovery
- latent structural-break detection using residual-based fluctuation tests
- output generation for analysts and downstream modeling workflows

### 2.2 Out of Scope

The package shall not support:

- dataset downloading, source verification, or raw ingestion from external repositories
- parser-specific or schema-specific cleaning logic for messy source files
- longitudinal or temporal modeling assumptions
- within-unit tracking or repeated measurements
- explicit forecasting or time ordering
- automatically fitting model ensembles for all possible partition variable combinations without a valid structural baseline

### 2.3 Upstream Data Pipeline Assumption

This package is intentionally scoped to the structure-discovery layer. It assumes the upstream data pipeline has already performed the following steps:

1. dataset acquisition and verification via the KMDS dataset utility stack, such as https://github.com/rajivsam/kmds-dataset-util
2. parsing and cleaning via explicit cleaning workflows, such as https://github.com/rajivsam/dd-parser-cleaner
3. numeric representation and featurization via explicit numeric-features workflows, such as https://github.com/rajivsam/featurization

Under this assumption, the structure_id package consumes a tabular dataset in which columns are already cleaned, typed, and in a numeric form suitable for redundancy analysis and downstream modeling. This package does not re-implement cleaning, source verification, or feature engineering workflows.

## 3. Definitions

### 3.1 Dataset

A dataset D is a tabular, row-wise data structure where:
- each row represents one observation
- each column represents one variable or feature
- variables are assumed to have already passed upstream cleaning and numeric representation steps
- the structure_id package operates over a numerically usable representation and does not redefine raw source cleaning or parser logic

### 3.2 Target

Y is the variable to be predicted or explained. It shall be supplied as a named column in D or as a separate aligned vector matching the row count of D.

### 3.3 Task Type

T is the modeling type:
- regression
- classification

The task type shall be explicitly specified and shall determine the baseline model objective and residual interpretation.

### 3.4 Structural Covariates

X is an optional set of variables known to be legitimate structural predictors. These variables shall be excluded from candidate partitioning tests but may still be used in the baseline model.

### 3.5 Candidate Partitioning Variables

Z is the pool of variables evaluated as possible drivers of heterogeneity. Candidate variables shall exclude:
- Y
- X
- invariant columns
- blocked or invalid columns

### 3.6 Explicit Structure

Explicit structures are observable and directly measurable in the feature space:
- redundant feature blocks (collinear variables)
- dense row clusters or macro-populations

### 3.7 Latent Structure

Latent structures describe hidden changes in the predictive relationship that are not visible in raw coordinates alone. These are inferred from the behavior of model errors or residuals.

A latent structure is a statistically significant break or instability in the model relationship along a candidate variable.

## 4. Inputs

The package shall accept the following required and optional inputs.

### 4.1 Required Inputs

1. Dataset D
   - A tabular dataset containing observations and variables.
   - Must not be empty.

2. Target column Y
   - Name of the target variable to predict or explain.
   - Must exist in D or be supplied as a valid aligned vector.

3. Task type T
   - Either regression or classification.
   - Any other value shall raise a validation error.

### 4.2 Optional Inputs

1. Structural covariates X
   - Optional list of variables known to be structural predictors.
   - Variables in X shall be excluded from partitioning candidates.

2. Configuration object
   - A dictionary or object containing thresholds and behavioral settings.

### 4.3 Required Configuration Parameters

The following parameters shall be supported with default values:

- mutual_information_threshold: default 0.85
  - primary redundancy tolerance for feature block detection in the normalized mutual-information (NMI) formulation
  - the canonical threshold used when the package is operating on preprocessed numeric features

- correlation_threshold: default 0.85
  - legacy compatibility alias retained for existing calling code and notebooks
  - if provided without mutual_information_threshold, it shall be treated as equivalent to the MI threshold for backward compatibility

- min_cluster_size: default 15
  - minimum cluster size for explicit row clustering

- alpha: default 0.05
  - significance threshold used for latent break detection

Additional filtering thresholds shall be supported:

- std_threshold: default 1e-5
  - minimum numerical variance required to retain a feature

- max_missing_ratio: default 0.20
  - maximum missingness allowed for a candidate variable

- max_categories: default 30
  - maximum number of unique categories allowed for categorical variables in the categorical path

- max_class_concentration: default 0.98
  - maximum proportion allowed for the dominant category before exclusion

The package assumes that cleaning and upstream numeric encodings have already been completed. Therefore, the redundancy stage shall primarily operate on already-tabular numeric columns; categorical handling is supported only for compatibility with mixed datasets and for downstream row-clustering encodings, not as a substitute for upstream normalization or cleaning.

### 4.4 Input Validation Rules

The package shall validate input before processing.

It shall raise a clear error if any of the following conditions occur:

- D is empty
- Y is missing
- Y does not exist in D when supplied as a column name
- T is not one of regression or classification
- required columns are missing or mismatched
- row count or column count is invalid
- all candidate variables are rejected during the preparation stage

## 5. Functional Requirements

## 5.1 Data Preparation and Candidate Selection

The package shall implement a candidate-selection stage before hypothesis testing.

### 5.1.1 Structural Exclusion

The system shall automatically exclude from the candidate set Z:
- the target variable Y
- any designated model regressors X
- any constant or near-constant variables
- columns with unacceptable missingness
- variables rejected by type-specific integrity rules

### 5.1.2 Variance and Invariance Filtering

The package shall drop any numerical column where:
- the number of unique non-null values is 1
- the standard deviation is below std_threshold

The package shall drop any categorical column where:
- a single class level accounts for more than max_class_concentration of the rows
- the variable is degenerate for downstream testing

### 5.1.3 Missingness Handling

For each candidate column:
- if missingness exceeds max_missing_ratio, the variable shall be rejected
- if missingness is below the threshold:
  - the package shall assume upstream cleaning has already converted raw missingness to a valid representation
  - categorical missing values may be recoded as a named category "__MISSING__" only as a compatibility fallback for mixed-source input
  - numerical missing values may be median-imputed only as a local preprocessing convenience within the structure pipeline

This requirement is intentionally compatible with upstream pipelines such as the KMDS dataset utility, dd-parser-cleaner, and the numeric featurization workflows, which are expected to perform the authoritative source cleaning and representation logic before structure discovery begins.

### 5.1.4 Type Mapping

Each surviving variable shall be assigned to one of two processing paths:

- Continuous path:
  - float and integer columns in the numeric representation
  - used in continuous ordering-based structural tests and in the explicit feature redundancy analysis

- Categorical path:
  - string, object, boolean, and low-cardinality integer-like labels used as compatibility paths for mixed input data
  - used in categorical or group-based distribution tests after the upstream dataset has already been normalized

### 5.1.5 Provisional Candidate Count

The number of candidate variables that survive preprocessing shall be recorded as:
- l_provisional

This value shall be used in downstream multiple-testing adjustment to avoid penalizing untestable or invariant noise variables.

### 5.1.6 Partition-Aware Model Development Workflow

The package shall support the standard supervised-learning workflow in which a dataset is partitioned into disjoint training, validation, and test subsets before model development and evaluation.

#### Partition Selection

The dataset shall support a partition-selection interface of the form:
- select_partition(partition)

The method shall return the subset of rows assigned to the requested partition.

The partition selector shall support at least the following partition labels:
- training
- validation
- test

The user shall provide the row-selection logic for each partition, and the package shall require that partition assignments are non-overlapping and consistent with the selected dataset definition. If duplicate partition indicators are present (for example `dataset_partition` and `dataset_split`), the package shall validate that they encode the same assignment and allow either field to serve as the selector. Partition membership shall be explicitly traceable in the model output and diagnostics.

#### Training, Validation, and Test Workflow

The package shall support the common workflow in which:
- the training partition is used to fit the model and derive feature mappings,
- the validation partition is used to tune model parameters and compare alternative configurations,
- the test partition is reserved for final performance evaluation and for structural-stability checks.

The system shall enforce a leakage-prevention rule such that the model learned on the training partition is not refit using information from the validation or test partitions when applying the learned feature transformations.

For structure discovery, the primary discovery dataset shall remain the training or analysis dataset. The validation and test partitions shall not be used to redefine the learned structure; instead, they shall be evaluated for structural preservation using the training-derived feature mappings and learned structure logic. The package shall record the degree of structural agreement or disagreement in the diagnostics and report it as a drift or stability assessment.

#### Feature Application Methods

The package shall provide explicit functions to apply the feature engineering or model-derived transformations learned on the training partition to the held-out partitions:
- apply_training_features(...)
- apply_validation_features(...)
- apply_test_features(...)

The training feature-application method shall construct the feature representation from the training data and retain any learned state required for downstream transformation.

The validation and test feature-application methods shall reuse the training-derived feature logic and transform the corresponding subsets without re-estimating the training model parameters.

These methods shall be expected to support both raw feature transformations and model-based feature extraction, and shall clearly record any learned state, excluded variables, and feature transformations applied.

#### Convenience Selection of Featurized Attributes

The package shall provide a convenience method for retrieving only the featurized attributes needed for model training or evaluation.

The method shall support a user-specified attribute list:
- select_featurized_attributes(attribute_list)

This method shall return the dataset subset containing only the requested featurized attributes, preserving row identity and any associated partition labels. It shall be used to isolate the final feature set for downstream modeling, diagnostics, and reporting.

The attributes passed to this method shall be explicitly validated, and any missing or invalid requested fields shall raise a clear error.

## 5.2 Stage 1: Explicit Column Structure Identification and Filtering

The package shall identify redundant feature blocks in the feature space after the upstream cleaning and numeric-featurization steps have already been executed.

### 5.2.1 Leakage Prevention

The target variable Y and structural regressors X shall be excluded from all candidate partitioning analysis.

### 5.2.2 Pairwise Redundancy Mapping

For all remaining continuous attributes in the already-preprocessed numeric representation:
- compute a pairwise normalized mutual-information (NMI) matrix
- convert it to a redundancy-distance matrix
- define distance as:
  D = 1 - NMI

This package shall treat mutual information as the canonical redundancy metric, because the upstream numerical featurization step is expected to have converted raw features into a stable numeric form before structure discovery. The redundancy analysis shall therefore operate on numeric columns rather than on raw parser output or mixed-source objects.

### 5.2.3 Hierarchical Clustering

The system shall apply hierarchical complete-linkage clustering to the distance matrix.

A cluster shall be cut at:
- height = 1 - mutual_information_threshold

For backward compatibility, an alias named correlation_threshold may be provided and interpreted as the equivalent redundancy threshold for the MI formulation. This shall produce groups of redundant variables.

### 5.2.4 Representative Feature Selection

For each cluster containing more than one variable:
- select the single variable with the highest variance as the representative feature
- log the remaining variables as dropped due to multivariable clustering

### 5.2.5 Column Filtering Output

The package shall retain the set of representative columns and exclude redundant columns from the active candidate set.

The output shall record:
- cluster id
- representative variable
- dropped variables
- method used
- threshold value

### 5.2.6 Candidate Count Revision

The total number of surviving representative features, plus naturally independent features, shall define the post-filter candidate count:
- l

## 5.3 Stage 2: Explicit Row Structure and Macro-Population Identification

The package shall detect dense macro-structures in the row space.

### 5.3.1 Row-Level Clustering

The system shall perform row clustering using a density-based method such as HDBSCAN on the surviving feature space.

### 5.3.2 Inclusion Rules

A row cluster shall be considered valid if:
- it contains at least min_cluster_size observations
- it is sufficiently coherent under the selected density method
- it is not labeled as noise or background

Rows that do not belong to a valid cluster shall be assigned to background noise.

### 5.3.3 Explicit Row Output

The package shall output:
- macro-cluster labels
- cluster sizes
- rows assigned to each cluster
- noise assignment
- cluster-level summaries

### 5.3.4 Use in Reporting

Macro-clusters shall be included in the final analyst report as explicit structures and may also be used to inform latent heterogeneity searches within sub-populations.

### 5.3.5 `structure_id` Feature and Instance-Level Structure Reporting

The package shall create a row-level structure feature named `structure_id` when the instance-level clustering step is executed on the selected representative features.

The `structure_id` feature shall satisfy the following rules:

- rows assigned to valid HDBSCAN clusters shall receive the numeric cluster id
- rows labeled as noise by HDBSCAN shall receive the literal value `noise`
- the value shall be appended to the final selected feature set for analyst inspection and downstream model use
- the feature shall be reported in the diagnostics and summary output so that the user can read cluster membership directly from the data

This feature shall be generated after the explicit feature-reduction step and based on the surviving representative features only, preserving the intended ordering of operations:

1. detect and collapse redundant feature blocks
2. retain representative features
3. cluster data instances in the reduced feature space
4. append `structure_id` to the final feature set and report the distribution

The package shall not treat instance-level `structure_id` assignments as a replacement for explicit feature-block detection; instead, it shall be reported as a complementary row-level structure summary.

### 5.3.6 Cluster Profiling for Training Data

The package shall support an analyst-facing profile of the training data that summarizes how each detected instance cluster differs from the overall training distribution.

This profiling layer shall include:

- a basic profile section summarizing cluster size and the top distinguishing features per cluster
- an interpretive summary describing the direction and magnitude of each cluster's strongest separation from the overall dataset
- the training-only context, so the report reflects the cluster characteristics learned on the training partition rather than on held-out data

The training cluster profile shall be computed from the feature matrix after feature reduction and `structure_id` assignment, and shall be used for analyst interpretation, not for refitting the model on validation or test partitions.

### 5.3.7 Structural Stability Check on Held-Out Data

The package shall support a held-out structure-preservation assessment in which the learned discovery structure is evaluated on validation or test partitions without re-estimating the structural model from the held-out rows.

This requirement shall be satisfied by:

- applying the training-derived feature representation to validation/test partitions
- using the frozen training-based structure logic to assign `structure_id` values on held-out rows when applicable
- comparing the resulting explicit structures and latent-break findings against the training-discovery results
- reporting descriptive differences in cluster distributions, noise rates, and residual structure so the analyst can inspect potential shifts without imposing an arbitrary pass/fail threshold

The held-out analysis shall therefore be treated as a comparative diagnostic. It shall record differences in discovered structure across partitions and flag them for analyst review when there may be a shift in the underlying operating population or data-generation process.

## 5.4 Stage 3: Latent Structure Detection via Residual-Based Heterogeneity Testing

The package shall detect where the underlying predictive relationship changes.

### 5.4.1 Baseline Model

The package shall fit a global baseline model using only structural covariates X, or, if X is empty, the remaining valid non-partitioning design variables.

Model type shall depend on task type:
- regression: continuous target model
- classification: probabilistic or logit-based model

### 5.4.2 Residual Extraction

The system shall extract residuals or empirical scores from the fitted baseline model:
- regression: raw residuals
- classification: deviance or martingale-like residuals

### 5.4.3 Variable Scanning

For each candidate variable Zj in the candidate pool:
- sort the residuals according to the ordering of Zj
- construct a cumulative fluctuation process
- compute the supremum statistic:
  lambda = max |Wn(t)|

### 5.4.4 Statistical Testing

The package shall derive raw p-values for each candidate through the asymptotic distribution associated with the fluctuation process.

### 5.4.5 Multiple Testing Correction

To prevent false positives:
- apply Bonferroni adjustment using the number of valid candidates
- adjusted p-value:
  p_adjusted = min(p_raw × l, 1.0)

### 5.4.6 Decision Rule

The candidate with the smallest adjusted p-value below alpha shall be identified as the primary latent driver if one exists.

If no candidate satisfies:
- p_adjusted < alpha

then the system shall conclude that no statistically significant latent structural break was detected.

## 5.5 Final Result Assembly

The system shall consolidate all findings into a single result object or equivalent structured output.

This output shall include:
- explicit column structures
- explicit row structures
- latent heterogeneity results
- diagnostics
- warnings and exclusions
- final analyst report summary

## 6. Output Requirements

The package shall produce a structured result object that includes the following sections.

### 6.1 Explicit Column Structures

For each detected redundant feature block:
- cluster id
- representative feature
- dropped features
- clustering method
- similarity threshold
- number of features in cluster
- merge history of the clustered pairs
- pairwise normalized mutual-information (NMI) values used to define redundancy
- full redundancy matrix for the cluster members

### 6.2 Explicit Row Structures

For each valid macro-cluster:
- cluster id
- size
- assigned row indices or row counts
- noise rows
- cluster-level summary statistics

### 6.3 Latent Structures

For each detected latent break:
- candidate variable name
- statistic
- p_raw
- p_adjusted
- alpha threshold
- whether significant
- cutpoint or ordered break region
- affected rows or observation ranges
- model diagnostic context

If no latent structure is found:
- the result shall explicitly set the driver to null
- the report shall state “No statistically significant latent structure detected”

### 6.4 Diagnostics

The output shall include:
- number of rows
- number of original columns
- dropped features and reasons
- candidate count l_provisional
- candidate count l after feature filtering
- task type
- source of structural covariates
- warnings and assumptions

### 6.5 Report

The package shall generate a human-readable analyst report summarizing:
- dataset overview
- explicit structures found
- latent instability findings
- decision support for downstream model design

### 6.6 Training Cluster Profile and Export Artifacts

The package shall generate an additional analyst-facing cluster profile for the training data when instance-level structure assignments are available.

This profile shall include:

- a summary section reporting total noise rows and valid cluster count
- a per-cluster section listing the cluster size and the top numerical features distinguishing that cluster from the overall training distribution
- an interpretive summary explaining whether the cluster is generally higher or lower than the overall population on its strongest discriminating features
- export support to generate a markdown report and an HTML report in a designated output directory

The markdown and HTML outputs shall be saved as separate files so that analysts can read them in notebooks, terminal sessions, or external documentation tools.

The package shall support the display of this report directly in notebook environments, allowing the generated markdown summary to be rendered inline as part of the workflow.

The cluster profile shall remain grounded in the training partition and shall explicitly preserve the logic that the training partition is where model-derived feature mappings and structure discovery are learned.

## 7. Validation and Error Handling

The package shall fail fast with actionable error messages for invalid inputs.

### 7.1 Fatal Validation Errors

The package shall halt execution on:
- empty input dataset
- missing target
- unsupported task type
- invalid column references
- mismatched target length
- no valid candidate variables after preprocessing

### 7.2 Non-Fatal Warnings

The package shall issue warnings for:
- near-constant columns omitted
- highly imbalanced categorical variables excluded
- missing values imputed or encoded
- no latent driver detected
- low candidate count after filtering

## 8. Non-Functional Requirements

### 8.1 Cross-Sectional Restriction

The system shall assume independent observations. No temporal ordering, panel structure, or repeated-measures logic shall be applied.

### 8.2 Distribution-Free Orientation

The package shall avoid rigid parametric assumptions wherever possible and prefer robust rank-based or residual-based procedures.

### 8.3 Statistical Rigor

All significance tests shall be explicitly traced to:
- the underlying test statistic
- the p-value derivation
- the multiple-testing adjustment
- the decision threshold

### 8.4 Reproducibility

The package shall preserve:
- random state where applicable
- configuration values used
- deterministic ordering of outputs when possible

## 9. Acceptance Criteria

The requirement shall be considered satisfied when all of the following are true:

1. The package accepts a tabular dataset, target, and task type.
2. It rejects invalid or empty inputs with clear errors.
3. It excludes Y and X from candidate partitioning.
4. It filters out constant, near-constant, degenerate, and overly missing columns.
5. It identifies redundant feature blocks using normalized mutual information on the already-preprocessed numeric representation.
6. It detects macro-clusters in row space using a density-based method.
7. It fits a valid baseline model and extracts residuals.
8. It scans candidate variables for latent instability.
9. It applies a multiple-testing correction.
10. It produces an output containing explicit and latent structures with analyst-readable summaries.
11. The implementation assumptions are consistent with the upstream KMDS data pipeline: source cleaning, dataset verification, and numeric featurization are treated as upstream responsibilities and not duplicated inside structure_id.

## 10. Recommended Minimal API Shape

A recommended interface is:

```python
result = structure_id(
    data=D,
    target="Y",
    task_type="regression",
    structural_covariates=["X1", "X2"],
    config={
        "mutual_information_threshold": 0.85,
        "correlation_threshold": 0.85,
        "min_cluster_size": 15,
        "alpha": 0.05,
        "std_threshold": 1e-5,
        "max_missing_ratio": 0.20,
        "max_categories": 30,
        "max_class_concentration": 0.98,
    },
)

train_data = D.select_partition("training")
validation_data = D.select_partition("validation")
test_data = D.select_partition("test")

train_features = model.fit(train_data)
validation_features = model.apply_validation_features(validation_data)
test_features = model.apply_test_features(test_data)
featurized_subset = D.select_featurized_attributes(["X1", "X2", "X3", "X4"])
```

The result should be a structured object with:
- explicit_column_structures
- explicit_row_structures
- latent_structures
- diagnostics
- report

## 11. Summary

This specification defines the package as a cross-sectional structure-discovery framework that:
- separates explicit and latent architecture,
- protects against invalid candidate variables,
- identifies redundant columns and dense macro-populations in a numerically preprocessed dataset,
- tests for residual-based structural breaks,
- and reports the final outputs in a structured and analyst-friendly form.

The package explicitly assumes that cleaning, dataset verification, and numeric featurization are handled upstream by the KMDS workflow stack, including the dataset utility, parser-cleaner, and featurization repositories. The structure_id package therefore provides the downstream discovery logic rather than re-implementing data-source preparation.
