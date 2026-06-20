# PaddlePDF

> **中文** | [English](README_en.md)

基于 PaddleOCR 的 PDF 文字识别工具，支持 **CLI 命令行** 和 **GUI 图形界面** 两种使用方式。

## 功能

- **GPU/CPU 双模式**：自动检测 NVIDIA GPU，支持 CUDA 加速
- **7 种语言模型**：中、英、日、韩、俄等，支持 PP-OCRv4 模型
- **可搜索 PDF**：精确字形宽度测算 + 基线垂直居中对齐，透明文字层（Render Mode 3）与底图文字贴合
- **纯文本输出**：保存 OCR 结果为文本文件（支持带置信度标注）
- **任务队列**：后台顺序执行多个 OCR 任务，支持排队、取消、逐个隔离模型
- **GUI 图形界面**：拖拽文件、实时进度、模型管理、GPU 状态检测

> **⚠️ 关于可搜索 PDF 质量的说明**
>
> 可搜索文本层的定位精度与以下因素密切相关：
> - **排版复杂度**：排版越简单（单栏、无图文混排），效果越好
> - **源文件清晰度**：扫描件/照片质量越高，OCR 识别越准，文字层贴合度越高
> - **模型大小**：大体积模型（如 `ch_server_v2`）精度显著优于轻量模型
>
> 如果源文件质量一般、使用较小的模型、或没有 CUDA 加速，体验会打较大折扣。**不能期望有开箱即用的准确度**，建议根据实际需求选择合适的模型和 DPI 设置。

## 安装

