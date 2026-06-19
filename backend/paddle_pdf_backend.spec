# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

SRC = str(Path(SPECPATH).parent / "src")

hiddenimports = [
    "uvicorn.logging","uvicorn.loops","uvicorn.loops.auto",
    "uvicorn.protocols","uvicorn.protocols.http","uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets","uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan","uvicorn.lifespan.on",
    "anyio","anyio._backends._asyncio",
    "paddle","paddle.base","paddleocr","paddlex",
    "cv2","pymupdf","PIL","pydantic","pydantic_core",
    "fastapi","starlette","starlette.middleware.cors",
]

excludes = [
    "paddle.distributed","paddle.fluid.tests","paddle.base.tests",
    "paddle.hapi","paddle.text","paddle.vision.datasets",
    "pytest","IPython","ipykernel","ipython_genutils","jupyter","notebook",
    "Cython","numba","llvmlite",
    "tkinter","PyQt5","PyQt6","wx",
    "test","tests","unittest","xmlrpc","lib2to3",
    "conda","conda_package_handling","conda_package_streaming",
]

a = Analysis(
    [SRC + "/paddle_pdf/app/http_server.py"],
    pathex=[SRC],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
