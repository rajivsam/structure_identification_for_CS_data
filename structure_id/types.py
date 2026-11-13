from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateVariable:
    name: str
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplicitColumnBlock:
    cluster_id: int
    representative_feature: str
    dropped_features: list[str]
    method: str = "mutual_information_complete_linkage"
    similarity_threshold: float = 0.85
    feature_count: int = 0
    cluster_members: list[str] = field(default_factory=list)
    pairwise_correlations: dict[str, float] = field(default_factory=dict)
    pairwise_mutual_information: dict[str, float] = field(default_factory=dict)
    merge_history: list[dict[str, Any]] = field(default_factory=list)
    correlation_matrix: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.pairwise_mutual_information and self.pairwise_correlations:
            self.pairwise_mutual_information = self.pairwise_correlations
        if not self.pairwise_correlations and self.pairwise_mutual_information:
            self.pairwise_correlations = self.pairwise_mutual_information

    def describe(self) -> str:
        if not self.cluster_members:
            return (
                f"Cluster {self.cluster_id}: representative={self.representative_feature}, "
                f"dropped={self.dropped_features}"
            )

        pair_snippets = []
        for item in self.merge_history[:5]:
            left, right = item["merged_pair"]
            mi_value = item.get("mutual_information", item.get("normalized_mutual_information", item.get("spearman_rho", 0.0)))
            pair_snippets.append(f"{left}↔{right} (mi={float(mi_value):.4f})")
        if not pair_snippets:
            pair_snippets.append("no explicit pairwise merge recorded")

        return (
            f"Cluster {self.cluster_id}: members={self.cluster_members}, "
            f"representative={self.representative_feature}, "
            f"dropped={self.dropped_features}, merge_pairs=[{'; '.join(pair_snippets)}]"
        )


@dataclass
class ExplicitRowCluster:
    cluster_id: int
    row_indices: list[int]
    size: int
    category_label: str = "macro_cluster"


@dataclass
class LatentBreak:
    variable_name: str
    statistic: float
    raw_p_value: float
    adjusted_p_value: float
    alpha: float
    significant: bool
    cutpoint: float | None = None
    row_support: list[int] | None = None


@dataclass
class StructureResult:
    target: str
    task_type: str
    provisional_columns: list[str]
    selected_columns: list[str]
    explicit_column_structures: list[ExplicitColumnBlock]
    explicit_row_clusters: list[ExplicitRowCluster]
    latent_break: LatentBreak | None
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "Structure Identification Summary",
            f"Target: {self.target}",
            f"Task type: {self.task_type}",
            f"Provisional candidates: {len(self.provisional_columns)}",
            f"Selected candidates: {len(self.selected_columns)}",
            f"Explicit column blocks: {len(self.explicit_column_structures)}",
            f"Explicit row clusters: {len(self.explicit_row_clusters)}",
        ]
        if self.explicit_column_structures:
            lines.append("Explicit column block details:")
            for block in self.explicit_column_structures:
                lines.append(f"  - {block.describe()}")
        structure_counts = self.diagnostics.get("structure_id_values")
        if isinstance(structure_counts, dict) and structure_counts:
            from collections import Counter
            counts = Counter(str(value) for value in structure_counts.values())
            noise = counts.get("noise", 0)
            cluster_counts = sorted(
                ((int(label), count) for label, count in counts.items() if label != "noise"),
                key=lambda item: item[0],
            )
            lines.append("Instance structure summary:")
            if noise:
                lines.append(f"  noise={noise}")
            if cluster_counts:
                for cluster_id, count in cluster_counts:
                    lines.append(f"  cluster_{cluster_id}={count}")
            else:
                lines.append("  no valid instance clusters assigned")
        if self.latent_break is None:
            lines.append("Latent break: none detected")
        else:
            lines.append(
                f"Latent break: {self.latent_break.variable_name} "
                f"(adj p={self.latent_break.adjusted_p_value:.4g}, sig={self.latent_break.significant})"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "task_type": self.task_type,
            "provisional_columns": self.provisional_columns,
            "selected_columns": self.selected_columns,
            "explicit_column_structures": [
                {
                    "cluster_id": block.cluster_id,
                    "representative_feature": block.representative_feature,
                    "dropped_features": block.dropped_features,
                    "cluster_members": block.cluster_members,
                    "method": block.method,
                    "similarity_threshold": block.similarity_threshold,
                    "feature_count": block.feature_count,
                    "pairwise_correlations": block.pairwise_correlations,
                    "pairwise_mutual_information": block.pairwise_mutual_information,
                    "merge_history": block.merge_history,
                    "correlation_matrix": block.correlation_matrix,
                }
                for block in self.explicit_column_structures
            ],
            "explicit_row_clusters": [
                {
                    "cluster_id": cluster.cluster_id,
                    "size": cluster.size,
                    "row_indices": cluster.row_indices,
                    "category_label": cluster.category_label,
                }
                for cluster in self.explicit_row_clusters
            ],
            "latent_break": None
            if self.latent_break is None
            else {
                "variable_name": self.latent_break.variable_name,
                "statistic": self.latent_break.statistic,
                "raw_p_value": self.latent_break.raw_p_value,
                "adjusted_p_value": self.latent_break.adjusted_p_value,
                "alpha": self.latent_break.alpha,
                "significant": self.latent_break.significant,
                "cutpoint": self.latent_break.cutpoint,
                "row_support": self.latent_break.row_support,
            },
            "diagnostics": self.diagnostics,
        }
