# 开发者文档

## 项目概述

基于 PaddleOCR 的 PDF 文字识别工具，支持 **CLI 命令行** 和 **GUI 图形界面** 两种使用方式。GUI 基于 pytauri（Python + Tauri + Vue 3）实现跨平台桌面应用。

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 桌面壳 | Tauri | 2.11 |
| Python 桥 | pytauri | 0.4 |
| 前端框架 | Vue 3 + TypeScript | 3.5 |
| UI 组件库 | Naive UI | 2.44 |
| 构建工具 | Vite | 8.0 |
| CSS | UnoCSS | 66.7 |
| 状态管理 | Pinia | 3.0 |
| OCR 引擎 | PaddleOCR | 3.4.1 |
| PDF 处理 | PyMuPDF (fitz) | 1.25+ |
| Python | CPython | 3.12 |
| GPU | PaddlePaddle GPU | 3.3.0 (CUDA 12.6) |
| 包管理 | pixi + pnpm | — |

## 项目结构（MVC 架构）

```
paddle_pdf/
├── src/paddle_pdf/           # Python 后端
│   ├── core/                 #   Model — 纯业务逻辑，无 UI 依赖
│   │   ├── ocr_engine.py     #     PaddleOCR 引擎封装
│   │   ├── pdf_pipeline.py   #     PDF 处理管线
│   │   ├── models.py         #     模型注册表 (7 种语言)
│   │   └── gpu_utils.py      #     CUDA 检测
│   ├── service/              #   Service — 编排 core，通过回调上报进度
│   │   ├── ocr_service.py    #     OCR 任务编排
│   │   ├── model_service.py  #     模型管理
│   │   └── system_service.py #     系统诊断
│   ├── controller/           #   Controller — 协议适配层
│   │   ├── cli_controller.py #     argparse CLI
│   │   └── ipc_controller.py #     pytauri IPC 端点 (11 个命令)
│   ├── common/               #   公共定义
│   │   ├── schemas.py        #     dataclass 数据结构
│   │   ├── events.py         #     IPC 事件常量
│   │   └── config.py         #     全局配置
│   └── app/                  #   应用入口
│       ├── cli_app.py        #     CLI 入口
│       └── pytauri_app.py    #     GUI 入口 (pytauri)
│
├── src-frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/            #     HomeView, TaskDetailView, SettingsView
│   │   ├── components/       #     FileDropZone, TaskCard, TaskProgress,
│   │   │                     #     ModelSelector, GpuStatus, TextPanel
│   │   ├── stores/           #     Pinia: task, settings, app
│   │   ├── composables/      #     useIpc, useTask, useModels
│   │   └── types/            #     TypeScript 类型定义
│   └── src-tauri/            #     Tauri Rust 壳
│       ├── src/lib.rs        #       pytauri 扩展模块 (pymodule_export)
│       ├── src/main.rs       #       Python 嵌入入口 (PythonInterpreterBuilder)
│       └── tauri.conf.json   #       Tauri 配置
│
├── doc/                      # 文档
├── pixi.toml                 # Python + Node 依赖
└── README.md
```

## pytauri 架构详解

### IPC 通信流程

```
┌─────────────────┐     pyInvoke("cmd", body)     ┌──────────────────┐
│  Vue Frontend   │ ─────────────────────────────→ │  Tauri Plugin    │
│  (useIpc.ts)    │                                │  (pyfunc handler)│
│                 │ ← ─ ─ Emitter.emit(event) ─ ─ ─│                  │
└─────────────────┘                                └──────────────────┘
                                                          │
                                                    invoke_handler
                                                          ↓
                                                   ┌──────────────┐
                                                   │  pytauri      │
                                                   │  Commands     │
                                                   │  (Python)     │
                                                   └──────────────┘
                                                          │
                                                          ↓
                                                   ┌──────────────┐
                                                   │  Service 层   │
                                                   │  Core 层      │
                                                   └──────────────┘
```

### 关键实现细节

1. **Rust `lib.rs`**：通过 `pytauri::pymodule_export` 创建 Python 扩展模块，导出 `context_factory` 和 `builder_factory`
2. **Rust `main.rs`**：使用 `PythonInterpreterBuilder` (standalone 模式) 嵌入 Python 解释器，运行入口模块
3. **Python `pytauri_app.py`**：使用 `Commands` 注册 IPC 命令，通过 `BlockingPortal` 异步处理
4. **前端 `useIpc.ts`**：使用 `pyInvoke` (来自 `tauri-plugin-pytauri-api`) 而非原生 `invoke`
5. **pytauri 命令签名**：`async def cmd(body: BaseModel) -> BaseModel | bytes`，`body` 和 `app_handle` 是特殊参数名

### 命令注册规范

```python
from pytauri import Commands, AppHandle, Emitter
from pydantic import BaseModel

commands = Commands()

class MyRequest(BaseModel):
    name: str

class MyResponse(BaseModel):
    message: str

@commands.command()
async def my_command(body: MyRequest) -> MyResponse:
    return MyResponse(message=f"Hello {body.name}")

# 无参数命令用 EmptyBody
class EmptyBody(BaseModel): pass

@commands.command()
async def no_args(body: EmptyBody) -> bytes:
    return b"ok"

# 需要 emit 事件的命令加 app_handle 参数
@commands.command()
async def with_progress(body: MyRequest, app_handle: AppHandle) -> MyResponse:
    Emitter.emit(app_handle, "progress", ProgressPayload(...))
    return MyResponse(message="done")
```

