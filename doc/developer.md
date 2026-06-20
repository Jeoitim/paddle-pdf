# 开发者文档

## 项目概述

基于 PaddleOCR 的 PDF 文字识别工具，支持 **CLI 命令行** 和 **GUI 图形界面** 两种使用方式。GUI 采用 FastAPI + Uvicorn 作为 Python 后端 Sidecar，前端通过 Tauri + Vue 3 渲染，并通过 HTTP 协议与 SSE 事件流实现前后端松耦合通信。

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 桌面壳 | Tauri | 2.11 |
| 通信机制 | FastAPI + Uvicorn (HTTP / SSE) | 0.115+ / 0.34+ |
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
│   │   ├── task_queue.py     #     后台任务队列 (ThreadPoolExecutor)
│   │   ├── model_service.py  #     模型管理
│   │   └── system_service.py #     系统诊断
│   ├── controller/           #   Controller — 协议适配层
│   │   └── cli_controller.py #     argparse CLI 参数解析
│   ├── common/               #   公共定义
│   │   ├── schemas.py        #     dataclass 数据结构
│   │   ├── events.py         #     通信事件常量
│   │   └── config.py         #     全局配置
│   └── app/                  #   应用入口
│       ├── cli_app.py        #     CLI 入口
│       └── http_server.py    #     FastAPI Web 服务端入口 (Sidecar)
│
├── src-frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/            #     HomeView, TaskDetailView, SettingsView
│   │   ├── components/       #     FileDropZone, TaskCard, TaskProgress,
│   │   │                     #     ModelSelector, GpuStatus, TextPanel
│   │   ├── stores/           #     Pinia: task, settings, app
│   │   ├── composables/      #     useIpc (HTTP/SSE 封装), useTask, useModels
│   │   └── types/            #     TypeScript 类型定义
│   └── src-tauri/            #     Tauri Rust 壳
│       ├── src/main.rs       #       主入口 (拉起 Sidecar，读取空闲端口)
│       └── tauri.conf.json   #       Tauri 资源拷贝与打包配置
│
├── doc/                      # 文档
├── pixi.toml                 # Python + Node 依赖管理
└── README.md
```

## FastAPI Sidecar 架构与前后端通信

### 通信流程

```
┌─────────────────┐       HTTP 请求 (GET / POST)       ┌──────────────────┐
│  Vue Frontend   │ ─────────────────────────────────→ │  FastAPI Backend │
│  (useIpc.ts)    │                                    │  (Uvicorn)       │
│                 │ ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  └──────────────────┘
└─────────────────┘      Server-Sent Events (SSE)               │
                                                                │
                                                         路由与后台任务
                                                                ↓
                                                       ┌──────────────┐
                                                       │  Service 层   │
                                                       │  Core 层      │
                                                       └──────────────┘
