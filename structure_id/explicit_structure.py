from __future__ import annotations

import hdbscan
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import mutual_info_score
from sklearn.preprocessing import StandardScaler

from .config import StructureIDConfig
from .types import ExplicitColumnBlock, ExplicitRowCluster


class ExplicitStructureDetector:
    def __init__(self, config: StructureIDConfig):
        self.config = config

    @staticmethod
    def _normalized_mutual_information(x: pd.Series, y: pd.Series) -> float:
        x_numeric = pd.to_numeric(x, errors="coerce").fillna(x.median())
        y_numeric = pd.to_numeric(y, errors="coerce").fillna(y.median())

        if x_numeric.empty or y_numeric.empty:
            return 0.0

        n_bins = max(2, min(len(x_numeric), 10))
        x_binned = pd.cut(x_numeric, bins=n_bins, duplicates="drop", include_lowest=True)
        y_binned = pd.cut(y_numeric, bins=n_bins, duplicates="drop", include_lowest=True)

        x_labels = x_binned.astype(str)
        y_labels = y_binned.astype(str)

        mi = mutual_info_score(x_labels, y_labels)
        if not np.isfinite(mi):
            return 0.0

        upper_bound = np.log(len(x_numeric))
        if upper_bound <= 0.0:
            return 0.0
        return float(np.clip(mi / upper_bound, 0.0, 1.0))

    def _mutual_information_matrix(self, data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        matrix = pd.DataFrame(0.0, index=columns, columns=columns)
        for left_index, left_name in enumerate(columns):
            for right_index in range(left_index + 1, len(columns)):
                right_name = columns[right_index]
                strength = self._normalized_mutual_information(data[left_name], data[right_name])
                matrix.at[left_name, right_name] = strength
                matrix.at[right_name, left_name] = strength
        for column in columns:
            matrix.at[column, column] = 1.0
        return matrix

    def detect_column_blocks(self, data: pd.DataFrame, candidate_columns: list[str]) -> tuple[list[ExplicitColumnBlock], list[str]]:
        if not candidate_columns:
            return [], []

        continuous_columns = [
            col for col in candidate_columns if pd.api.types.is_numeric_dtype(data[col])
        ]
        if len(continuous_columns) <= 1:
            return [], list(candidate_columns)

        similarity = self._mutual_information_matrix(data, continuous_columns)
        distance = 1.0 - similarity.to_numpy()
        np.fill_diagonal(distance, 0.0)
        condensed = squareform(distance, checks=False)

        linkage_matrix = linkage(condensed, method="complete")
        threshold = self.config.mutual_information_threshold or self.config.correlation_threshold
        labels = fcluster(linkage_matrix, t=1.0 - threshold, criterion="distance")

        groups: dict[int, list[str]] = {}
        for column, label in zip(continuous_columns, labels):
            groups.setdefault(int(label), []).append(column)

        blocks: list[ExplicitColumnBlock] = []
        surviving: set[str] = set()
        for cluster_id, members in sorted(groups.items()):
            if len(members) == 1:
                surviving.add(members[0])
                continue

            cluster_similarity = similarity.loc[members, members].copy()
            pairwise_mutual_information: dict[str, float] = {}
            merge_history: list[dict[str, float | list[str] | str]] = []
            for left_index, left_name in enumerate(members):
                for right_index in range(left_index + 1, len(members)):
                    right_name = members[right_index]
                    mutual_information = float(cluster_similarity.loc[left_name, right_name])
                    pair_name = f"{left_name}__{right_name}"
                    pairwise_mutual_information[pair_name] = mutual_information
                    merge_history.append(
                        {
                            "merged_pair": [left_name, right_name],
                            "mutual_information": mutual_information,
                            "normalized_mutual_information": mutual_information,
                            "distance": 1.0 - mutual_information,
                        }
                    )

            merge_history.sort(key=lambda item: float(item["mutual_information"]), reverse=True)
            variance = data[members].var(ddof=0).to_dict()
            representative = max(members, key=lambda col: float(variance.get(col, 0.0)))
            dropped = [col for col in members if col != representative]
            blocks.append(
                ExplicitColumnBlock(
                    cluster_id=cluster_id,
                    representative_feature=representative,
                    dropped_features=dropped,
                    similarity_threshold=threshold,
                    feature_count=len(members),
                    cluster_members=members,
                    pairwise_correlations=pairwise_mutual_information,
                    pairwise_mutual_information=pairwise_mutual_information,
                    merge_history=merge_history,
                    correlation_matrix={
                        row: {col: float(value) for col, value in values.items()}
                        for row, values in cluster_similarity.to_dict().items()
                    },
                )
            )
            surviving.add(representative)

        remaining = [
            col for col in candidate_columns if col in surviving or not pd.api.types.is_numeric_dtype(data[col])
        ]
        return blocks, remaining

    def detect_row_clusters(self, data: pd.DataFrame, candidate_columns: list[str]) -> tuple[list[ExplicitRowCluster], pd.Series]:
        if not candidate_columns:
            return [], pd.Series("noise", index=data.index, dtype=object)

        frame = data[candidate_columns].copy()
        for col in frame.columns:
            if pd.api.types.is_numeric_dtype(frame[col]):
                frame[col] = frame[col].fillna(frame[col].median())
            else:
                frame[col] = frame[col].fillna("__MISSING__").astype(str)

        encoded = pd.get_dummies(frame, dummy_na=True)
        if encoded.empty or encoded.shape[1] == 0:
            return [], pd.Series("noise", index=data.index, dtype=object)

        scaler = StandardScaler()
        scaled = scaler.fit_transform(encoded)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=max(2, self.config.min_cluster_size),
            min_samples=max(1, min(5, self.config.min_cluster_size)),
            cluster_selection_epsilon=0.0,
        )
        labels = clusterer.fit_predict(scaled)

        structure_ids = pd.Series("noise", index=data.index, dtype=object)
        clusters: list[ExplicitRowCluster] = []
        unique_labels = sorted(set(labels))
        for label in unique_labels:
            if label == -1:
                continue
            indices = np.where(labels == label)[0].tolist()
            if len(indices) < self.config.min_cluster_size:
                continue
            structure_ids.iloc[indices] = int(label)
            clusters.append(
                ExplicitRowCluster(
                    cluster_id=int(label),
                    row_indices=indices,
                    size=len(indices),
                    category_label="macro_cluster",
                )
            )

        return clusters, structure_ids
