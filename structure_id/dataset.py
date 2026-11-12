from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd


class PartitionedDataset(pd.DataFrame):
    """A pandas DataFrame with explicit partition and feature-application hooks.

    This keeps the DataFrame API intact while supporting the project requirement for
    training/validation/test dataset selection and train-derived feature application.
    """

    _metadata = [
        "_partition_logic",
        "_feature_history",
        "_training_feature_names",
        "_validation_feature_names",
        "_test_feature_names",
    ]

    def __init__(
        self,
        *args: Any,
        partition_logic: dict[str, Callable[[pd.DataFrame], Any] | Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._partition_logic = dict(partition_logic or {})
        self._feature_history = {
            "training": None,
            "validation": None,
            "test": None,
        }
        self._training_feature_names: list[str] | None = None
        self._validation_feature_names: list[str] | None = None
        self._test_feature_names: list[str] | None = None

    @property
    def _constructor(self):
        return PartitionedDataset

    def __finalize__(self, other: Any, method: str | None = None, **kwargs: Any) -> "PartitionedDataset":
        for attr in self._metadata:
            if hasattr(other, attr):
                setattr(self, attr, getattr(other, attr))
        return super().__finalize__(other, method=method, **kwargs)

    @classmethod
    def from_dataframe(cls, data: pd.DataFrame, **kwargs: Any) -> "PartitionedDataset":
        return cls(data.copy(), **kwargs)

    def set_partition_logic(self, partition: str, selector: Callable[[pd.DataFrame], Any] | Any) -> "PartitionedDataset":
        normalized = self._normalize_partition_name(partition)
        self._partition_logic[normalized] = selector
        return self

    def _normalize_partition_name(self, partition: str) -> str:
        if partition is None:
            raise ValueError("Partition name must be provided.")
        normalized = str(partition).strip().lower()
        if normalized not in {"training", "validation", "test"}:
            raise ValueError("Partition must be one of: training, validation, test.")
        return normalized

    def select_partition(self, partition: str) -> pd.DataFrame:
        normalized = self._normalize_partition_name(partition)
        selector = self._partition_logic.get(normalized)
        if selector is None:
            raise ValueError(
                f"No partition logic is registered for '{normalized}'. "
                "Use set_partition_logic(partition, selector) first."
            )

        if callable(selector):
            result = selector(self)
        else:
            result = selector

        if isinstance(result, pd.DataFrame):
            return result.copy()
        if isinstance(result, pd.Series):
            return self.loc[result.index].copy()
        if isinstance(result, (list, tuple, np.ndarray, pd.Index)):
            return self.iloc[list(result)].copy()
        if isinstance(result, slice):
            return self.iloc[result].copy()
        if isinstance(result, pd.Index):
            return self.loc[result].copy()
        if isinstance(result, (bool, np.bool_)):
            return self.loc[result].copy()
        if isinstance(result, tuple) and len(result) == 2 and all(isinstance(item, (list, tuple, np.ndarray, slice, pd.Index)) for item in result):
            return self.iloc[result].copy()

        mask = pd.Series(result, index=self.index, dtype=bool)
        return self.loc[mask].copy()

    def _resolve_attribute_list(self, attribute_list: list[str] | tuple[str, ...] | set[str] | None, data: pd.DataFrame | None = None) -> list[str]:
        if attribute_list is None:
            raise ValueError("An attribute list must be provided.")

        columns = data.columns if data is not None else self.columns
        normalized = list(attribute_list)
        missing = [attribute for attribute in normalized if attribute not in columns]
        if missing:
            raise ValueError(f"Requested attributes are missing from the dataset: {missing}")
        return normalized

    def select_featurized_attributes(self, attribute_list: list[str] | tuple[str, ...] | set[str], data: pd.DataFrame | None = None) -> pd.DataFrame:
        frame = self if data is None else data
        attributes = self._resolve_attribute_list(attribute_list, frame)
        return frame.loc[:, attributes].copy()

    def _remember_feature_state(self, partition: str, attribute_list: list[str] | tuple[str, ...] | set[str]) -> None:
        normalized = self._normalize_partition_name(partition)
        attrs = list(attribute_list)
        self._feature_history[normalized] = attrs
        if normalized == "training":
            self._training_feature_names = attrs
        elif normalized == "validation":
            self._validation_feature_names = attrs
        elif normalized == "test":
            self._test_feature_names = attrs

    def apply_training_features(
        self,
        data: pd.DataFrame | None = None,
        attribute_list: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> pd.DataFrame:
        frame = self if data is None else data
        attributes = attribute_list if attribute_list is not None else self._training_feature_names
        if attributes is None:
            raise ValueError("Training feature attributes have not been set.")
        attributes = self._resolve_attribute_list(attributes, frame)
        self._remember_feature_state("training", attributes)
        return frame.loc[:, attributes].copy()

    def apply_validation_features(
        self,
        data: pd.DataFrame | None = None,
        attribute_list: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> pd.DataFrame:
        frame = self if data is None else data
        attributes = attribute_list if attribute_list is not None else self._training_feature_names
        if attributes is None:
            raise ValueError("Training feature attributes have not been set; fit/resolve training features first.")
        attributes = self._resolve_attribute_list(attributes, frame)
        self._remember_feature_state("validation", attributes)
        return frame.loc[:, attributes].copy()

    def apply_test_features(
        self,
        data: pd.DataFrame | None = None,
        attribute_list: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> pd.DataFrame:
        frame = self if data is None else data
        attributes = attribute_list if attribute_list is not None else self._training_feature_names
        if attributes is None:
            raise ValueError("Training feature attributes have not been set; fit/resolve training features first.")
        attributes = self._resolve_attribute_list(attributes, frame)
        self._remember_feature_state("test", attributes)
        return frame.loc[:, attributes].copy()


StructureDataset = PartitionedDataset

__all__ = ["PartitionedDataset", "StructureDataset"]
