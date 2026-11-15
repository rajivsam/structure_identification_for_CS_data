from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from .config import StructureIDConfig


def validate_inputs(
    data: pd.DataFrame,
    target: str,
    task_type: str,
    structural_covariates: list[str] | None = None,
) -> tuple[pd.DataFrame, str, list[str]]:
    if data is None or data.empty:
        raise ValueError("The input dataset is empty.")

    if not isinstance(data, pd.DataFrame):
        raise TypeError("The dataset must be a pandas DataFrame.")

    if target is None or target == "":
        raise ValueError("A target column name must be provided.")

    if target not in data.columns:
        raise ValueError(f"Target column '{target}' was not found in the dataset.")

    task_type = str(task_type).strip().lower()
    if task_type not in {"regression", "classification"}:
        raise ValueError("Task type must be one of: 'regression' or 'classification'.")

    covariates = [] if structural_covariates is None else list(structural_covariates)
    missing_covariates = [c for c in covariates if c not in data.columns]
    if missing_covariates:
        raise ValueError(
            "Structural covariates were provided but not found in the dataset: "
            + ", ".join(missing_covariates)
        )

    if target in covariates:
        raise ValueError("The target column cannot also be listed as a structural covariate.")

    return data.copy(), task_type, covariates


def validate_and_prepare_data(
    data: pd.DataFrame,
    target: str | pd.Series | np.ndarray,
    task_type: str,
    structural_covariates: list[str] | None = None,
    config: StructureIDConfig | None = None,
) -> tuple[pd.DataFrame, int, dict]:
    """
    Stage 0: Input Validation and Candidate Preparation
    
    Validates data, target, and task_type. Filters candidate features by:
    - Missing ratio threshold
    - Numeric column standard deviation
    - Categorical column cardinality
    - Class concentration
    
    Returns:
        (Z, l_provisional, diagnostics) where:
        - Z: DataFrame of candidate features (excluding target and structural_covariates)
        - l_provisional: Number of surviving candidate columns
        - diagnostics: Dictionary with filtering details
    """
    cfg = config or StructureIDConfig()
    
    # Validate and extract target
    if isinstance(target, str):
        if target not in data.columns:
            raise ValueError(f"Target column '{target}' not found in data.")
        y = data[target].copy()
    elif isinstance(target, (pd.Series, np.ndarray)):
        if len(target) != len(data):
            raise ValueError(f"Target length {len(target)} does not match data length {len(data)}.")
        y = target
    else:
        raise TypeError(f"Target must be column name, Series, or array, got {type(target)}.")
    
    # Validate task_type
    task_type = str(task_type).strip().lower()
    if task_type not in {"regression", "classification"}:
        raise ValueError(f"Task type must be 'regression' or 'classification', got {task_type}.")
    
    # Validate structural_covariates
    structural_covariates = structural_covariates or []
    missing_covariates = [c for c in structural_covariates if c not in data.columns]
    if missing_covariates:
        raise ValueError(f"Structural covariates not found: {missing_covariates}")
    
    # Identify candidate pool: exclude target and structural_covariates
    exclude_cols = {target} if isinstance(target, str) else set()
    exclude_cols.update(structural_covariates)
    candidate_cols = [c for c in data.columns if c not in exclude_cols]
    
    diagnostics = {
        "total_input_features": len(data.columns),
        "excluded_features": list(exclude_cols),
        "candidate_features_before_filtering": len(candidate_cols),
        "filtering_details": {},
    }
    
    Z = data[candidate_cols].copy()
    
    # Step 1: Drop columns with excessive missing values
    missing_ratios = Z.isnull().sum() / len(Z)
    high_missing = missing_ratios[missing_ratios > cfg.max_missing_ratio].index.tolist()
    if high_missing:
        Z = Z.drop(columns=high_missing)
        diagnostics["filtering_details"]["dropped_high_missing"] = high_missing
    
    # Step 2: Impute remaining numeric missing, encode categorical missing
    for col in Z.columns:
        if Z[col].isnull().any():
            if pd.api.types.is_numeric_dtype(Z[col]):
                median_val = Z[col].median()
                Z[col] = Z[col].fillna(median_val)
                warnings.warn(f"Imputed {col} with median: {median_val}")
            else:
                Z[col] = Z[col].fillna("__MISSING__")
                warnings.warn(f"Encoded missing values in {col} as '__MISSING__'")
    
    # Step 3: Drop numeric columns with low variance or insufficient unique values
    low_var_cols = []
    for col in Z.columns:
        if pd.api.types.is_numeric_dtype(Z[col]):
            std_val = Z[col].std()
            n_unique = Z[col].nunique()
            if std_val < cfg.std_threshold or n_unique <= 1:
                low_var_cols.append(col)
    
    if low_var_cols:
        Z = Z.drop(columns=low_var_cols)
        diagnostics["filtering_details"]["dropped_low_variance"] = low_var_cols
    
    # Step 4: Drop categorical columns with excessive cardinality or class concentration
    high_card_cols = []
    for col in Z.columns:
        if not pd.api.types.is_numeric_dtype(Z[col]):
            n_unique = Z[col].nunique()
            if n_unique > cfg.max_categories:
                high_card_cols.append(col)
            else:
                # Check class concentration
                class_freq = (Z[col].value_counts() / len(Z)).max()
                if class_freq > cfg.max_class_concentration:
                    high_card_cols.append(col)
    
    if high_card_cols:
        Z = Z.drop(columns=high_card_cols)
        diagnostics["filtering_details"]["dropped_high_cardinality"] = high_card_cols
    
    # Final validation: at least one candidate remains
    if Z.empty or len(Z.columns) == 0:
        raise ValueError("No valid candidate features survived filtering.")
    
    l_provisional = len(Z.columns)
    diagnostics["candidate_features_after_filtering"] = l_provisional
    diagnostics["surviving_features"] = Z.columns.tolist()
    
    return Z, l_provisional, diagnostics
