"""CUDA / GPU environment detection and setup."""

import os
import logging
from pathlib import Path
from typing import Optional

from ..common.schemas import GpuInfo

logger = logging.getLogger(__name__)


def detect_cuda_environment() -> dict[str, Optional[str]]:
    """Auto-detect CUDA Toolkit installation and return environment settings."""
    result: dict[str, Optional[str]] = {
        "cuda_root": None,
        "cuda_version": None,
        "runtime_path": None,
    }

    cuda_base = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if not cuda_base.exists():
        return result

    cuda_versions: list[str] = []
    for d in cuda_base.iterdir():
        if d.is_dir() and d.name.lower().startswith("v"):
            nvcc = d / "bin" / "nvcc.exe"
            if nvcc.exists():
                cuda_versions.append(d.name)

    if not cuda_versions:
        return result

    def ver_key(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v[1:].split("."))

    cuda_versions.sort(key=ver_key, reverse=True)
    newest = cuda_versions[0]
    cuda_root = str(cuda_base / newest)
    result["cuda_root"] = cuda_root
    result["cuda_version"] = newest

    runtime_candidates = [
        os.path.join(cuda_root, "bin", "x64"),
        os.path.join(cuda_root, "bin"),
    ]

    conda_base = os.path.dirname(
        cuda_root.split("\\CUDA\\")[0] if "\\CUDA\\" in cuda_root else cuda_root
    )
    conda_pkgs = os.path.join(conda_base, "pkgs")
    if os.path.exists(conda_pkgs):
        for d in os.listdir(conda_pkgs):
            if "cuda-cudart" in d.lower() and "dev" not in d.lower():
                p = os.path.join(conda_pkgs, d, "Library", "bin")
                if os.path.exists(p):
                    runtime_candidates.append(p)

    for p in runtime_candidates:
        if os.path.exists(p):
            dlls = os.listdir(p)
            if any("cudart" in f.lower() for f in dlls):
                result["runtime_path"] = p
                break

    return result


def setup_gpu_environment() -> bool:
    """Configure CUDA DLL paths in os.environ. Returns True if successful."""
    cuda_info = detect_cuda_environment()

    if not cuda_info["cuda_root"]:
        logger.warning("CUDA Toolkit not found. GPU mode will not be available.")
        return False

    logger.info(
        f"CUDA detected: {cuda_info['cuda_version']} at {cuda_info['cuda_root']}"
    )

    if cuda_info["runtime_path"]:
        logger.info(f"CUDA runtime DLLs: {cuda_info['runtime_path']}")
        current_path = os.environ.get("PATH", "")
        if cuda_info["runtime_path"] not in current_path:
            os.environ["PATH"] = cuda_info["runtime_path"] + os.pathsep + current_path
        os.environ["CUDA_HOME"] = cuda_info["cuda_root"]
        os.environ["CUDA_PATH"] = cuda_info["cuda_root"]
        return True

    return False


def check_gpu_available(verbose: bool = False) -> GpuInfo:
    """Check if GPU is available and working. Returns GpuInfo."""
    cuda_env = detect_cuda_environment()
    info = GpuInfo(
        cuda_version=cuda_env.get("cuda_version"),
        cuda_root=cuda_env.get("cuda_root"),
    )

    try:
        import paddle

        count = paddle.device.cuda.device_count()
        info.device_count = count
        if count > 0:
            paddle.device.set_device("gpu:0")
            x = paddle.to_tensor([1.0])
            _ = x * 2
            info.available = True
    except Exception as e:
        info.error = str(e)
        if verbose:
            logger.warning(f"GPU check failed: {e}")
    return info


def configure_cuda_for_engine(verbose: bool = False) -> bool:
    """Configure CUDA env vars for PaddleOCR engine init. Returns True if configured."""
    cuda_info = detect_cuda_environment()
    if not cuda_info["cuda_root"]:
        if verbose:
            logger.warning("CUDA Toolkit not found in standard location")
        return False

    if cuda_info["runtime_path"]:
        current_path = os.environ.get("PATH", "")
        if cuda_info["runtime_path"] not in current_path:
            os.environ["PATH"] = cuda_info["runtime_path"] + os.pathsep + current_path
        os.environ["CUDA_HOME"] = cuda_info["cuda_root"]
        os.environ["CUDA_PATH"] = cuda_info["cuda_root"]
        if verbose:
            logger.info(
                f"CUDA configured: {cuda_info['cuda_version']} ({cuda_info['cuda_root']})"
            )
            logger.info(f"Runtime DLLs: {cuda_info['runtime_path']}")
        return True

    if verbose:
        logger.warning(
            f"CUDA {cuda_info['cuda_version']} found but runtime DLLs not detected"
        )
    return False
