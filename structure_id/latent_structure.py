from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, LogisticRegression

from .config import StructureIDConfig


def detect_latent_breaks(
    Y: pd.Series | np.ndarray,
    Z_rep: pd.DataFrame,
    structural_covariates: list[str] | None = None,
    config: StructureIDConfig | None = None,
    data: pd.DataFrame | None = None,
) -> tuple[str | None, float | None, dict]:
    """
    Stage 4: Latent Heterogeneity Analysis (Residual Fluctuation Testing)
    
    Detect hidden instability in P(Y | X) along surviving features via
    ordered fluctuation testing on baseline model residuals.
    
    Args:
        Y: Target values (Series or array)
        Z_rep: Representative features DataFrame (original un-orthogonalized)
        structural_covariates: List of structural covariate column names
        config: StructureIDConfig
        data: Original data DataFrame (needed to access structural_covariates)
    
    Returns:
        (primary_driver, cutpoint, diagnostics)
    """
    cfg = config or StructureIDConfig()
    structural_covariates = structural_covariates or []
    
    # Convert Y to numpy array
    if isinstance(Y, pd.Series):
        y = Y.values
    else:
        y = np.asarray(Y)
    
    # Fit baseline model
    if data is not None and structural_covariates:
        X_baseline = data[structural_covariates].copy()
    else:
        X_baseline = None
    
    # Fit baseline model based on task_type
    # For simplicity, we'll assume we need to detect task type or accept it as param
    # Let's use a simple approach: check if Y is mostly binary/small integer
    y_unique = len(np.unique(y[~np.isnan(y)]))
    is_classification = y_unique <= 10 and np.all(np.isin(y, [0, 1, -1, np.nan], assume_unique=False))
    
    if X_baseline is not None and not X_baseline.empty:
        # Fit model with structural covariates
        if is_classification:
            model = LogisticRegression(max_iter=1000)
            try:
                model.fit(X_baseline.fillna(X_baseline.mean()), y)
                y_pred = model.predict_proba(X_baseline.fillna(X_baseline.mean()))[:, 1]
            except:
                y_pred = np.full_like(y, y.mean())
        else:
            model = LinearRegression()
            try:
                model.fit(X_baseline.fillna(X_baseline.mean()), y)
                y_pred = model.predict(X_baseline.fillna(X_baseline.mean()))
            except:
                y_pred = np.full_like(y, y.mean())
    else:
        # Baseline: intercept only
        y_pred = np.full_like(y, np.nanmean(y))
    
    # Compute residuals
    residuals = y - y_pred
    
    # Scan each feature in Z_rep for ordered fluctuation test
    results = []
    
    for col in Z_rep.columns:
        if not pd.api.types.is_numeric_dtype(Z_rep[col]):
            continue
        
        z_values = Z_rep[col].fillna(Z_rep[col].median()).values
        
        # Sort residuals by ascending z values
        sort_idx = np.argsort(z_values)
        z_sorted = z_values[sort_idx]
        res_sorted = residuals[sort_idx]
        
        # Compute ordered fluctuation test statistic
        # W_n(t) = (1/sqrt(n)) * sum_{i=1}^{nt} (e_i - mean(e))
        n = len(res_sorted)
        res_centered = res_sorted - np.mean(res_sorted)
        W_n = np.cumsum(res_centered) / np.sqrt(n)
        
        # Test statistic: λ = max|W_n(t)|
        lambda_stat = np.max(np.abs(W_n))
        
        # P-value from Brownian bridge approximation
        # Use Kolmogorov-Smirnov distribution
        p_raw = stats.kstwobign.sf(lambda_stat)
        
        # Bonferroni correction
        p_adj = min(1.0, p_raw * len(Z_rep.columns))
        
        # Find cutpoint (value of z where max fluctuation occurs)
        max_idx = np.argmax(np.abs(W_n))
        cutpoint = float(z_sorted[max_idx])
        
        results.append({
            "feature": col,
            "test_statistic": float(lambda_stat),
            "raw_p_value": float(p_raw),
            "adjusted_p_value": float(p_adj),
            "cutpoint": cutpoint,
            "significant": p_adj < cfg.alpha,
        })
    
    # Select primary driver (smallest adjusted p-value among significant results)
    significant_results = [r for r in results if r["significant"]]
    
    if significant_results:
        primary_result = min(significant_results, key=lambda r: r["adjusted_p_value"])
        primary_driver = primary_result["feature"]
        cutpoint = primary_result["cutpoint"]
    else:
        primary_driver = None
        cutpoint = None
    
    diagnostics = {
        "n_features_tested": len(Z_rep.columns),
        "n_significant_features": len(significant_results),
        "alpha": cfg.alpha,
        "test_results": results,
        "primary_driver": primary_driver,
    }
    
    return primary_driver, cutpoint, diagnostics