### 注意事项

- **不要使用 `from __future__ import annotations`**：pytauri 的 `wrap_pyfunc` 需要运行时类型注解做 `issubclass` 检查
- **`app_handle` 参数类型必须是 `AppHandle`**：不能用 `Any`
- **返回 `bytes` 的命令**：前端收到的是原始 bytes，需手动 JSON.parse
- **`PYTHONPATH` 必须包含 `src/` 目录**：在 pixi.toml 的 tauri tasks 中通过 env 设置

## PaddleOCR 3.x API 关键差异

### 构造函数参数

| 旧参数 (2.x) | 新参数 (3.x) | 说明 |
|---|---|---|
| `use_gpu=True/False` | **已移除** | 改用 `paddle.device.set_device("gpu:0")` |
| `show_log=False` | **已移除** | 不再支持 |
| `use_angle_cls=True` | `use_textline_orientation=True` | 参数改名 |

### 返回结果格式

```python
# 旧版 2.x: [[bbox, (text, score)], ...]
# 新版 3.x: [OCRResult] (dict-like)

ocr_result = raw_result[0]
rec_texts = ocr_result["rec_texts"]     # list[str]
rec_scores = ocr_result["rec_scores"]   # list[float] (0-1)
rec_polys = ocr_result["rec_polys"]     # list[polygon], 每个 polygon = [[x,y]×4]
```

### bbox 处理

```python
import numpy as np

pts = np.array(bbox)         # shape (4, 2)
x0, y0 = pts.min(axis=0)
x1, y1 = pts.max(axis=0)
```

## PDF 可搜索层写入

使用 PyMuPDF (fitz) 将 OCR 文本以完全透明的模式（`render_mode=3`）精准叠加到原始 PDF。

### 核心算法

1. **图像检测高分辨率限制**：针对小字（如页眉、下标）容易合并或丢失的问题，设置了高分辨率文本检测限制。当启用 GPU 时，`text_det_limit_side_len` 默认设为 `4320`（支持无损检测 400 DPI 以上的 B5/A4 页面）；当使用 CPU 时设为 `1920` 以平衡内存与时间开销。
2. **字体预注册与嵌入**：检测系统 CJK 字体，降级使用 PyMuPDF 内置 `cjk` 字体包。
3. **字号匹配（宽度优先，高度截断容差）**：优先满足宽度匹配（即 `fs_by_width`），仅在严重超高时截断（允许最大 1.05 倍高度的容差），以保证选中高亮框的宽度与底层图片中文字完全契合。
4. **自适应字间距（TextWriter 逐字写入）**：使用 `fitz.TextWriter` 逐字符追加，并通过计算差值 `(target_width - text_width) / (n - 1)` 动态分配字间距，保留原始字符间的空格或稀疏排版。
5. **基线精准定位与限制**：将文本在 bounding box 垂直范围内居中，利用 Ascender 定位：`baseline_y = ry0 + (target_height - fontsize) / 2 + ascender * fontsize`。这保证了当 OCR 检测框由于行高偏大或包含额外空白时，文字依然能完美限定并居中放置在框线边界 `[ry0, ry1]` 内部，消除了摘要和标题等的系统性偏移。

## 环境搭建

```bash
# 安装所有依赖（含 Node.js、pnpm）
pixi install

# CLI
pixi run run -- -i "book.pdf"

# GUI 开发模式
pixi run tauri-dev

# GUI 生产构建
pixi run tauri-build

# GPU 诊断
pixi run check-gpu
```

## 常见错误速查

| 错误现象 | 原因 | 修复方法 |
|---|---|---|
| `Unknown argument: use_gpu` | PaddleOCR 3.x 已删除该参数 | 改用 `paddle.device.set_device()` |
| `Unknown argument: use_angle_cls` | 参数被重命名 | 改为 `use_textline_orientation=True` |
| `not enough values to unpack bbox` | Bbox 是 4 点多边形 | 用 `np.array(bbox)` 提取 min/max |
| `issubclass() arg 1 must be a class` | 使用了 `from __future__ import annotations` | 删除该导入，使用 Python 3.12 原生注解 |
| `Command X not found` | 前端用了 `invoke` 而非 `pyInvoke` | 使用 `tauri-plugin-pytauri-api` 的 `pyInvoke` |
| `pytauri.pyfunc not allowed` | Tauri 权限未配置 | 在 capabilities 中添加 `pytauri:default` |
| `No module named 'paddle_pdf'` | PYTHONPATH 未设置 | pixi.toml 中 tauri tasks 设置 `PYTHONPATH = "../src"` |
| PyO3 不支持 Python 3.14 | 系统 Python 版本过新 | 使用 pixi 的 Python 3.12，设置 `PYO3_PYTHON` |

## 已知限制

- **版面阅读顺序**：复杂多列排版在纯文本导出时可能不完全符合阅读顺序
- **极小或超大字符**：字号缩放下限 1.0pt
- **系统字体依赖**：自动搜索常用中文字体，降级使用内置 `cjk` 字体包
- **模型缓存**：`~/.paddleocr/` 和 `~/.paddlex/`