需要 [pixi](https://pixi.sh) 包管理器和 [pnpm](https://pnpm.io)。

```bash
# 1. 安装 Python 后端及基础依赖 (自动由 pixi 管理)
pixi install

# 2. 安装前端 Node.js 依赖
pixi run frontend-install
```

## CLI 使用

```bash
# CPU 模式
pixi run run -- -i "book.pdf"

# GPU 模式（要求本地已配置 CUDA 与 cuDNN）
pixi run run-gpu -- -i "book.pdf"

# 高精度模型 + GPU
pixi run run-gpu -- -gpu -model=ch_plus -i "book.pdf"

# 只处理前 5 页
pixi run run -- -i "book.pdf" --max-pages 5

# 查看所有模型
pixi run run -- --list-models
```

### 命令行参数

| 参数              | 说明                                      | 默认                    |
| --------------- | --------------------------------------- | --------------------- |
| `-i, --input`   | **必填**，输入 PDF                           | —                     |
| `-gpu`          | 启用 GPU 加速                               | 关闭                    |
| `-model <名称>`   | OCR 模型 (ch/ch_plus/ch_server_v2/en/...) | ch                    |
| `-o <目录>`       | 输出目录                                    | `<文件名>_ocr_output/`   |
| `--max-pages N` | 最多处理页数                                  | 全部                    |
| `--dpi N`       | 渲染分辨率                                   | 300                   |
| `--conf`        | 文本输出含置信度                                | 关闭                    |
| `--list-models` | 列出所有模型                                  | —                     |
| `-v`            | 详细输出                                    | 关闭                    |

### 输出

| 文件              | 说明              |
| --------------- | --------------- |
| `<文件名>_可搜索.pdf` | 带文字层 PDF，可搜索/复制 |
| `<文件名>_文字.txt`  | 纯文本，默认不含置信度     |

## GUI 使用

### 开发模式（热重载）

在开发环境下，前端和后端服务需在两个终端窗口分别启动：

```bash
# 终端 1：启动 Python FastAPI 后端服务
pixi run backend-dev

# 终端 2：启动前端 GUI
pixi run tauri-dev
```

### 生产打包

```bash
# 1. 编译 Python 后端为独立可执行文件
pixi run build-backend

# 2. 调用 Rust tauri build 构建 NSIS 安装包
pixi run tauri-build
```

### GUI 功能

- 📄 **拖拽上传**：直接拖入 PDF 文件，支持批量排队处理
- 🔄 **实时进度**：逐页显示 OCR 处理进度，支持取消运行中/等待中的任务
- 🧠 **模型管理**：查看/下载/切换 7 种 OCR 模型
- 💻 **GPU 状态**：自动检测 CUDA 环境，显示 GPU 可用性
- 🌙 **深色模式**：支持明暗主题切换，设置自动保存
- 📊 **结果展示**：页数、行数、置信度、耗时统计
- 📂 **快捷操作**：一键打开输出文件/文件夹

## GPU 环境要求

若需要 GPU 加速，用户需要在本地电脑上安装以下组件：

| 组件           | 说明                  |
| ------------ | ------------------- |
| NVIDIA GPU   | RTX 3060+ (6GB+) 推荐 |
| CUDA Toolkit | 12.x 或 11.x         |
| cuDNN        | 需下载对应版本的 cuDNN，并将其 DLL 放入 CUDA Toolkit 的 `bin` 文件夹下或加入系统 PATH 中 |

```bash
pixi run check-gpu  # 验证 GPU 环境
```

## 项目结构

```
paddle_pdf/
├── src/paddle_pdf/           # Python 后端（MVC 架构）
├── src/paddle_pdf/app/       #   应用入口
│   ├── cli_app.py            #     CLI 启动入口
│   └── http_server.py        #     FastAPI Web 服务端入口
├── src/paddle_pdf/controller/#   控制器层（协议适配）
│   └── cli_controller.py     #     argparse CLI 参数解析器
├── src/paddle_pdf/core/      #   核心业务逻辑（无 UI 依赖）
│   ├── ocr_engine.py         #     PaddleOCR 引擎封装与模型选择
│   ├── pdf_pipeline.py       #     PDF 处理管线（图片渲染、隐式 PDF 生成）
│   ├── models.py             #     模型注册表
│   └── gpu_utils.py          #     CUDA 检测与环境变量设置
├── src/paddle_pdf/service/   #   服务层（编排核心逻辑）
│   ├── ocr_service.py        #     OCR 任务编排
│   ├── task_queue.py         #     后台异步任务队列
│   ├── model_service.py      #     模型文件下载与管理
│   └── system_service.py     #     GPU 状态诊断
├── src-frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/            #     GUI 视图模块
│   │   ├── stores/           #     Pinia 状态管理
│   │   └── composables/      #     useIpc.ts (通过 HTTP/SSE 轮询和订阅事件)
│   └── src-tauri/            #     Tauri Rust 进程壳
│       ├── src/main.rs       #       主入口（拉起 Python 后端 Sidecar 并读取空闲端口）
│       └── tauri.conf.json   #       Tauri 配置（设置打包资源拷贝路径）
├── doc/                      # 项目文档
├── pixi.toml                 # Pixi Python + Node 依赖环境配置
└── README.md
```

## 技术栈

| 层级       | 技术                                                |
| -------- | ------------------------------------------------- |
| 桌面壳      | [Tauri 2.x](https://tauri.app) (Rust)             |
| 通信机制    | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn (HTTP / SSE 订阅) |
| 前端框架     | [Vue 3](https://vuejs.org) + TypeScript            |
| UI 组件    | [Naive UI](https://www.naiveui.com)                |
| 构建工具     | [Vite](https://vitejs.dev) + [pnpm](https://pnpm.io) |
| CSS      | [UnoCSS](https://unocss.dev)                       |
| 状态管理     | [Pinia](https://pinia.vuejs.org)                   |
| OCR 引擎   | [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 3.4.1 |
| PDF 处理   | [PyMuPDF](https://github.com/pymupdf/PyMuPDF)      |
| 包管理      | [pixi](https://pixi.sh) (Python) + pnpm (Node)     |

## 文档

- [用户使用指南](doc/user-guide.md) ([English](doc/user-guide_en.md)) — 详细用法、示例、故障排除
- [开发者文档](doc/developer.md) ([English](doc/developer_en.md)) — 项目架构、API 差异、踩坑记录

## 许可证

MIT License
