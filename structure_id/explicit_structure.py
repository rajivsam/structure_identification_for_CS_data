from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import normalized_mutual_info_score
import hdbscan

from .config import StructureIDConfig


def redundancy_collapse(Z: pd.DataFrame, config: StructureIDConfig) -> tuple[pd.DataFrame, list[dict], dict]:
    """
    Stage 1: Explicit Feature Clustering (Redundancy Collapse)
    
    Identify redundant feature blocks via NMI clustering and select
    highest-variance representative per block.
    
    Args:
        Z: DataFrame of candidate features (numeric expected)
        config: StructureIDConfig with mutual_information_threshold
    
    Returns:
        (Z_rep, column_structures, diagnostics) where:
        - Z_rep: DataFrame of surviving representative features
        - column_structures: List of dicts describing each cluster
        - diagnostics: Filtering details
    """
    if Z.empty or len(Z.columns) <= 1:
        return Z.copy(), [], {
            "n_clusters": len(Z.columns) if not Z.empty else 0,
            "clustering_method": "none_needed"
        }
    
    # Compute pairwise NMI for numeric columns
    numeric_cols = [c for c in Z.columns if pd.api.types.is_numeric_dtype(Z[c])]
    
    if len(numeric_cols) <= 1:
        return Z.copy(), [], {
            "n_clusters": len(Z.columns),
            "clustering_method": "no_numeric_pairs"
        }
    
    # Build NMI distance matrix
    n = len(numeric_cols)
    nmi_matrix = np.eye(n)
    
    for i in range(n):
        for j in range(i + 1, n):
            col_i = numeric_cols[i]
            col_j = numeric_cols[j]
            
            # Compute NMI
            x = Z[col_i].fillna(Z[col_i].median()).values
            y = Z[col_j].fillna(Z[col_j].median()).values
            
            # Discretize for NMI
            n_bins = max(2, min(len(x) // 10, 10))
            x_binned = pd.cut(x, bins=n_bins, labels=False, duplicates='drop')
            y_binned = pd.cut(y, bins=n_bins, labels=False, duplicates='drop')
            
            # Remove NaN from discretization
            valid_mask = ~(pd.isna(x_binned) | pd.isna(y_binned))
            if valid_mask.sum() > 0:
                nmi = normalized_mutual_info_score(x_binned[valid_mask], y_binned[valid_mask])
            else:
                nmi = 0.0
            
            nmi_matrix[i, j] = nmi
            nmi_matrix[j, i] = nmi
    
    # Distance matrix: d = 1 - NMI
    distance_matrix = 1.0 - nmi_matrix
    np.fill_diagonal(distance_matrix, 0.0)
    
    # Hierarchical clustering with complete linkage
    condensed_dist = squareform(distance_matrix, checks=False)
    Z_linkage = linkage(condensed_dist, method='complete')
    
    # Cut dendrogram at threshold: 1.0 - mutual_information_threshold
    threshold = 1.0 - config.mutual_information_threshold
    cluster_labels = fcluster(Z_linkage, t=threshold, criterion='distance')
    
    # Group features by cluster
    clusters = {}
    for label, col in zip(cluster_labels, numeric_cols):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(col)
    
    # For each cluster, select highest-variance representative
    Z_rep_cols = []
    column_structures = []
    
    for cluster_id in sorted(clusters.keys()):
        members = clusters[cluster_id]
        
        if len(members) == 1:
            Z_rep_cols.append(members[0])
            column_structures.append({
                "cluster_id": cluster_id,
                "representative_feature": members[0],
                "dropped_features": [],
                "cluster_members": members,
                "n_members": 1,
                "nmi_threshold": config.mutual_information_threshold,
            })
        else:
            # Select highest variance as representative
            variances = Z[members].var(ddof=1)
            representative = variances.idxmax()
            dropped = [c for c in members if c != representative]
            
            Z_rep_cols.append(representative)
            
            # Record NMI submatrix
            member_indices = [numeric_cols.index(c) for c in members]
            nmi_submatrix = nmi_matrix[np.ix_(member_indices, member_indices)]
            
            column_structures.append({
                "cluster_id": cluster_id,
                "representative_feature": representative,
                "dropped_features": dropped,
                "n_members": len(members),
                "cluster_members": members,
                "nmi_threshold": config.mutual_information_threshold,
                "nmi_submatrix": {
                    members[i]: {members[j]: float(nmi_submatrix[i, j]) 
                                 for j in range(len(members))}
                    for i in range(len(members))
                },
            })
    
    # Include non-numeric columns as-is
    non_numeric_cols = [c for c in Z.columns if c not in numeric_cols]
    Z_rep_cols.extend(non_numeric_cols)
    
    Z_rep = Z[Z_rep_cols].copy()
    
    diagnostics = {
        "n_initial_numeric_features": len(numeric_cols),
        "n_initial_features": len(Z.columns),
        "n_clusters": len(clusters),
        "n_surviving_features": len(Z_rep_cols),
        "nmi_threshold": config.mutual_information_threshold,
        "column_structures": column_structures,
    }
    
    return Z_rep, column_structures, diagnostics


def gram_schmidt_orthogonalize(Z_rep: pd.DataFrame, config: StructureIDConfig) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """
    Stage 2: Gram-Schmidt Orthogonalization with Interpretability
    
    Apply modified Gram-Schmidt (unnormalized) to orthogonalize features
    while preserving scale and inter-cluster separation.
    
    Args:
        Z_rep: DataFrame of representative features
        config: StructureIDConfig
    
    Returns:
        (U, W, interpretation) where:
        - U: DataFrame of orthogonalized features
        - W: Weight matrix from QR decomposition
        - interpretation: Dict with feature attribution
    """
    # Select numeric columns and order by descending variance
    numeric_cols = [c for c in Z_rep.columns if pd.api.types.is_numeric_dtype(Z_rep[c])]
    numeric_cols = sorted(numeric_cols, 
                         key=lambda c: Z_rep[c].var(ddof=1) if not Z_rep[c].isna().all() else 0.0,
                         reverse=True)
    
    # Center the data
    Z_centered = Z_rep[numeric_cols].copy()
    Z_centered = Z_centered - Z_centered.mean(axis=0)
    
    n_samples = len(Z_centered)
    n_features = len(numeric_cols)
    
    # Unnormalized modified Gram-Schmidt
    U = np.zeros((n_samples, n_features))
    R = np.zeros((n_features, n_features))
    
    for j in range(n_features):
        z_j = Z_centered.iloc[:, j].values
        
        # Subtract projections onto previous basis vectors
        u_j = z_j.copy()
        for k in range(j):
            R[k, j] = np.dot(z_j, U[:, k])
            denom = np.dot(U[:, k], U[:, k])
            if abs(denom) < 1e-12:
                warnings.warn(f"Near-zero denominator in Gram-Schmidt at step {k}, {j}")
                denom = 1e-12
            u_j = u_j - (R[k, j] / denom) * U[:, k]
        
        R[j, j] = np.linalg.norm(u_j)
        if R[j, j] < 1e-12:
            warnings.warn(f"Gram-Schmidt produced near-zero vector at step {j}")
            U[:, j] = u_j  # Keep as is
        else:
            U[:, j] = u_j
    
    # Compute weight matrix W = R^{-1} for interpretation
    # This tells us the linear combination of original features in each orthogonal component
    try:
        W = np.linalg.inv(R)
    except np.linalg.LinAlgError:
        warnings.warn("R matrix is singular; using pseudoinverse")
        W = np.linalg.pinv(R)
    
    # Create orthogonalized DataFrame
    U_df = pd.DataFrame(U, index=Z_rep.index, columns=[f"Ortho_{i}" for i in range(n_features)])
    
    # Interpret components: feature attribution
    interpretation = {
        "n_components": n_features,
        "n_original_features": n_features,
        "original_features": numeric_cols,
        "components": [],
        "weight_matrix": W.tolist(),
    }
    
    for j in range(n_features):
        comp_name = f"Ortho_{j}"
        
        # Get weights for this component
        weights = W[:, j]
        
        # Compute contributions
        abs_weights = np.abs(weights)
        total_abs_weight = np.sum(abs_weights)
        
        if total_abs_weight > 1e-12:
            contributions = []
            for i, feat_name in enumerate(numeric_cols):
                pct = (abs_weights[i] / total_abs_weight) * 100
                if pct >= 5.0:  # Only report contributions >= 5%
                    contributions.append({
                        "feature": feat_name,
                        "weight": float(weights[i]),
                        "sign": "+" if weights[i] > 0 else "-",
                        "percentage": float(pct),
                    })
            
            # Sort by absolute weight descending
            contributions = sorted(contributions, 
                                 key=lambda x: abs(x["weight"]), 
                                 reverse=True)
            
            # Format string for display
            contrib_str = ", ".join([
                f"{c['sign']}{c['feature']} ({c['percentage']:.1f}%)"
                for c in contributions
            ])
        else:
            contributions = []
            contrib_str = "(zero component)"
        
        interpretation["components"].append({
            "component_id": j,
            "component_name": comp_name,
            "contributors": contributions,
            "contribution_string": contrib_str,
            "retained_variance": float(np.var(U[:, j])),
            "raw_weights": weights.tolist(),
        })
    
    return U_df, W, interpretation


def cluster_rows(U: pd.DataFrame, config: StructureIDConfig) -> tuple[pd.Series, list[dict], dict]:
    """
    Stage 3: Row Clustering & Independent Instance Accounting
    
    Run HDBSCAN on orthogonalized features to identify dense clusters.
    Noise points (-1) are labeled as "independent".
    
    Args:
        U: DataFrame of orthogonalized features
        config: StructureIDConfig with min_cluster_size
    
    Returns:
        (structure_id, cluster_profiles, diagnostics)
    """
    # Prepare data for clustering - make writable copy
    data = U.values.copy()
    
    # Handle edge case: single column (reshape to 2D)
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    
    # Ensure minimum samples for HDBSCAN
    if len(data) < 2:
        # Only one sample, mark as independent
        structure_id = pd.Series(["independent"] * len(U), index=U.index, dtype=object)
        return structure_id, [], {
            "n_clusters": 0,
            "n_independent": len(U),
            "n_total": len(U),
            "proportion_clustered": 0.0,
            "cluster_profiles": [],
        }
    
    # Run HDBSCAN
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min(config.min_cluster_size, len(data) // 2),
        min_samples=max(1, min(5, config.min_cluster_size // 2)),
        cluster_selection_epsilon=0.0,
    )
    labels = clusterer.fit_predict(data)
    
    # Map labels: keep cluster IDs, convert -1 to "independent"
    structure_id_values = []
    for label in labels:
        if label == -1:
            structure_id_values.append("independent")
        else:
            structure_id_values.append(int(label))
    
    structure_id = pd.Series(structure_id_values, index=U.index, dtype=object)
    
    # Cluster profiles
    cluster_profiles = []
    unique_labels = sorted(set(labels))
    
    for label in unique_labels:
        if label == -1:
            continue
        
        mask = labels == label
        cluster_size = mask.sum()
        cluster_indices = np.where(mask)[0].tolist()
        
        cluster_profiles.append({
            "cluster_id": int(label),
            "size": int(cluster_size),
            "proportion": float(cluster_size / len(U)),
            "row_indices": cluster_indices,
        })
    
    # Diagnostics
    diagnostics = {
        "n_clusters": len(cluster_profiles),
        "n_independent": (structure_id == "independent").sum(),
        "n_total": len(U),
        "proportion_clustered": (len(U) - (structure_id == "independent").sum()) / len(U),
        "cluster_profiles": cluster_profiles,
    }
    
    return structure_id, cluster_profiles, diagnostics


def get_orthogonal_feature_interpretation_report(interpretation: dict) -> dict:
    """
    Format orthogonal interpretation into structured reporting format.
    
    Returns dict with:
    - table: DataFrame with columns ['Decorrelated Feature', 'Contributing Raw Features (Ordered by Strength)']
    - structured: Dict mapping component names to contributor lists
    - summary: DataFrame with component summary statistics
    - metadata: Config metadata
    """
    components = interpretation.get("components", [])
    
    # Build tabular report
    table_data = []
    for comp in components:
        comp_name = comp["component_name"]
        contrib_str = comp["contribution_string"]
        table_data.append({
            "Decorrelated Feature": comp_name,
            "Contributing Raw Features (Ordered by Strength)": contrib_str,
        })
    
    table = pd.DataFrame(table_data)
    
    # Build structured dictionary
    structured = {}
    for comp in components:
        comp_name = comp["component_name"]
        structured[comp_name] = {
            "contributors": comp["contributors"],
            "contribution_string": comp["contribution_string"],
            "retained_variance": comp["retained_variance"],
        }
    
    # Build summary
    summary_data = []
    for comp in components:
        summary_data.append({
            "Component ID": comp["component_id"],
            "Component Name": comp["component_name"],
            "Retained Variance": comp["retained_variance"],
            "Dominant Attribute Group": comp["contribution_string"].split(",")[0] if comp["contribution_string"] else "N/A",
            "Top Driver": comp["contributors"][0]["feature"] if comp["contributors"] else "N/A",
        })
    
    summary = pd.DataFrame(summary_data)
    
    # Metadata
    metadata = {
        "n_components": interpretation.get("n_components"),
        "n_original_features": interpretation.get("n_original_features"),
        "original_features": interpretation.get("original_features"),
        "total_variance_explained": sum(c["retained_variance"] for c in components),
    }
    
    return {
        "table": table,
        "structured": structured,
        "summary": summary,
        "metadata": metadata,
    }

