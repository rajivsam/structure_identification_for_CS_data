from dataclasses import dataclass
from typing import Any


@dataclass
class StructureIDConfig:
    correlation_threshold: float = 0.85
    min_cluster_size: int = 15
    alpha: float = 0.05
    std_threshold: float = 1e-5
    max_missing_ratio: float = 0.20
    max_categories: int = 30
    max_class_concentration: float = 0.98

    @classmethod
    def from_dict(cls, config: dict[str, Any] | None = None) -> "StructureIDConfig":
        if config is None:
            return cls()
        return cls(**{k: v for k, v in config.items() if hasattr(cls, k)})

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_threshold": self.correlation_threshold,
            "min_cluster_size": self.min_cluster_size,
            "alpha": self.alpha,
            "std_threshold": self.std_threshold,
            "max_missing_ratio": self.max_missing_ratio,
            "max_categories": self.max_categories,
            "max_class_concentration": self.max_class_concentration,
        }