```

### 关键实现细节

1. **子进程拉起与生命周期管理** (`src-frontend/src-tauri/src/main.rs`)：
   - Tauri 主进程在初始化阶段 (`setup` hook) 启动 Python 后端进程。
   - 开发模式下，优先检测并拉起 `backend/dist/paddle_pdf_backend/paddle_pdf_backend.exe`。若不存在，则使用 pixi 环境中的 `python.exe` 启动 `-m paddle_pdf.app.http_server` 并设置 `PYTHONPATH`。
   - 生产打包模式下，Tauri 从资源目录中找到并启动打包好的 `paddle_pdf_backend.exe`。
2. **动态端口握手与服务发现**：
   - Python 后端绑定 `127.0.0.1` 上的一个随机空闲端口（通过 `socket.bind(("", 0))` 获取），并在启动时向 stdout 打印一行 `PADDLE_PDF_PORT=<port>`。
   - Rust 主进程拦截该 stdout 管道，利用 `BufReader` 行读取解析出该动态端口，并将其缓存在 Tauri 的 `BackendState` 中。
   - 前端在首次请求前，通过 Tauri Native Command `get_backend_port` 获得缓存端口，随后建立与其的本地 HTTP 和 SSE 通信。
3. **孤儿进程自动清理** (PID 监视器)：
   - 为了防止 Tauri 前端崩溃或被强制结束时，后台 Python 进程残留在系统中，Rust 端在拉起子进程时会注入环境变量 `PADDLE_PDF_PARENT_PID=<parent_pid>`。
   - Python 后端 (`http_server.py`) 启动一个守护线程检测父进程的存活状态（在 Windows 下利用 `OpenProcess` 与 `GetExitCodeProcess` 检查 `STILL_ACTIVE`，Unix 下通过 `os.kill(pid, 0)` 检查）。一旦发现父进程退出，立即调用 `os._exit(0)` 进行自我清理。

### API 请求与 SSE 事件总览

1. **API 调用** (`useIpc.ts`)：
   - 前端通过 `ipcInvoke(command, args)` 将方法名映射至 HTTP endpoint（例如 `process_task` 映射为 `POST /process_task`），通过 `fetch` 发送标准 HTTP 请求并解析返回的 JSON。
2. **事件推送**：
   - 服务端配置了 `/events` 路由，前端使用 HTML5 `EventSource` 订阅该长连接以接收 SSE 推送。
   - 后台任务产生的各种状态（如进度更新、任务完成、失败、模型下载进度等）通过 Python 的异步事件队列广播至所有 SSE 客户端。

---

## 任务队列架构 (TaskQueue)

### 设计概述

`TaskQueue`（`src/paddle_pdf/service/task_queue.py`）实现了后台任务队列，支持顺序执行多个 OCR 任务：

- **异步提交**：`add_task()` 立即返回，任务在后台线程执行
- **顺序处理**：`max_workers=1`（默认），GPU 显存通常不允许并发加载多个模型
- **任务隔离**：每个任务拥有独立的 `OcrService` 实例，模型状态互不干扰
- **回调机制**：通过 4 种回调（progress/completion/failure/cancel）触发 SSE 事件广播至前端

### 核心类

```
TaskQueue
├── _tasks: dict[str, QueuedTask]    # 所有任务（按 task_id 索引）
├── _queue: list[str]                # 等待执行的 task_id（FIFO）
├── _active: dict[str, OcrService]   # 正在运行的任务
├── _executor: ThreadPoolExecutor    # 后台线程池
└── _lock: threading.Lock            # 线程安全锁
```

### Sidecar 通信事件流

```
Backend TaskQueue                    FastAPI /events (SSE)              Frontend (useTask.ts)
─────────────────                    ─────────────────────              ──────────────────────
progress_callback(task_id, tp)  ──→  SSE [task://progress]        ──→   store.updateProgress
completion_callback(task_id, r) ──→  SSE [task://completed]       ──→   store.completeTask
failure_callback(task_id, err)  ──→  SSE [task://failed]          ──→   store.failTask
cancel_callback(task_id)        ──→  SSE [task://cancelled]       ──→   store.cancelTask
```

### Sidecar HTTP API 路由总览

| 接口 | 方法 | 说明 | 返回 |
|---|---|---|---|
| `/process_task` | `POST` | 提交任务到队列（立即返回） | `SimpleResponse` |
| `/cancel_task` | `POST` | 取消指定任务 | `SimpleResponse` |
| `/queue_status` | `GET` | 获取所有任务状态快照 | `list[TaskStatus]` |
| `/remove_task` | `POST` | 移除已完成/失败/取消的任务 | `SimpleResponse` |
| `/list_models` | `GET` | 获取可用 OCR 模型列表 | `list[ModelInfo]` |
| `/download_model`| `POST` | 触发后台下载模型 | `SimpleResponse` |
| `/check_gpu` | `GET` | 系统 GPU/CUDA 状态诊断 | `GpuInfo` |

### 前端任务 Store

Pinia `task` store 维护任务列表，通过 computed 属性分片：

- `pendingTasks`：status === 'pending'
- `activeTasks`：status ∈ ['extracting', 'ocr_running', 'saving']
- `completedTasks`：status === 'completed'
- `finishedTasks`：status ∈ ['completed', 'failed', 'cancelled']

### 前端事件监听

`useTask` composable 在首次调用时通过 `ipcListen` 注册 SSE 事件监听，通过 `task_id` 路由事件到对应任务：

```typescript
ipcListen<TaskProgress>('task://progress', (progress) => {
  store.updateProgress(progress.task_id, progress)
})
ipcListen<TaskCompletedEvent>('task://completed', (payload) => {
  store.completeTask(payload.task_id, payload)
})
```
```

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
| `partially initialized module 'paddle' has no attribute 'tensor' (circular import)` | 打包后 Python 环境初始化顺序问题导致的循环导入 | 在 PyInstaller 运行时钩子 `rth_paddle.py` 中，在最开始显式导入 `paddle.base` 与 `paddle.tensor` |
| `No module named 'unittest'` (或 `importlib.metadata.PackageNotFoundError`) | 打包为单文件/独立目录后，`.dist-info` 丢失，Paddlex 等检测 cv2 等依赖版本失败 | 在 `rth_paddle.py` 中 monkeypatch `importlib.metadata.version`，检测到若对应包实际可被 import，则返回虚拟版本号（如 opencv 返回 `4.10.0.84`） |
| 打包版 GPU 检测为 False / 找不到 CUDA DLL | 打包未包含体积巨大的 NVIDIA 依赖包；系统无法通过 PATH 找到本地显卡 CUDA 安装 | 确保本地安装了 CUDA Toolkit 12.x 及 cuDNN，并将其 bin/ 目录加入 PATH；打包版会通过 `rth_paddle.py` 扫描注册表/默认路径并调用 `os.add_dll_directory` 动态加载 |
| `No module named 'paddle_pdf'` | PYTHONPATH 未设置 | pixi.toml 中 tauri tasks 设置 `PYTHONPATH = "../src"` 或使用正确的 python 运行命令 |

## 已知限制

- **版面阅读顺序**：复杂多列排版在纯文本导出时可能不完全符合阅读顺序
- **极小或超大字符**：字号缩放下限 1.0pt
- **系统字体依赖**：自动搜索常用中文字体，降级使用内置 `cjk` 字体包
- **模型缓存**：`~/.paddleocr/` 和 `~/.paddlex/`
