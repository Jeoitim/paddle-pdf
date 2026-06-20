import sys
import os
import importlib.metadata
import importlib.util

# Monkeypatch importlib.metadata.version to support frozen package metadata checks.
# When packaged by PyInstaller, standard metadata files (.dist-info/.egg-info) are not present,
# causing importlib.metadata.PackageNotFoundError. This dynamic patch checks if the module
# is actually importable (meaning it is bundled inside the executable) and returns a dummy
# version string to satisfy Paddlex's internal dependency checks.
_original_version = importlib.metadata.version

def _patched_version(package_name):
    try:
        return _original_version(package_name)
    except importlib.metadata.PackageNotFoundError:
        module_mapping = {
            "opencv-contrib-python": "cv2",
            "opencv-python": "cv2",
            "opencv-python-headless": "cv2",
            "pyclipper": "pyclipper",
            "shapely": "shapely",
            "pypdfium2": "pypdfium2",
            "python-bidi": "bidi",
            "imagesize": "imagesize",
            "beautifulsoup4": "bs4",
            "einops": "einops",
            "ftfy": "ftfy",
            "Jinja2": "jinja2",
            "lxml": "lxml",
            "openpyxl": "openpyxl",
            "premailer": "premailer",
            "regex": "regex",
            "safetensors": "safetensors",
            "scikit-learn": "sklearn",
            "scipy": "scipy",
            "sentencepiece": "sentencepiece",
            "tiktoken": "tiktoken",
            "tokenizers": "tokenizers",
        }
        mod_name = module_mapping.get(package_name, package_name)
        try:
            if importlib.util.find_spec(mod_name) is not None:
                if "opencv" in package_name:
                    return "4.10.0.84"
                return "1.0.0"
        except Exception:
            pass
        raise importlib.metadata.PackageNotFoundError(package_name)

importlib.metadata.version = _patched_version

# Add host CUDA Toolkit bin directory to the DLL search path and system PATH
# so that the OS loader can resolve CUDA/cuDNN DLLs (like cudnn64_9.dll, cubart64_12.dll)
# from the user's local NVIDIA installation.
try:
    from pathlib import Path
    _cuda_base = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if _cuda_base.exists():
        _cuda_dirs = []
        for _d in _cuda_base.iterdir():
            if _d.is_dir() and _d.name.lower().startswith("v"):
                _nvcc = _d / "bin" / "nvcc.exe"
                if _nvcc.exists():
                    _cuda_dirs.append(_d)
        if _cuda_dirs:
            def _ver_key(d):
                try:
                    return tuple(int(x) for x in d.name[1:].split("."))
                except Exception:
                    return (0,)
            _cuda_dirs.sort(key=_ver_key, reverse=True)
            _newest_cuda = _cuda_dirs[0]
            _bin_dir = _newest_cuda / "bin"
            if _bin_dir.exists():
                os.environ["PATH"] = str(_bin_dir) + os.pathsep + os.environ.get("PATH", "")
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(str(_bin_dir))
                    except Exception:
                        pass
except Exception as e:
    sys.stderr.write(f"Warning: Failed to configure host CUDA environment: {e}\n")
    sys.stderr.flush()

# Fallback: search for local .pixi directory (if running on developer's machine)
# to locate cudnn/cuda DLLs and add them to path to simplify dev-testing of packaged app.
try:
    from pathlib import Path
    _exec_dir = Path(sys.executable).parent
    _proj_root = _exec_dir
    _pixi_dir = None
    for _ in range(6):
        if (_proj_root / ".pixi").exists():
            _pixi_dir = _proj_root / ".pixi"
            break
        _proj_root = _proj_root.parent

    if _pixi_dir:
        _added_dirs = set()
        # Find all cudnn, cublas, and cuda runtime DLLs in the .pixi envs
        _patterns = ["cudnn*.dll", "cublas64*.dll", "cudart64*.dll"]
        for _pat in _patterns:
            for _dll in _pixi_dir.rglob(_pat):
                _dir = _dll.parent
                if _dir not in _added_dirs:
                    os.environ["PATH"] = str(_dir) + os.pathsep + os.environ.get("PATH", "")
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(str(_dir))
                        except Exception:
                            pass
                    _added_dirs.add(_dir)
except Exception as e:
    sys.stderr.write(f"Warning: Failed to configure local .pixi DLL fallback: {e}\n")
    sys.stderr.flush()

# Suppress paddle's model source connectivity check which causes delays at startup
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Force paddle core submodules to initialize in correct dependency order
# before any application code runs. This resolves circular import issues.
try:
    import paddle.base   # noqa: F401 - base framework
    import paddle.tensor # noqa: F401 - tensor operations (commonly missing)
    import paddle.nn     # noqa: F401 - neural network modules
    import paddle.device # noqa: F401 - device management (needed for GPU check)
except Exception as e:
    import traceback
    sys.stderr.write(f"Error in rth_paddle runtime hook: {e}\n")
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
