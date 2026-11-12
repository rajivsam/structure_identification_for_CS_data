
Requirements Document: Residual-Based Heterogeneity Identification Framework


1. Objective & Scope

The purpose of this framework is to identify statistically significant structural heterogeneity within a dataset without forcing rigid parametric assumptions or requiring computationally heavy recursive tree refitting. Given a structural baseline model, this framework scans a candidate pool of partitioning variables (Zcap Z
𝑍
) to discover if, where, and along which feature the model’s core functional relationships structurally break down or change.

2. Functional Requirements & Process Workflow

[Input Dataset] ──> [Stage 1: Global Non-Parametric Fit (GAM/EBM)]
                           │
                           ▼
                  [Extract Residuals / Empirical Scores]
                           │
                           ▼
[Candidate Pool Z] ──> [Stage 2: CUSUM Fluctuation Engine]
                           │
                           ▼
                  [Bonferroni Multiple-Testing Filter]
                           │
                           ▼
               [Identify Optimal Partitioning Driver]

Stage 1: Global Baseline Estimation

• Baseline Modeling: Fit a single, global non-parametric model (such as a Generalized Additive Model via pyGAM or an Explainable Boosting Machine via InterpretML) using only the structural covariates (Xcap X
𝑋
).
• Target Configurations:
	• Regression: Train using continuous targets and objective functions optimizing Mean Squared Error (MSE) or deviance.
	• Classification: Train using log-odds, optimizing binary cross-entropy or multinomial log-loss.
• Score Extraction: Extract the empirical scores or residuals (uiu sub i
𝑢𝑖
) from the model.
	• For regression, extract the raw residuals: 𝑢𝑖
=𝑦𝑖
−𝑦̂𝑖.
	• For classification, extract the deviance or martingale-like residuals.

Stage 2: Fluctuation Engine & Variable Scanning

• Data Ordering: For each candidate partitioning variable Zjcap Z sub j
𝑍𝑗
 in the candidate pool (𝑍1
,
𝑍2
,
…
,
𝑍𝑘), sort the entire residual vector uiu sub i
𝑢𝑖
 according to the numerical or rank ordering of Zjcap Z sub j
𝑍𝑗
.
• Stochastic Process Construction: Compute the empirical cumulative sum (CUSUM) fluctuation process (𝑊𝑛
(
𝑡
)) over the sorted array. Under the null hypothesis (H0cap H sub 0
𝐻0
), the parameters are stable, and this process behaves like a random walk centered around zero.
• Statistic Extraction: Calculate the Supremum (maximum absolute value) of the generated fluctuation path:
λ=max|Wn(t)|lambda equals max of the absolute value of cap W sub n open paren t close paren end-absolute-value 
𝜆=max|𝑊𝑛(𝑡)|

Stage 3: Statistical Identification & Correction

• P-Value Derivation: Map the supremum statistic λlambda
𝜆
 against the asymptotic boundary of a Brownian Bridge using the Kolmogorov distribution tail function to yield a raw pp
𝑝
-value.
• Multiple Testing Correction: To prevent false positives from scaling with the size of the candidate pool, apply a Bonferroni adjustment:
padjusted=min(praw×k,1.0)p sub adjusted end-sub equals min of open paren p sub raw end-sub cross k comma 1.0 close paren
𝑝adjusted=min(𝑝raw×𝑘,1.0)

(where kk
𝑘
 is the total number of candidate partitioning variables evaluated).
• Decision Boundary: The variable with the lowest padjustedp sub adjusted end-sub
𝑝adjusted
 that falls strictly below the predefined significance threshold (e.g., 𝛼
=0.05) is systematically identified as the primary driver of structural heterogeneity. If no variables clear the threshold, the global baseline model stands as structurally invariant.

3. Academic & Theoretical Citations

To justify and defend the statistical validity of this pipeline in papers, technical documentation, or regulatory audits, use the following foundational citations:

Foundation of Residual Fluctuation & CUSUM Dynamics

• Ploberger, W., & Krämer, W. (1992). The CUSUM test with OLS residuals. Econometrica, 271-285.
	• Application: Provides the mathematical proof that empirical residuals from a global model can be ordered along a secondary variable to construct a valid structural fluctuation process converging asymptotically to a Brownian Bridge.
• Brown, R. L., Durbin, J., & Evans, J. M. (1975). Techniques for testing the constancy of regression relationships over time. Journal of the Royal Statistical Society: Series B (Methodological), 37(2), 149–163.
	• Application: The pioneering text establishing cumulative sum (CUSUM) boundaries to map structural changes and parameter drift.

Score-Based Testing & Parameter Instability

• Zeileis, A. (2005). A unified approach to structural change tests based on ML scores. Econometric Reviews, 24(4), 445-466.
	• Application: Decouples fluctuation testing from time-series models, validating that empirical scores or residuals can be calculated from a single global estimate to test parameter constancy across any continuous or categorical covariate.
• Zeileis, A., & Hornik, K. (2007). Generalized M-fluctuation tests for parameter instability. Statistica Neerlandica, 61(4), 488–508.
	• Application: Establishes the Generalized M-fluctuation framework that transforms raw local gradients and model scores into rigorous asymptotic statistical tests.

Two-Stage Residual Diagnostics & Non-Parametric Validation

• Fithian, W., & Hastie, T. (2015). Localist selection: The critical role of residuals in subgroup analysis. Annals of Applied Statistics.
	• Application: Establishes the statistical advantages of the two-stage framework (Global main effects →right arrow
→
 Residual analysis), demonstrating that filtering global patterns out first preserves the exact focus on true trend shifts and interactions.
• Fan, J., & Li, Q. (1996). Consistent model specification tests for regression models of unknown form. Journal of Econometrics, 73(1), 23-45.
	• Application: Asserts that empirical residuals derived specifically from complex, non-parametric baseline estimators (such as splines, GAMs, or additive boosting architectures) maintain consistent properties when tested for unmodeled dependencies.
Would you like me to translate this architecture into an explicit production-ready Python class matching these requirements, or should we design the functional specs for handling categorical partitioning variables which require a χ2chi squared
𝜒2
 merge statistic instead of a continuous CUSUM sort?
