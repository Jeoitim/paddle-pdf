"""Model management service."""

from __future__ import annotations

from ..common.schemas import ModelInfo
from ..core import models


class ModelService:
    """Query, download, and manage OCR models."""

    def list_models(self) -> list[ModelInfo]:
        """Return all models with cache status."""
        result: list[ModelInfo] = []
        for name, info in models.MODEL_REGISTRY.items():
            result.append(
                ModelInfo(
                    name=name,
                    desc=info["desc"],
                    lang=info["lang"],
                    model_type=info.get("model_type", ""),
                    note=info.get("note", ""),
                    cached=models.is_model_cached(name),
                )
            )
        return result

    def get_model_info(self, name: str) -> ModelInfo:
        """Get info for a single model."""
        info = models.get_model_info(name)
        return ModelInfo(
            name=name,
            desc=info["desc"],
            lang=info["lang"],
            model_type=info.get("model_type", ""),
            note=info.get("note", ""),
            cached=models.is_model_cached(name),
        )

    def is_cached(self, name: str) -> bool:
        return models.is_model_cached(name)

    def download(self, name: str, force: bool = False) -> bool:
        return models.download_model(name, force=force)
