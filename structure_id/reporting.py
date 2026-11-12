from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path

import pandas as pd

from .types import StructureResult


def _structure_id_distribution(result: StructureResult) -> list[str]:
    values = result.diagnostics.get("structure_id_values")
    if not isinstance(values, dict) or not values:
        return []

    counts = Counter(str(value) for value in values.values())
    lines = ["- Instance structure summary:"]
    noise_count = counts.get("noise", 0)
    cluster_counts = sorted(
        ((int(label), count) for label, count in counts.items() if label != "noise"),
        key=lambda item: item[0],
    )
    if noise_count:
        lines.append(f"  noise={noise_count}")
    if cluster_counts:
        for cluster_id, count in cluster_counts:
            lines.append(f"  cluster_{cluster_id}={count}")
    else:
        lines.append("  no valid instance clusters assigned")
    return lines


def _cluster_profile(result: StructureResult) -> list[str]:
    profile = result.diagnostics.get("cluster_profile_data")
    if profile is None or not isinstance(profile, pd.DataFrame):
        return []

    if "structure_id" not in profile.columns:
        return []

    numeric = profile.select_dtypes(include=["number"]).copy()
    if numeric.empty:
        return ["- No numeric training features available for cluster profiling."]

    overall_mean = numeric.mean()
    overall_std = numeric.std(ddof=0).replace(0, pd.NA)
    valid_labels: list[int | str] = []
    for label in set(profile["structure_id"]):
        if str(label) == "noise":
            continue
        try:
            valid_labels.append(int(label))
        except (TypeError, ValueError):
            valid_labels.append(str(label))

    if not valid_labels:
        return ["- No valid training clusters available for profile generation."]

    valid_labels = sorted(valid_labels, key=lambda value: (0 if isinstance(value, int) else 1, str(value)))

    lines = ["", "Basic profile (training data):"]
    for label in valid_labels:
        members = profile[profile["structure_id"] == label]
        if members.empty:
            continue

        rankings: list[tuple[float, str, float]] = []
        for col in numeric.columns:
            std = overall_std.get(col)
            if pd.isna(std) or std == 0:
                continue
            effect = (members[col].mean() - overall_mean[col]) / float(std)
            rankings.append((abs(effect), col, effect))

        rankings.sort(reverse=True)
        top = rankings[:3]
        top_description = ", ".join(
            f"{feature}({effect:+.2f}sd)" for _, feature, effect in top
        ) if top else "no numeric contrast"
        lines.append(f"- Cluster {label}: n={len(members)}; representative features: {top_description}")

    lines.extend(["", "Interpretive summary (training data):"])
    for label in valid_labels:
        members = profile[profile["structure_id"] == label]
        if members.empty:
            continue

        rankings: list[tuple[float, str, float]] = []
        for col in numeric.columns:
            std = overall_std.get(col)
            if pd.isna(std) or std == 0:
                continue
            effect = (members[col].mean() - overall_mean[col]) / float(std)
            rankings.append((abs(effect), col, effect))

        rankings.sort(reverse=True)
        top = rankings[:3]
        if not top:
            lines.append(f"- Cluster {label}: no stable numeric contrast detected.")
            continue

        summary = ", ".join(f"{feature} {effect:+.2f}sd" for _, feature, effect in top)
        direction = "higher than overall" if top[0][2] > 0 else "lower than overall"
        lines.append(
            f"- Cluster {label}: strongest separation is {summary}; this cluster is generally {direction} on its leading features."
        )

    return lines


def _profile_data_for_export(result: StructureResult) -> tuple[pd.DataFrame, list[int | str]] | None:
    profile = result.diagnostics.get("cluster_profile_data")
    if not isinstance(profile, pd.DataFrame) or "structure_id" not in profile.columns:
        return None

    numeric = profile.select_dtypes(include=["number"]).copy()
    if numeric.empty:
        return None

    labels = []
    for label in sorted(set(profile["structure_id"]), key=lambda value: (str(value) != "noise", str(value))):
        if str(label) == "noise":
            continue
        labels.append(int(label) if str(label).isdigit() else str(label))
    return numeric, labels


