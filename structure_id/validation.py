from __future__ import annotations

import pandas as pd


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
