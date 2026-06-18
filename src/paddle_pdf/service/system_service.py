"""System diagnostics service — GPU detection, environment info."""

from __future__ import annotations

from ..common.schemas import GpuInfo
from ..core import gpu_utils


class SystemService:
    """System environment queries."""

    def check_gpu(self) -> GpuInfo:
        """Check GPU availability."""
        return gpu_utils.check_gpu_available()

    def diagnose(self) -> dict[str, str]:
        """Run full environment diagnosis."""
        gpu_info = self.check_gpu()
        cuda_env = gpu_utils.detect_cuda_environment()

        return {
            "gpu_available": str(gpu_info.available),
            "gpu_device_count": str(gpu_info.device_count),
            "cuda_version": gpu_info.cuda_version or "N/A",
            "cuda_root": gpu_info.cuda_root or "N/A",
            "gpu_error": gpu_info.error or "None",
            "cuda_runtime_path": cuda_env.get("runtime_path") or "N/A",
        }
