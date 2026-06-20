# PyInstaller Runtime Hook for PaddlePaddle
# This hook runs BEFORE the main application script.
# It forces paddle submodules to be imported in the correct order,
# preventing "partially initialized module 'paddle'" circular import errors
# that occur when PyInstaller's frozen importer changes the import sequence.

import sys
import os

# Suppress paddle's model source connectivity check which causes delays at startup
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Force paddle core submodules to initialize in correct dependency order
# before any application code runs. This resolves circular import issues.
try:
    import paddle.fluid  # noqa: F401 - initializes C++ backend
    import paddle.base   # noqa: F401 - base framework
    import paddle.tensor # noqa: F401 - tensor operations (commonly missing)
    import paddle.nn     # noqa: F401 - neural network modules
    import paddle.device # noqa: F401 - device management (needed for GPU check)
except Exception:
    # If paddle itself fails to load, let the main app handle the error
    pass