def generate_cluster_profile_markdown(result: StructureResult) -> str:
    profile = result.diagnostics.get("cluster_profile_data")
    if not isinstance(profile, pd.DataFrame) or "structure_id" not in profile.columns:
        return "# Training Cluster Profile\n\nNo training cluster profile is available."

    numeric = profile.drop(columns=["structure_id"]).select_dtypes(include=["number"]).copy()
    if numeric.empty:
        return "# Training Cluster Profile\n\nNo numeric training features are available for cluster profiling."

    overall_mean = numeric.mean()
    overall_std = numeric.std(ddof=0).replace(0, pd.NA)
    values = Counter(str(value) for value in profile["structure_id"].tolist())
    noise_count = values.get("noise", 0)
    cluster_labels = [
        int(label) if str(label).isdigit() else str(label)
        for label in sorted(set(profile["structure_id"]), key=lambda value: (str(value) == "noise", str(value)))
        if str(label) != "noise"
    ]

    lines = [
        "# Training Cluster Profile",
        "",
        "## Summary",
        f"- Noise rows: {noise_count}",
        f"- Valid clusters: {len(cluster_labels)}",
        "",
        "## Cluster-level interpretation",
    ]

    for label in cluster_labels:
        label_value = int(label) if isinstance(label, int) else str(label)
        members = profile[profile["structure_id"] == label_value]
        rankings: list[tuple[float, str, float]] = []
        for col in numeric.columns:
            std = overall_std.get(col)
            if pd.isna(std) or std == 0:
                continue
            effect = (members[col].mean() - overall_mean[col]) / float(std)
            rankings.append((abs(effect), col, effect))

        rankings.sort(reverse=True)
        top = rankings[:3]
        top_summary = ", ".join(f"{feature} ({effect:+.2f}sd)" for _, feature, effect in top) if top else "no stable contrast"
        direction = "higher than overall" if top[0][2] > 0 else "lower than overall"
        lines.extend([
            f"### Cluster {label_value}",
            f"- Size: {len(members)}",
            f"- Leading features: {top_summary}",
            f"- Interpretation: this cluster is generally {direction} on its strongest discriminating features.",
            "",
        ])

    return "\n".join(lines)


def _markdown_to_html(markdown_text: str) -> str:
    html_lines = [
        "<html>",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }",
        "h1, h2, h3 { color: #111827; }",
        "ul { margin-top: 0.25rem; }",
        "li { margin-bottom: 0.25rem; }",
        "code { background: #f3f4f6; padding: 0.1rem 0.25rem; border-radius: 3px; }",
        "</style>",
        "</head>",
        "<body>",
    ]

    previous_was_list = False
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            if previous_was_list:
                html_lines.append("</ul>")
                previous_was_list = False
            html_lines.append("")
            continue
        if line.startswith("# "):
            if previous_was_list:
                html_lines.append("</ul>")
                previous_was_list = False
            html_lines.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            if previous_was_list:
                html_lines.append("</ul>")
                previous_was_list = False
            html_lines.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("### "):
            if previous_was_list:
                html_lines.append("</ul>")
                previous_was_list = False
            html_lines.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("- "):
            if not previous_was_list:
                html_lines.append("<ul>")
                previous_was_list = True
            html_lines.append(f"<li>{escape(line[2:])}</li>")
            continue

        if previous_was_list:
            html_lines.append("</ul>")
            previous_was_list = False
        html_lines.append(f"<p>{escape(line)}</p>")

    if previous_was_list:
        html_lines.append("</ul>")

    html_lines.extend(["</body>", "</html>"])
    return "\n".join(html_lines)


def export_cluster_profile_report(
    result: StructureResult,
    output_dir: str | Path = "reports",
    filename_prefix: str = "training_cluster_profile",
) -> dict[str, Path]:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = report_dir / f"{filename_prefix}.md"
    html_path = report_dir / f"{filename_prefix}.html"

    markdown_text = generate_cluster_profile_markdown(result)
    markdown_path.write_text(markdown_text, encoding="utf-8")
    html_path.write_text(_markdown_to_html(markdown_text), encoding="utf-8")

    return {"markdown": markdown_path, "html": html_path}


def generate_report(result: StructureResult) -> str:
    lines = [
        "Structure Identification Report",
        "=" * 32,
        f"Target: {result.target}",
        f"Task type: {result.task_type}",
        f"Provisional candidates: {len(result.provisional_columns)}",
        f"Selected candidates: {len(result.selected_columns)}",
        "",
        "Explicit column structures:",
    ]

    if not result.explicit_column_structures:
        lines.append("- No redundant feature blocks detected.")
    else:
        for block in result.explicit_column_structures:
            lines.append(f"- {block.describe()}")
            if block.merge_history:
                for item in block.merge_history[:3]:
                    left, right = item["merged_pair"]
                    rho = float(item["spearman_rho"])
                    lines.append(
                        f"    pair={left}↔{right}, rho={rho:.4f}, distance={1.0 - abs(rho):.4f}"
                    )

    lines.extend(["", "Explicit row clusters:"])
    if not result.explicit_row_clusters:
        lines.append("- No valid macro-clusters detected.")
    else:
        for cluster in result.explicit_row_clusters:
            lines.append(
                f"- Cluster {cluster.cluster_id}: size={cluster.size}, rows={cluster.row_indices[:10]}"
            )

    lines.extend(_structure_id_distribution(result))
    lines.extend(_cluster_profile(result))

    if "structure_id" in result.selected_columns:
        lines.append(
            "- Instance clustering: added feature 'structure_id' with noise rows labeled 'noise' and cluster rows labeled by the HDBSCAN cluster id."
        )

    lines.extend(["", "Latent structure:"])
    if result.latent_break is None:
        lines.append("- No statistically significant latent break detected.")
    else:
        lines.append(
            f"- Variable={result.latent_break.variable_name}, "
            f"adj_p={result.latent_break.adjusted_p_value:.4g}, "
            f"sig={result.latent_break.significant}"
        )

    return "\n".join(lines)
