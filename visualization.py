"""
Visualization utilities for structure_id results.

Provides plotting functions for:
- Dendrogram (Stage 1: NMI clustering)
- Orthogonality heatmap (Stage 2: Gram-Schmidt validation)
- Cluster size distribution (Stage 3: HDBSCAN)
- Variance explained (interpretation)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from structure_id import StructureResult


def plot_dendrogram_stage1(
    result: StructureResult,
    output_path: Optional[Path] = None,
    figsize: tuple = (12, 6),
    title: str = "Stage 1: Feature Redundancy Dendrogram (NMI Clustering)",
) -> Optional[Path]:
    """
    Plot dendrogram of feature redundancy clustering (Stage 1).

    Uses scipy.cluster.hierarchy and scipy.spatial.distance for hierarchical
    clustering visualization based on NMI distances.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_path : Path, optional
        Where to save the figure. If None, displays interactively.

    figsize : tuple, default=(12, 6)
        Figure size in inches.

    title : str
        Figure title.

    Returns
    -------
    Path or None
        Path where figure was saved, or None if displayed interactively.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import plot_dendrogram_stage1
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> plot_dendrogram_stage1(result, output_path='dendrogram.png')
    """
    try:
        import matplotlib.pyplot as plt
        from scipy.cluster.hierarchy import dendrogram, linkage
        from scipy.spatial.distance import squareform
    except ImportError:
        print("ERROR: matplotlib and scipy required for visualization")
        print("Install with: pip install matplotlib scipy")
        return None

    if not result.explicit_column_structures:
        print("No explicit_column_structures in result (Stage 1 failed?)")
        return None

    # Extract feature names from column structures
    features = set()
    for block in result.explicit_column_structures:
        features.add(block['representative'])
        features.update(block['members'])

    features = sorted(list(features))
    n_features = len(features)

    # Mock distance matrix based on clustering info
    # (In production, you'd extract this from the NMI calculation)
    distance_matrix = np.eye(n_features)

    for block in result.explicit_column_structures:
        rep_idx = features.index(block['representative'])
        for member in block['members']:
            if member != block['representative']:
                mem_idx = features.index(member)
                # Distance = 1 - NMI_score
                dist = 1.0 - block.get('nmi_score', 0.85)
                distance_matrix[rep_idx, mem_idx] = dist
                distance_matrix[mem_idx, rep_idx] = dist

    # Convert to condensed distance matrix
    condensed_dist = squareform(distance_matrix, checks=False)

    # Perform hierarchical clustering
    Z = linkage(condensed_dist, method='complete')

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    dendrogram(
        Z,
        labels=features,
        ax=ax,
        leaf_font_size=10,
    )
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylabel('Distance (1 - NMI)', fontsize=12)
    ax.set_xlabel('Features', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Dendrogram saved to: {output_path}")
        plt.close(fig)
        return Path(output_path)
    else:
        plt.show()
        return None


def plot_orthogonality_heatmap(
    result: StructureResult,
    output_path: Optional[Path] = None,
    figsize: tuple = (10, 8),
    title: str = "Stage 2: Orthogonality Check (Correlation Heatmap)",
) -> Optional[Path]:
    """
    Plot correlation heatmap of orthogonal components (Stage 2).

    Verifies that Gram-Schmidt orthogonalization produced zero-correlation
    components. Should show near-zero off-diagonal values.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_path : Path, optional
        Where to save the figure. If None, displays interactively.

    figsize : tuple, default=(10, 8)
        Figure size in inches.

    title : str
        Figure title.

    Returns
    -------
    Path or None
        Path where figure was saved, or None if displayed interactively.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import plot_orthogonality_heatmap
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> plot_orthogonality_heatmap(result, output_path='orthogonality.png')
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("ERROR: matplotlib and seaborn required for visualization")
        print("Install with: pip install matplotlib seaborn")
        return None

    if result.orthogonal_basis is None or result.orthogonal_basis.empty:
        print("No orthogonal_basis in result (Stage 2 failed?)")
        return None

    # Extract orthogonal components (exclude structure_id column)
    U = result.orthogonal_basis.drop(columns=['structure_id'])

    # Compute correlation matrix
    corr_matrix = U.corr()

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt='.3f',
        cmap='coolwarm',
        center=0.0,
        vmin=-0.1,
        vmax=0.1,
        square=True,
        cbar_kws={'label': 'Correlation'},
        ax=ax,
    )
    ax.set_title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Orthogonality heatmap saved to: {output_path}")
        plt.close(fig)
        return Path(output_path)
    else:
        plt.show()
        return None


