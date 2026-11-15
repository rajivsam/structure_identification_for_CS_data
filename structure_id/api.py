from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Any

from .config import StructureIDConfig
from .validation import validate_inputs, validate_and_prepare_data
from .explicit_structure import (
    redundancy_collapse,
    gram_schmidt_orthogonalize,
    cluster_rows,
    get_orthogonal_feature_interpretation_report,
)
from .latent_structure import detect_latent_breaks
from .comparison import compare_structures


@dataclass
class StructureResult:
    """Complete v2.0 structure identification result"""
    target: str
    task_type: str
    
    # Stage outputs
    variance_ledger: dict
    explicit_column_structures: list[dict]
    orthogonal_basis: pd.DataFrame
    orthogonal_interpretation: dict
    representative_features: pd.DataFrame
    explicit_row_structures: list[dict]
    latent_structures: dict
    
    # Diagnostic information
    diagnostics: dict = field(default_factory=dict)
    
    def get_orthogonal_feature_interpretation_report(self) -> dict:
        """Return formatted orthogonal interpretation report"""
        return self.orthogonal_interpretation.copy()
    
    def to_html(self) -> str:
        """Generate HTML report of structure identification results"""
        html_parts = [
            "<html><head><title>Structure Identification Report</title></head><body>",
            "<h1>Structure Identification Report (v2.0)</h1>",
            f"<h2>Target: {self.target} | Task Type: {self.task_type}</h2>",
        ]
        
        # Variance ledger
        html_parts.append("<h3>Variance Ledger</h3>")
        html_parts.append("<ul>")
        for key, value in self.variance_ledger.items():
            html_parts.append(f"<li>{key}: {value}</li>")
        html_parts.append("</ul>")
        
        # Orthogonal interpretation
        if self.orthogonal_interpretation.get("table") is not None:
            html_parts.append("<h3>Orthogonal Feature Interpretation</h3>")
            table_df = self.orthogonal_interpretation["table"]
            html_parts.append(table_df.to_html())
        
        # Summary table
        if self.orthogonal_interpretation.get("summary") is not None:
            html_parts.append("<h3>Component Summary</h3>")
            summary_df = self.orthogonal_interpretation["summary"]
            html_parts.append(summary_df.to_html())
        
        # Row clusters
        html_parts.append("<h3>Row Clusters</h3>")
        html_parts.append(f"<p>Number of clusters: {len(self.explicit_row_structures)}</p>")
        if self.explicit_row_structures:
            html_parts.append("<ul>")
            for cluster in self.explicit_row_structures:
                html_parts.append(f"<li>Cluster {cluster['cluster_id']}: {cluster['size']} rows</li>")
            html_parts.append("</ul>")
        
        # Latent structure
        if self.latent_structures.get("primary_driver"):
            html_parts.append("<h3>Latent Structure</h3>")
            html_parts.append(f"<p>Primary driver: {self.latent_structures['primary_driver']}</p>")
            if self.latent_structures.get("cutpoint"):
                html_parts.append(f"<p>Cutpoint: {self.latent_structures['cutpoint']}</p>")
        
        html_parts.append("</body></html>")
        return "\n".join(html_parts)
    
    def save_reports(self, output_dir: str) -> None:
        """Save HTML and CSV reports to output directory"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Save HTML report
        html_path = os.path.join(output_dir, "structure_report.html")
        with open(html_path, "w") as f:
            f.write(self.to_html())
        
        # Save interpretation table
        if self.orthogonal_interpretation.get("table") is not None:
            table_path = os.path.join(output_dir, "orthogonal_interpretation.csv")
            self.orthogonal_interpretation["table"].to_csv(table_path, index=False)
        
        # Save summary table
        if self.orthogonal_interpretation.get("summary") is not None:
            summary_path = os.path.join(output_dir, "component_summary.csv")
            self.orthogonal_interpretation["summary"].to_csv(summary_path, index=False)
        
        # Save orthogonal basis
        basis_path = os.path.join(output_dir, "orthogonal_basis.csv")
        self.orthogonal_basis.to_csv(basis_path)
        
        # Save representative features
        rep_path = os.path.join(output_dir, "representative_features.csv")
        self.representative_features.to_csv(rep_path)


def structure_id(
    data: pd.DataFrame,
    target: str | pd.Series | np.ndarray,
    task_type: str,
    structural_covariates: list[str] | None = None,
    config: dict | StructureIDConfig | None = None,
) -> StructureResult:
    """
    Complete structure_id v2.0 pipeline orchestration.
    
    Executes all 4 stages:
    1. Input validation and candidate preparation
    2. Explicit feature clustering (redundancy collapse)
    3. Gram-Schmidt orthogonalization
    4. Row clustering
    5. Latent heterogeneity testing
    
    Args:
        data: Input DataFrame
        target: Target column name or values
        task_type: "regression" or "classification"
        structural_covariates: Optional list of structural covariate columns
        config: StructureIDConfig or dict
    
    Returns:
        StructureResult with complete pipeline outputs
    """
    # Parse config
    if isinstance(config, dict):
        cfg = StructureIDConfig.from_dict(config)
    elif isinstance(config, StructureIDConfig):
        cfg = config
    else:
        cfg = StructureIDConfig()
    
    # Validate basic inputs
    data_copy, task_type, structural_covariates = validate_inputs(
        data, target if isinstance(target, str) else "target", task_type, structural_covariates
    )
    
    # If target is not a column name, add it to data
    if isinstance(target, str):
        y = data_copy[target]
    else:
        y = target
        data_copy["_target_"] = y
        target = "_target_"
    
    # STAGE 0: Validation and Candidate Preparation
    Z, l_provisional, validation_diagnostics = validate_and_prepare_data(
        data_copy,
        target,
        task_type,
        structural_covariates,
        cfg,
    )
    
    # Initialize variance ledger
    variance_ledger = {
        "total_input_features": len(data_copy.columns) - 1,
        "provisional_candidate_features": l_provisional,
        "target": target,
        "structural_covariates": structural_covariates or [],
    }
    
    # STAGE 1: Explicit Feature Clustering (Redundancy Collapse)
    Z_rep, column_structures, stage1_diag = redundancy_collapse(Z, cfg)
    
    variance_ledger["features_after_redundancy_collapse"] = len(Z_rep.columns)
    variance_ledger["dropped_redundant_features"] = (
        len(Z.columns) - len(Z_rep.columns)
    )
    variance_ledger["explicit_column_structures"] = len(column_structures)
    
    # STAGE 2: Gram-Schmidt Orthogonalization
    U, W, interpretation = gram_schmidt_orthogonalize(Z_rep, cfg)
    
    variance_ledger["orthogonal_basis_dimension"] = len(U.columns)
    variance_ledger["total_variance_retained"] = float(
        np.sum([c["retained_variance"] for c in interpretation["components"]])
    )
    
    # STAGE 3: Row Clustering
    structure_id_values, cluster_profiles, stage3_diag = cluster_rows(U, cfg)
    
    # Add structure_id to orthogonal basis and representative features
    U_with_structure = U.copy()
    U_with_structure["structure_id"] = structure_id_values
    
    Z_rep_with_structure = Z_rep.copy()
    Z_rep_with_structure["structure_id"] = structure_id_values
    
    variance_ledger["n_clusters"] = len(cluster_profiles)
    variance_ledger["clustered_rows"] = sum(c["size"] for c in cluster_profiles)
    variance_ledger["independent_rows"] = (structure_id_values == "independent").sum()
    variance_ledger["total_rows"] = len(data_copy)
    
    # Get orthogonal interpretation report
    ortho_report = get_orthogonal_feature_interpretation_report(interpretation)
    
    # STAGE 4: Latent Heterogeneity Testing
    primary_driver, cutpoint, latent_diag = detect_latent_breaks(
        y,
        Z_rep,  # Use original un-orthogonalized features
        structural_covariates,
        cfg,
        data_copy,
    )
    
    latent_structures = {
        "primary_driver": primary_driver,
        "cutpoint": cutpoint,
        "latent_break_detected": primary_driver is not None,
        "diagnostics": latent_diag,
    }
    
    variance_ledger["latent_break_detected"] = primary_driver is not None
    
    # Assemble final result
    result = StructureResult(
        target=target,
        task_type=task_type,
        variance_ledger=variance_ledger,
        explicit_column_structures=column_structures,
        orthogonal_basis=U_with_structure,
        orthogonal_interpretation=ortho_report,
        representative_features=Z_rep_with_structure,
        explicit_row_structures=cluster_profiles,
        latent_structures=latent_structures,
        diagnostics={
            "stage0_validation": validation_diagnostics,
            "stage1_redundancy": stage1_diag,
            "stage2_orthogonalization": {
                "n_components": interpretation["n_components"],
                "weight_matrix": interpretation["weight_matrix"],
            },
            "stage3_clustering": stage3_diag,
            "stage4_latent": latent_diag,
            "config": cfg.to_dict(),
        },
    )
    
    return result


__all__ = ["structure_id", "StructureResult", "compare_structures"]
