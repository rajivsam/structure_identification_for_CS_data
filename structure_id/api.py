from __future__ import annotations

import pandas as pd

from .candidate_selection import CandidateSelector
from .config import StructureIDConfig
from .dataset import PartitionedDataset, StructureDataset
from .explicit_structure import ExplicitStructureDetector
from .latent_structure import LatentStructureDetector
from .reporting import generate_report
from .types import StructureResult
from .validation import validate_inputs

__all__ = ["structure_id", "PartitionedDataset", "StructureDataset"]


def structure_id(
    data: pd.DataFrame,
    target: str,
    task_type: str,
    structural_covariates: list[str] | None = None,
    config: dict | StructureIDConfig | None = None,
) -> StructureResult:
    cfg = config if isinstance(config, StructureIDConfig) else StructureIDConfig.from_dict(config)
    data, task_type, structural_covariates = validate_inputs(
        data=data,
        target=target,
        task_type=task_type,
        structural_covariates=structural_covariates,
    )

    selector = CandidateSelector(cfg)
    selection = selector.select(data, target, structural_covariates)
    selected_columns = selection["selected_columns"]
    provisional_columns = selected_columns.copy()

    explicit_detector = ExplicitStructureDetector(cfg)
    explicit_column_blocks, remaining_columns = explicit_detector.detect_column_blocks(data, selected_columns)
    row_clusters, structure_id_values = explicit_detector.detect_row_clusters(data, remaining_columns)
    structure_id_column = "structure_id"
    profile_frame = data.loc[:, remaining_columns].copy() if remaining_columns else pd.DataFrame(index=data.index)
    if "structure_id" in profile_frame.columns:
        profile_frame = profile_frame.drop(columns=["structure_id"])
    profile_frame[structure_id_column] = structure_id_values.astype(object)
    selected_with_structure = list(remaining_columns)
    if structure_id_column not in selected_with_structure:
        selected_with_structure.append(structure_id_column)

    latent_detector = LatentStructureDetector(cfg)
    latent_break = latent_detector.detect(
        data=data,
        target=target,
        task_type=task_type,
        candidate_columns=remaining_columns,
        structural_covariates=structural_covariates,
    )

    result = StructureResult(
        target=target,
        task_type=task_type,
        provisional_columns=provisional_columns,
        selected_columns=selected_with_structure,
        explicit_column_structures=explicit_column_blocks,
        explicit_row_clusters=row_clusters,
        latent_break=latent_break,
        diagnostics={
            "config": cfg.to_dict(),
            "dropped_columns": selection["dropped_columns"],
            "selected_before_column_filter": selected_columns,
            "selected_after_column_filter": remaining_columns,
            "structure_id_column": structure_id_column,
            "structure_id_values": structure_id_values.to_dict(),
            "cluster_profile_data": profile_frame,
            "row_cluster_count": len(row_clusters),
            "candidate_count": len(remaining_columns),
        },
    )
    result.diagnostics["report"] = generate_report(result)
    return result
