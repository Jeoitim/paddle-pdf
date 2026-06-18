#!/usr/bin/env python3
"""
PDF OCR CLI - GPU Environment Diagnostic

Checks the current Python/PaddlePaddle environment and writes results to check_env.txt.
Run with: pixi run check-gpu
"""

import subprocess
import sys
import os

results = []


def run(cmd, desc):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=True)
        results.append(f"=== {desc} ===")
        results.append(f"stdout: {r.stdout[:200]}")
        results.append(f"stderr: {r.stderr[:200]}")
        results.append(f"rc: {r.returncode}")
    except Exception as e:
        results.append(f"=== {desc} ERROR ===")
        results.append(str(e))


python = sys.executable

run(f'"{python}" --version', "Python version")
run(f'"{python}" -c "import paddle; print(paddle.__version__)"', "Paddle version")
run(
    f'"{python}" -c "import paddle; print(paddle.device.cuda.device_count())"',
    "GPU count",
)
run(
    f'"{python}" -c "import paddle; x=paddle.to_tensor([1]); print(x.device)"',
    "Tensor device",
)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_env.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(results))
print(f"Results written to: {output_path}", file=sys.stderr)
