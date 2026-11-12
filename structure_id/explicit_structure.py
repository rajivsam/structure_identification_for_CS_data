from __future__ import annotations

import hdbscan
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.preprocessing import StandardScaler

from .config import StructureIDConfig
from .types import ExplicitColumnBlock, ExplicitRowCluster


class ExplicitStructureDetector:
    def __init__(self, config: StructureIDConfig):
        self.config = config

    def detect_column_blocks(self, data: pd.DataFrame, candidate_columns: list[str]) -> tuple[list[ExplicitColumnBlock], list[str]]:
        if not candidate_columns:
            return [], []

        continuous_columns = [
            col for col in candidate_columns if pd.api.types.is_numeric_dtype(data[col])
        ]
        if len(continuous_columns) <= 1:
            return [], list(candidate_columns)

        corr = data[continuous_columns].corr(method="spearman")
        distance = 1.0 - np.abs(corr.to_numpy())
        np.fill_diagonal(distance, 0.0)
        condensed = squareform(distance, checks=False)

        linkage_matrix = linkage(condensed, method="complete")
        labels = fcluster(linkage_matrix, t=1.0 - self.config.correlation_threshold, criterion="distance")

        groups: dict[int, list[str]] = {}
        for column, label in zip(continuous_columns, labels):
            groups.setdefault(int(label), []).append(column)

        blocks: list[ExplicitColumnBlock] = []
        surviving: set[str] = set()
        for cluster_id, members in sorted(groups.items()):
            if len(members) == 1:
                surviving.add(members[0])
                continue

            cluster_corr = corr.loc[members, members].copy()
            pairwise_correlations: dict[str, float] = {}
            merge_history: list[dict[str, float | list[str] | str]] = []
            for left_index, left_name in enumerate(members):
                for right_index in range(left_index + 1, len(members)):
                    right_name = members[right_index]
                    rho = float(cluster_corr.loc[left_name, right_name])
                    pair_name = f"{left_name}__{right_name}"
                    pairwise_correlations[pair_name] = rho
                    merge_history.append(
                        {
                            "merged_pair": [left_name, right_name],
                            "spearman_rho": rho,
                            "absolute_spearman_rho": abs(rho),
                            "distance": 1.0 - abs(rho),
                        }
                    )

            merge_history.sort(key=lambda item: abs(float(item["spearman_rho"])), reverse=True)
            variance = data[members].var(ddof=0).to_dict()
            representative = max(members, key=lambda col: float(variance.get(col, 0.0)))
            dropped = [col for col in members if col != representative]
            blocks.append(
                ExplicitColumnBlock(
                    cluster_id=cluster_id,
                    representative_feature=representative,
                    dropped_features=dropped,
                    similarity_threshold=self.config.correlation_threshold,
                    feature_count=len(members),
                    cluster_members=members,
                    pairwise_correlations=pairwise_correlations,
                    merge_history=merge_history,
                    correlation_matrix={
                        row: {col: float(value) for col, value in values.items()}
                        for row, values in cluster_corr.to_dict().items()
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
