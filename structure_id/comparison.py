from __future__ import annotations

import pandas as pd
import numpy as np


def compare_structures(result_a, result_b) -> dict:
    """
    Compare two structure_id results for consistency and similarity.
    
    Computes:
    - Column similarity (Jaccard index of representative features)
    - Row structure shift (difference in clustered vs independent proportions)
    - Primary driver agreement
    
    Args:
        result_a: First StructureResult
        result_b: Second StructureResult
    
    Returns:
        Dictionary with comparison metrics
    """
    comparison = {}
    
    # Column structure similarity
    # Extract representative features from each result's explicit_column_structures
    features_a = set()
    features_b = set()
    
    # From explicit_column_structures, collect all representative and surviving features
    if hasattr(result_a, 'selected_columns'):
        features_a = set(result_a.selected_columns)
        if "structure_id" in features_a:
            features_a.remove("structure_id")
    
    if hasattr(result_b, 'selected_columns'):
        features_b = set(result_b.selected_columns)
        if "structure_id" in features_b:
            features_b.remove("structure_id")
    
    # Jaccard similarity
    if features_a or features_b:
        intersection = len(features_a & features_b)
        union = len(features_a | features_b)
        column_jaccard = intersection / union if union > 0 else 0.0
    else:
        column_jaccard = 1.0
    
    comparison["column_similarity"] = {
        "features_a": list(features_a),
        "features_b": list(features_b),
        "intersection": list(features_a & features_b),
        "jaccard_index": float(column_jaccard),
    }
    
    # Row structure shift
    # Get structure_id values from diagnostics
    structure_id_a = result_a.diagnostics.get("structure_id_values", {})
    structure_id_b = result_b.diagnostics.get("structure_id_values", {})
    
    # Count clustered vs independent
    if isinstance(structure_id_a, dict):
        counts_a = {}
        for val in structure_id_a.values():
            val_str = str(val)
            counts_a[val_str] = counts_a.get(val_str, 0) + 1
    else:
        counts_a = {}
    
    if isinstance(structure_id_b, dict):
        counts_b = {}
        for val in structure_id_b.values():
            val_str = str(val)
            counts_b[val_str] = counts_b.get(val_str, 0) + 1
    else:
        counts_b = {}
    
    total_a = sum(counts_a.values()) if counts_a else 0
    total_b = sum(counts_b.values()) if counts_b else 0
    
    independent_a = counts_a.get("noise", 0) / total_a if total_a > 0 else 0.0
    independent_b = counts_b.get("noise", 0) / total_b if total_b > 0 else 0.0
    
    clustered_a = (total_a - counts_a.get("noise", 0)) / total_a if total_a > 0 else 0.0
    clustered_b = (total_b - counts_b.get("noise", 0)) / total_b if total_b > 0 else 0.0
    
    comparison["row_structure_shift"] = {
        "clustered_proportion_a": float(clustered_a),
        "clustered_proportion_b": float(clustered_b),
        "independent_proportion_a": float(independent_a),
        "independent_proportion_b": float(independent_b),
        "proportion_shift": float(abs(clustered_a - clustered_b)),
    }
    
    # Primary driver agreement (from latent_break)
    driver_a = None
    driver_b = None
    
    if hasattr(result_a, 'latent_break') and result_a.latent_break:
        driver_a = result_a.latent_break.variable_name
    
    if hasattr(result_b, 'latent_break') and result_b.latent_break:
        driver_b = result_b.latent_break.variable_name
    
    comparison["latent_structure_agreement"] = {
        "primary_driver_a": driver_a,
        "primary_driver_b": driver_b,
        "drivers_match": driver_a == driver_b if (driver_a and driver_b) else None,
    }
    
    return comparison
