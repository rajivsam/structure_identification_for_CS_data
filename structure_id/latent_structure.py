from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from .config import StructureIDConfig
from .types import LatentBreak


class LatentStructureDetector:
    def __init__(self, config: StructureIDConfig):
        self.config = config

    def _build_baseline_predictor(self, data: pd.DataFrame, target: str, candidate_columns: list[str], structural_covariates: list[str], task_type: str):
        model_columns = [
            col for col in data.columns if col not in {target, *candidate_columns} and col not in structural_covariates
        ]
        if structural_covariates:
            model_columns = [
                col for col in structural_covariates if col in data.columns
            ] + [
                col for col in model_columns if col not in structural_covariates
            ]

        if not model_columns:
            y = data[target].astype(float)
            if task_type == "regression":
                return lambda: y.mean(), y
            return lambda: np.full(len(y), y.value_counts(normalize=True).idxmax()), y

        X = data[model_columns].copy()
        y = data[target].astype(float)
        transform = ColumnTransformer(
            transformers=[
                ("num", "passthrough", X.select_dtypes(include=[np.number]).columns.tolist()),
                ("cat", OneHotEncoder(handle_unknown="ignore"), X.select_dtypes(exclude=[np.number]).columns.tolist()),
            ],
            remainder="drop",
        )

        if task_type == "regression":
            model = Pipeline([
                ("preprocess", transform),
                ("model", LinearRegression()),
            ])
            model.fit(X, y)
            return model.predict, y

        model = Pipeline([
            ("preprocess", transform),
            ("model", LogisticRegression(max_iter=2000)),
        ])
        model.fit(X, y)

        def predict_fn(frame):
            proba = model.predict_proba(frame)
            if proba.shape[1] == 1:
                proba = np.column_stack([1.0 - proba[:, 0], proba[:, 0]])
            return proba

        return predict_fn, y

    def detect(self, data: pd.DataFrame, target: str, task_type: str, candidate_columns: list[str], structural_covariates: list[str]):
        if not candidate_columns:
            return None

        predictor_fn, y = self._build_baseline_predictor(
            data,
            target,
            candidate_columns,
            structural_covariates,
            task_type,
        )

        if task_type == "regression":
            predictions = predictor_fn(data)
            residuals = y.to_numpy(dtype=float) - np.asarray(predictions, dtype=float)
        else:
            proba = predictor_fn(data)
            if proba.ndim == 1:
                prob_values = np.asarray(proba, dtype=float)
                residuals = y.to_numpy(dtype=float) - prob_values
            else:
                max_prob = proba.max(axis=1)
                residuals = y.to_numpy(dtype=float) - max_prob

        best: LatentBreak | None = None
        for col in candidate_columns:
            if col not in data.columns:
                continue

            series = data[col]
            if series.empty:
                continue

            values = series.fillna(series.median()) if pd.api.types.is_numeric_dtype(series) else series.astype("string").fillna("__MISSING__")
            if pd.api.types.is_numeric_dtype(values):
                ordered = np.argsort(values.to_numpy(dtype=float))
                ordered_values = values.to_numpy(dtype=float)[ordered]
                ordered_residuals = residuals[ordered]
            else:
                cat_map = {val: idx for idx, val in enumerate(sorted(pd.unique(values)))}
                encoded = values.map(cat_map).to_numpy(dtype=float)
                ordered = np.argsort(encoded)
                ordered_values = encoded[ordered]
                ordered_residuals = residuals[ordered]

            if ordered_residuals.size < 2:
                continue

            centered = ordered_residuals - ordered_residuals.mean()
            cusum = np.cumsum(centered)
            statistic = np.max(np.abs(cusum)) / np.sqrt(ordered_residuals.size)
            p_raw = float(stats.kstwobign.sf(statistic))
            p_adjusted = min(1.0, p_raw * max(1, len(candidate_columns)))
            significant = p_adjusted < self.config.alpha

            candidate_break = LatentBreak(
                variable_name=col,
                statistic=float(statistic),
                raw_p_value=float(p_raw),
                adjusted_p_value=float(p_adjusted),
                alpha=float(self.config.alpha),
                significant=bool(significant),
                cutpoint=float(ordered_values[np.argmax(np.abs(cusum))]) if len(cusum) else None,
                row_support=ordered.tolist(),
            )

            if best is None or candidate_break.adjusted_p_value < best.adjusted_p_value:
                best = candidate_break

        return best
