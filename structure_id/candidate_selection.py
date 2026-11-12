from __future__ import annotations

from collections import OrderedDict

import pandas as pd

from .config import StructureIDConfig


class CandidateSelector:
    def __init__(self, config: StructureIDConfig):
        self.config = config

    def select(self, data: pd.DataFrame, target: str, structural_covariates: list[str]) -> dict:
        excluded = {target, *structural_covariates}
        candidate_columns = [col for col in data.columns if col not in excluded]

        dropped: OrderedDict[str, str] = OrderedDict()
        selected: list[str] = []
        metadata: dict[str, dict] = {}

        for col in candidate_columns:
            series = data[col]
            if series.empty:
                dropped[col] = "empty column"
                continue

            missing_ratio = series.isna().mean()
            if missing_ratio > self.config.max_missing_ratio:
                dropped[col] = "missingness exceeds maximum threshold"
                continue

            non_null = series.dropna()
            if non_null.empty:
                dropped[col] = "all values missing"
                continue

            if pd.api.types.is_numeric_dtype(series):
                if non_null.nunique() <= 1:
                    dropped[col] = "constant numeric column"
                    continue
                if non_null.std(ddof=0) <= self.config.std_threshold:
                    dropped[col] = "near-zero variance"
                    continue
                selected.append(col)
                metadata[col] = {"kind": "continuous"}
                continue

            if non_null.nunique() <= 1:
                dropped[col] = "constant categorical column"
                continue

            dominant_ratio = non_null.value_counts(normalize=True).max()
            if dominant_ratio > self.config.max_class_concentration:
                dropped[col] = "dominant category concentration exceeds threshold"
                continue

            if non_null.nunique() > self.config.max_categories:
                dropped[col] = "categorical cardinality exceeds allowable threshold"
                continue

            selected.append(col)
            metadata[col] = {"kind": "categorical"}

        return {
            "selected_columns": selected,
            "dropped_columns": dropped,
            "provisional_count": len(selected),
            "feature_metadata": metadata,
        }
