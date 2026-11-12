
Module 0: Provisional Candidate Selection & Filtering Requirements


0.1 Objective

To programmatically scan, validate, and select a clean, high-signal subset of provisional features to act as partitioning candidates (Z), ensuring downstream Brownian Bridge and χ² tests remain computationally stable and statistically powerful.

0.1.1 Scope Restriction: Cross-Sectional Data Only

This module is explicitly scoped to cross-sectional data. It does not support longitudinal, panel, time-series, repeated-measures, or clustered temporal datasets. The candidate-selection logic assumes a single observational snapshot with independent rows and does not incorporate temporal ordering, unit tracking, or within-subject dependence.
+--------------------------------------------------------+

|                 RAW INPUT VARIABLES                    |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+

|         STEP 1: STRUCTURAL EXCLUSION FILTERS           |
|  - Drop targets/regressors (Y, X)                      |
|  - Drop Zero-Variance / Near-Constant columns          |
|  - Flag/Drop High-Cardinality categories (> Max Levels)|
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+

|       STEP 2: MODEL INTEGRITY FILTERS (MISSINGNESS)   |
|  - Drop columns with missingness > Missing Threshold   |
|  - Categorical missing: Impute as discrete level 'NA'  |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+

|       STEP 3: PROVISIONAL TYPE SELECTION MAPPING       |
|  - Type Continuous -> Continuous Brownian Bridge Test   |
|  - Type Nominal/Factor -> Discrete Chi-Square Test     |
+--------------------------------------------------------+
                           |
                           v
+--------------------------------------------------------+

|      FINAL FILTERED SUITE OF PROVISIONAL Z-CANDIDATES  |
+--------------------------------------------------------+

0.2 Functional Requirements


0.2.1 Structural Separation Filter

• Leakage Prevention Rule: The engine must automatically exclude the Target Variable (Y) and any features explicitly designated as Model Regressors (X) from being evaluated as partitioning candidates (Z).

0.2.2 Variance & Invariance Filter

• Constant Column Drop: The engine must drop any column where the number of unique non-null values is exactly equal to 1.
• Near-Zero Variance Rule: For numerical columns, the system must drop variables where the standard deviation drops below a configurable threshold (e.g., std_threshold = 1e-5).
• Dominant Category Drop: For categorical columns, if a single class level accounts for more than a configurable percentage of the total sample size (e.g., max_class_concentration = 0.98), the variable must be excluded to prevent degenerate, highly unbalanced tree branches downstream.

0.2.3 Missing Data & Completeness Strategy

• Hard Ceiling Drop: Any candidate column with a missing data percentage exceeding a strict configurable limit (default: max_missing_ratio = 0.20) must be rejected.
• Categorical Structural Handling: For categorical variables below the missing threshold, missing values must not be dropped. The engine must automatically recast nulls into a new explicit categorical level named "__MISSING__". This treats the act of omitting data as a potential structural subgroup.
• Continuous Masking/Imputation: For numerical variables below the missing threshold, the engine must flag missing data and apply a baseline median imputation prior to executing the continuous ordering phase of the Brownian Bridge test, or explicitly isolate them as an auxiliary discrete partition block.

0.2.4 Cardinality & Type Constraint Mapping

• High-Cardinality Factor Cap: The engine must reject any categorical column where the number of distinct levels (C) exceeds a structural threshold (default: max_categories = 30). This protects the Chi-square degrees of freedom (C-1) × k from blowing up and diluting the statistical power of the test.
• Semantic Casting Rule: Variables must be cataloged into exactly two processing paths based on data type:
	• Continuous Path: Float and Integer columns with unique value counts greater than max_categories are passed into the continuous sorting engine.
	• Categorical Path: String, Boolean, Object, and low-count Integer fields are cast into the categorical block engine.

0.3 Impact on Downstream Adjustments

• The final count of variables surviving this pre-processing step is designated as lprovisionall sub provisional end-sub
𝑙provisional
.
• Dynamic Bonferroni Rule: The engine must explicitly use lprovisionall sub provisional end-sub
𝑙provisional
 (the number of validated, eligible candidates) as the multiplier for the downstream multiple testing correction, rather than the count of raw columns in the input dataframe. This prevents the penalization of p-values by un-splittable or invariant noise columns.
Should the candidate selector also include an optional statistical screening filter—such as calculating a fast mutual information score between Z and Y to rank them before running the full MOB process—or do you prefer keeping it strictly restricted to data-integrity filters?