def plot_cluster_distribution(
    result: StructureResult,
    output_path: Optional[Path] = None,
    figsize: tuple = (12, 6),
    title: str = "Stage 3: Cluster Size Distribution (HDBSCAN)",
) -> Optional[Path]:
    """
    Plot cluster size distribution (Stage 3).

    Shows number of clusters vs. number of instances per cluster.
    Includes "independent" instances (unclustered) as separate bar.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_path : Path, optional
        Where to save the figure. If None, displays interactively.

    figsize : tuple, default=(12, 6)
        Figure size in inches.

    title : str
        Figure title.

    Returns
    -------
    Path or None
        Path where figure was saved, or None if displayed interactively.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import plot_cluster_distribution
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> plot_cluster_distribution(result, output_path='cluster_dist.png')
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERROR: matplotlib required for visualization")
        print("Install with: pip install matplotlib")
        return None

    if result.orthogonal_basis is None or result.orthogonal_basis.empty:
        print("No orthogonal_basis in result (Stage 3 failed?)")
        return None

    # Extract structure_id values
    structure_ids = result.orthogonal_basis['structure_id']

    # Count cluster sizes
    cluster_sizes = structure_ids.value_counts().sort_index()

    # Separate "independent" from integer clusters
    if "independent" in cluster_sizes.index:
        independent_count = cluster_sizes["independent"]
        cluster_sizes = cluster_sizes[cluster_sizes.index != "independent"]
    else:
        independent_count = 0

    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Plot 1: Cluster size distribution
    cluster_sizes.plot(kind='bar', ax=ax1, color='steelblue', edgecolor='black')
    ax1.set_title('Cluster Sizes', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Cluster ID', fontsize=11)
    ax1.set_ylabel('Number of Instances', fontsize=11)
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Summary statistics
    summary_data = {
        'Clustered': len(structure_ids[structure_ids != "independent"]),
        'Independent': independent_count,
    }
    colors = ['steelblue', 'lightcoral']
    ax2.bar(summary_data.keys(), summary_data.values(), color=colors, edgecolor='black')
    ax2.set_title('Instance Classification', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Instances', fontsize=11)
    ax2.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for i, (k, v) in enumerate(summary_data.items()):
        ax2.text(i, v, f'{v:,}', ha='center', va='bottom', fontweight='bold')

    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Cluster distribution plot saved to: {output_path}")
        plt.close(fig)
        return Path(output_path)
    else:
        plt.show()
        return None


def plot_variance_explained(
    result: StructureResult,
    output_path: Optional[Path] = None,
    figsize: tuple = (12, 6),
    title: str = "Stage 2: Variance Explained by Component",
) -> Optional[Path]:
    """
    Plot variance explained by each orthogonal component.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_path : Path, optional
        Where to save the figure. If None, displays interactively.

    figsize : tuple, default=(12, 6)
        Figure size in inches.

    title : str
        Figure title.

    Returns
    -------
    Path or None
        Path where figure was saved, or None if displayed interactively.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import plot_variance_explained
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> plot_variance_explained(result, output_path='variance.png')
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("ERROR: matplotlib required for visualization")
        print("Install with: pip install matplotlib")
        return None

    if result.orthogonal_interpretation is None:
        print("No orthogonal_interpretation in result (interpretation failed?)")
        return None

    # Extract variance from summary
    summary_df = result.orthogonal_interpretation.get('summary')
    if summary_df is None or summary_df.empty:
        print("Cannot extract variance from interpretation summary")
        return None

    # Get component names and variance
    components = summary_df.get('Component ID', [])
    variances = summary_df.get('Retained Variance', [])

    if len(components) == 0:
        print("No components found in interpretation")
        return None

    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Plot 1: Individual variance
    ax1.bar(range(len(components)), variances, color='steelblue', edgecolor='black')
    ax1.set_title('Individual Component Variance', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Component', fontsize=11)
    ax1.set_ylabel('Retained Variance', fontsize=11)
    ax1.set_xticks(range(len(components)))
    ax1.set_xticklabels(components, rotation=45, ha='right')
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Cumulative variance
    cumsum_var = np.cumsum(variances)
    ax2.plot(
        range(len(components)),
        cumsum_var,
        marker='o',
        linewidth=2,
        markersize=8,
        color='steelblue',
    )
    ax2.fill_between(
        range(len(components)),
        cumsum_var,
        alpha=0.3,
        color='steelblue',
    )
    ax2.set_title('Cumulative Variance', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Component', fontsize=11)
    ax2.set_ylabel('Cumulative Variance', fontsize=11)
    ax2.set_xticks(range(len(components)))
    ax2.set_xticklabels(components, rotation=45, ha='right')
    ax2.grid(alpha=0.3)

    fig.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Variance plot saved to: {output_path}")
        plt.close(fig)
        return Path(output_path)
    else:
        plt.show()
        return None


def plot_contribution_heatmap(
    result: StructureResult,
    output_path: Optional[Path] = None,
    figsize: tuple = (12, 8),
    title: str = "Stage 2: Feature Contribution Heatmap (Percentage)",
    top_n_features: int = 20,
) -> Optional[Path]:
    """
    Plot feature contribution percentages to each orthogonal component.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_path : Path, optional
        Where to save the figure. If None, displays interactively.

    figsize : tuple, default=(12, 8)
        Figure size in inches.

    title : str
        Figure title.

    top_n_features : int, default=20
        Show only top N features by total contribution.

    Returns
    -------
    Path or None
        Path where figure was saved, or None if displayed interactively.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import plot_contribution_heatmap
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> plot_contribution_heatmap(result, output_path='contributions.png')
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("ERROR: matplotlib and seaborn required for visualization")
        print("Install with: pip install matplotlib seaborn")
        return None

    if result.orthogonal_interpretation is None:
        print("No orthogonal_interpretation in result")
        return None

    # Extract structured interpretation
    structured = result.orthogonal_interpretation.get('structured', {})
    if not structured:
        print("Cannot extract structured interpretation")
        return None

    # Build contribution matrix
    all_features = set()
    contributions = {}

    for comp_name, comp_info in structured.items():
        contributions[comp_name] = {}
        for contributor in comp_info.get('contributors', []):
            feature = contributor['feature']
            percentage = contributor['percentage']
            contributions[comp_name][feature] = percentage
            all_features.add(feature)

    # Create DataFrame
    contrib_df = pd.DataFrame(contributions).fillna(0)

    # Sort by total contribution and keep top N
    total_contrib = contrib_df.sum(axis=1).sort_values(ascending=False)
    contrib_df = contrib_df.loc[total_contrib.head(top_n_features).index]

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        contrib_df,
        annot=True,
        fmt='.1f',
        cmap='YlOrRd',
        cbar_kws={'label': 'Contribution (%)'},
        ax=ax,
    )
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Orthogonal Component', fontsize=12)
    ax.set_ylabel('Feature', fontsize=12)
    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Contribution heatmap saved to: {output_path}")
        plt.close(fig)
        return Path(output_path)
    else:
        plt.show()
        return None


def generate_all_visualizations(
    result: StructureResult,
    output_dir: Path = Path('./visualizations'),
    include_dendrogram: bool = True,
    include_orthogonality: bool = True,
    include_cluster_dist: bool = True,
    include_variance: bool = True,
    include_contributions: bool = True,
) -> dict[str, Path]:
    """
    Generate all available visualizations and save to directory.

    Parameters
    ----------
    result : StructureResult
        Result object from structure_id().

    output_dir : Path, default=Path('./visualizations')
        Output directory (created if doesn't exist).

    include_dendrogram : bool, default=True
        Generate Stage 1 dendrogram.

    include_orthogonality : bool, default=True
        Generate Stage 2 orthogonality heatmap.

    include_cluster_dist : bool, default=True
        Generate Stage 3 cluster distribution.

    include_variance : bool, default=True
        Generate variance explained plot.

    include_contributions : bool, default=True
        Generate feature contribution heatmap.

    Returns
    -------
    dict[str, Path]
        Mapping of visualization name to output path.

    Example
    -------
    >>> from structure_id import structure_id
    >>> from visualization import generate_all_visualizations
    >>> result = structure_id(data=df, target='y', task_type='classification')
    >>> paths = generate_all_visualizations(result, output_dir='./viz/')
    >>> print(paths)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {}

    try:
        if include_dendrogram:
            path = plot_dendrogram_stage1(
                result,
                output_path=output_dir / '01_dendrogram_stage1.png',
            )
            if path:
                paths['dendrogram_stage1'] = path

        if include_orthogonality:
            path = plot_orthogonality_heatmap(
                result,
                output_path=output_dir / '02_orthogonality_heatmap.png',
            )
            if path:
                paths['orthogonality_heatmap'] = path

        if include_cluster_dist:
            path = plot_cluster_distribution(
                result,
                output_path=output_dir / '03_cluster_distribution.png',
            )
            if path:
                paths['cluster_distribution'] = path

        if include_variance:
            path = plot_variance_explained(
                result,
                output_path=output_dir / '04_variance_explained.png',
            )
            if path:
                paths['variance_explained'] = path

        if include_contributions:
            path = plot_contribution_heatmap(
                result,
                output_path=output_dir / '05_contribution_heatmap.png',
            )
            if path:
                paths['contribution_heatmap'] = path

        print(f"\n✓ Generated {len(paths)} visualizations in {output_dir}")
        return paths

    except Exception as e:
        print(f"ERROR generating visualizations: {e}")
        print("Ensure matplotlib and seaborn are installed:")
        print("  pip install matplotlib seaborn scipy")
        return paths


if __name__ == '__main__':
    """
    Example usage:
    
    python visualization.py
    
    Generates sample visualizations (requires sample data).
    """
    print("visualization.py - Plotting utilities for structure_id results")
    print("\nUsage:")
    print("  from visualization import generate_all_visualizations")
    print("  from structure_id import structure_id")
    print("")
    print("  result = structure_id(data=df, target='y', task_type='classification')")
    print("  paths = generate_all_visualizations(result, output_dir='./viz')")
