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

需要 [pixi](https://pixi.sh) 包管理器。

```bash
# 基础安装（CLI）
pixi install

# 安装 GUI 依赖（含 pytauri）
pixi install --environment gui
```

## CLI 使用

```bash
# CPU 模式
pixi run run -- -i "book.pdf"

# GPU 模式
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

```bash
# 开发模式（热重载）
pixi run tauri-dev

# 构建生产包
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

| 组件           | 说明                  |
| ------------ | ------------------- |
| NVIDIA GPU   | RTX 3060+ (6GB+) 推荐 |
| CUDA Toolkit | 11.x 或 12.x         |
| cuDNN        | 需单独安装               |

```bash
pixi run check-gpu  # 验证 GPU 环境
```

## 项目结构

```
paddle_pdf/
├── src/paddle_pdf/           # Python 后端（MVC 架构）
│   ├── core/                 #   核心业务逻辑（无 UI 依赖）
│   │   ├── ocr_engine.py     #     PaddleOCR 引擎封装
│   │   ├── pdf_pipeline.py   #     PDF 处理管线
│   │   ├── models.py         #     模型注册表
│   │   └── gpu_utils.py      #     CUDA 检测
│   ├── service/              #   服务层（编排核心逻辑）
│   │   ├── ocr_service.py    #     OCR 任务编排
│   │   ├── task_queue.py     #     后台任务队列
│   │   ├── model_service.py  #     模型管理
│   │   └── system_service.py #     系统诊断
│   ├── controller/           #   控制器层（协议适配）
│   │   ├── cli_controller.py #     argparse CLI
│   │   └── ipc_controller.py #     pytauri IPC 端点
│   ├── common/               #   公共定义
│   │   ├── schemas.py        #     数据结构
│   │   ├── events.py         #     事件常量
│   │   └── config.py         #     全局配置
│   └── app/                  #   应用入口
│       ├── cli_app.py        #     CLI 入口
│       └── pytauri_app.py    #     GUI 入口
├── src-frontend/             # Vue 3 前端
│   ├── src/
│   │   ├── views/            #     页面组件
│   │   ├── components/       #     可复用组件
│   │   ├── stores/           #     Pinia 状态管理
│   │   ├── composables/      #     组合式函数
│   │   └── types/            #     TypeScript 类型
│   └── src-tauri/            #     Tauri Rust 壳
├── doc/                      # 文档
├── pixi.toml                 # Python 依赖配置
└── README.md
```

## 技术栈

| 层级       | 技术                                                |
| -------- | ------------------------------------------------- |
| 桌面壳      | [Tauri 2.x](https://tauri.app) (Rust)             |
| Python 桥 | [pytauri](https://github.com/pytauri/pytauri)      |
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
