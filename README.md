# PaddlePDF

基于 PaddleOCR 的 PDF 文字识别命令行工具，支持 GPU/CPU 加速。

## 功能

- **GPU/CPU 双模式**：自动检测 NVIDIA GPU，支持 CUDA 加速
- **7 种语言模型**：中、英、日、韩、俄等，支持 PP-OCRv5 最新模型
- **可搜索 PDF**：基于精确字形宽度测算与基线垂直居中对齐算法，透明文字层（Render Mode 3）与底图文字贴合，支持划词、搜索与复制
- **输出纯文本文件**：保存 OCR 结果为 Markdown/Txt 文本（支持带置信度标注）

## 安装

需要 [pixi](https://pixi.sh) 包管理器。

```bash
pixi install
```

## 快速使用

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

Windows 批处理脚本：

```bash
run_ocr.bat -i "book.pdf"
run_ocr.bat -gpu -i "book.pdf"
```

## 命令行参数

| 参数              | 说明                                      | 默认                  |
| --------------- | --------------------------------------- | ------------------- |
| `-i, --input`   | **必填**，输入 PDF                           | —                   |
| `-gpu`          | 启用 GPU 加速                               | 关闭                  |
| `-model <名称>`   | OCR 模型 (ch/ch_plus/ch_server_v2/en/...) | ch                  |
| `-o <目录>`       | 输出目录                                    | `<文件名>_ocr_output/` |
| `--max-pages N` | 最多处理页数                                  | 全部                  |
| `--dpi N`       | 渲染分辨率                                   | 300                 |
| `--conf`        | 文本输出含置信度                                | 关闭                  |
| `--list-models` | 列出所有模型                                  | —                   |
| `-v`            | 详细输出                                    | 关闭                  |

## 输出

| 文件              | 说明              |
| --------------- | --------------- |
| `<文件名>_可搜索.pdf` | 带文字层 PDF，可搜索/复制 |
| `<文件名>_文字.txt`  | 纯文本，默认不含置信度     |

## GPU 环境要求

| 组件           | 说明                  |
| ------------ | ------------------- |
| NVIDIA GPU   | RTX 3060+ (6GB+) 推荐 |
| CUDA Toolkit | 11.x 或 12.x         |
| cuDNN        | 需单独安装               |

```bash
pixi run check-gpu  # 验证 GPU 环境
```

## 文档

- [用户使用指南](doc/user-guide.md) — 详细用法、示例、故障排除
- [开发者文档](doc/developer.md) — 项目架构、API 差异、踩坑记录

## 项目结构

```
paddle_pdf/
├── main.py              # CLI 入口
├── ocr_engine.py        # OCR 引擎
├── pdf_pipeline.py      # PDF 处理流程
├── models.py            # 模型注册表
├── check_gpu_env.py     # GPU 诊断
├── pixi.toml            # 依赖配置
├── run_ocr.bat          # Windows 启动脚本
├── doc/
│   ├── developer.md     # 开发者文档
│   └── user-guide.md    # 用户指南
└── README.md
```

## 技术栈

- [PaddlePaddle](https://github.com/PaddlePaddle/Paddle) 3.3.0
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 3.4.1
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF 渲染
- [pixi](https://pixi.sh) — 包管理

## 许可证

MIT License
