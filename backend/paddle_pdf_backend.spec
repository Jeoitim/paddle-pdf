# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

SRC = str(Path(SPECPATH).parent / "src")
HOOKS_DIR = str(Path(SPECPATH) / "hooks")

# Auto-collect all dependencies, data files, and binaries for paddle libraries
paddle_datas, paddle_binaries, paddle_hiddenimports = collect_all('paddle')
ocr_datas, ocr_binaries, ocr_hiddenimports = collect_all('paddleocr')
pdx_datas, pdx_binaries, pdx_hiddenimports = collect_all('paddlex')

hiddenimports = [
    "uvicorn.logging","uvicorn.loops","uvicorn.loops.auto",
    "uvicorn.protocols","uvicorn.protocols.http","uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets","uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan","uvicorn.lifespan.on",
    "anyio","anyio._backends._asyncio",
    "cv2","pymupdf","PIL","pydantic","pydantic_core",
    "fastapi","starlette","starlette.middleware.cors",
    "unittest","unittest.mock","xmlrpc","xmlrpc.client",
    "distutils","distutils.version",
] + paddle_hiddenimports + ocr_hiddenimports + pdx_hiddenimports

excludes = [
    "paddle.distributed","paddle.fluid.tests","paddle.base.tests",
    "paddle.hapi","paddle.text","paddle.vision.datasets",
    "pytest","IPython","ipykernel","ipython_genutils","jupyter","notebook",
    "Cython","numba","llvmlite",
    "tkinter","PyQt5","PyQt6","wx",
    "lib2to3",
    "conda","conda_package_handling","conda_package_streaming",
]

a = Analysis(
    [SRC + "/paddle_pdf/app/http_server.py"],
    pathex=[SRC],
    binaries=paddle_binaries + ocr_binaries + pdx_binaries,
    datas=paddle_datas + ocr_datas + pdx_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[HOOKS_DIR + "/rth_paddle.py"],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="paddle_pdf_backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="paddle_pdf_backend",
)

