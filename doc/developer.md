# 开发者文档

## 项目概述

基于 PaddleOCR 的 PDF 文字识别 CLI 工具，支持 GPU/CPU 双模式，输出可搜索 PDF + 纯文本。

## 技术栈

| 组件 | 版本 |
|------|------|
| Python | 3.12 |
| PaddlePaddle | 3.3.0 (GPU) |
| PaddleOCR | 3.4.1 |
| PyMuPDF (fitz) | 1.27+ |
| 包管理 | pixi 0.68+ |

## 项目结构

```
paddle_pdf/
├── main.py              # CLI 入口 (argparse)
├── ocr_engine.py        # OCR 引擎 (GPU/CPU 初始化、PaddleOCR 封装)
├── pdf_pipeline.py      # PDF 处理流程 (提取页面、OCR、生成输出)
├── models.py            # 模型注册表 (7 种语言)
├── check_gpu_env.py     # GPU 环境诊断
├── pixi.toml            # pixi 环境配置
├── pixi.lock            # 锁定依赖版本
├── pyproject.toml       # 项目元数据
├── run_ocr.bat          # Windows 快捷启动
├── doc/
│   ├── developer.md     # 本文档
│   └── user-guide.md    # 用户使用指南
└── README.md
```

## 环境搭建

```bash
# 安装所有依赖
pixi install

# 验证
pixi run python -c "import paddle; print(paddle.__version__)"
pixi run check-gpu
```

## PaddleOCR 3.x API 关键差异

### 构造函数参数

| 旧参数 (2.x) | 新参数 (3.x) | 说明 |
|---|---|---|
| `use_gpu=True/False` | **已移除** | 改用 `paddle.device.set_device("gpu:0")` |
| `show_log=False` | **已移除** | 不再支持 |
| `use_angle_cls=True` | `use_textline_orientation=True` | 参数改名 |

```python
# 正确的 PaddleOCR 3.x 初始化
import paddle

if use_gpu:
    paddle.device.set_device("gpu:0")
else:
    paddle.device.set_device("cpu")

ocr = PaddleOCR(
    use_textline_orientation=True,
    lang="ch",
    text_det_limit_side_len=960,
    text_det_limit_type="max",
)

# 调用时不传 cls 参数
raw_result = ocr.ocr(image_path)
```

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

PaddleOCR 3.x 的 `rec_polys` 是 4 点多边形，不能直接 unpack：

```python
import numpy as np

pts = np.array(bbox)         # shape (4, 2)
x0, y0 = pts.min(axis=0)
x1, y1 = pts.max(axis=0)

# 注意：不能用 if not bbox (NumPy 布尔判断会报错)
# 改用 if bbox is None
```

### 置信度计算

`rec_scores` 是 0-1 小数，百分比转换注意不要重复：

```python
# ocr_engine.py: 单页平均置信度
avg_conf = (total_conf / num_lines * 100)  # 已是百分比

# pdf_pipeline.py: 全文统计时
total_conf_sum += conf * num_lines / 100.0  # conf 已是 %，需转回 0-1
```

## GPU 初始化模式

```python
import paddle

# 1. 检测 CUDA 环境 (DLL 路径)
# 2. 设置设备
if use_gpu:
    try:
        paddle.device.set_device("gpu:0")
    except Exception:
        use_gpu = False
        paddle.device.set_device("cpu")

# 3. 验证 GPU 可用
def check_gpu():
    if paddle.device.cuda.device_count() > 0:
        x = paddle.to_tensor([1.0])
        _ = x * 2
        return True
    return False
```

## PDF 可搜索层写入

使用 PyMuPDF (fitz) 将 OCR 文本以完全透明的模式（`render_mode=3`）精准叠加到原始 PDF 的图像上方，确保用户可以在保留原始图像的外观下进行文字复制、搜索和高亮。

### 核心设计原则

1.  **字体预注册与嵌入**：
    为避免重复加载字体导致 PDF 冗余以及浏览器渲染乱码，在每页处理开始前，自动检测系统 CJK 字体（如 `simsun.ttc`），若不存在则使用 PyMuPDF 内置的 `cjk` 字体包，并通过 `page.insert_font` 进行一次性注册。
2.  **字号匹配算法（宽度优先，高度截断）**：
    由于 OCR 识别的 Bbox 宽高比可能与 PDF 标准字体的宽高比存在偏差，如果直接限制字号或采用 `insert_textbox`，会导致文字换行或超出边界。我们先以参考字号 `ref_fs = 10` 测量字体的物理渲染宽度，再按比例缩放，并保证不超过高度的 95%：
    $$\text{fontsize\_by\_width} = \text{ref\_fs} \times \frac{\text{target\_width}}{\text{measured\_width}}$$
    $$\text{fontsize} = \max(\min(\text{fontsize\_by\_width}, \text{target\_height} \times 0.95), 1.0)$$
3.  **基线垂直居中对齐公式**：
    PyMuPDF 的 `insert_text` 是基于文字基线（Baseline）渲染的。当字号因为宽度限制而缩小后，为了避免文字悬挂在框顶部或沉到底部，我们计算垂直居中偏移量，并根据字体的 `ascender` 属性确定最终的基线 $Y$ 坐标：
    $$\text{baseline\_y} = \text{ry0} + \frac{\text{target\_height} - \text{fontsize}}{2} + \text{ascender} \times \text{fontsize}$$

### 核心实现代码

```python
# 1. 加载并注册字体
if font_path:
    try:
        font = fitz.Font(fontname="simsun", fontfile=font_path)
        font_name = "simsun"
    except Exception:
        font = fitz.Font("cjk")
        font_name = "cjk"
else:
    font = fitz.Font("cjk")
    font_name = "cjk"

try:
    if font_path and font_name == "simsun":
        page.insert_font(fontname=font_name, fontfile=font_path)
    else:
        page.insert_font(fontname=font_name, fontbuffer=font.buffer)
except Exception:
    # 自动降级处理
    ...

ascender = getattr(font, "ascender", 0.8)

# 2. 逐行精确放置文字
for line_data in lines:
    text = line_data.get("text", "").strip()
    bbox = line_data.get("bbox")
    
    # 坐标转换与缩放 (rx0, ry0, rx1, ry1)
    ...
    target_width = rx1 - rx0
    target_height = ry1 - ry0
    
    # 动态匹配字号
    measured_width = font.text_length(text, fontsize=10.0)
    fs_by_width = 10.0 * target_width / measured_width if measured_width > 0 else target_height
    fontsize = max(min(fs_by_width, target_height * 0.95), 1.0)
    
    # 计算居中基线
    baseline_y = ry0 + (target_height - fontsize) / 2 + ascender * fontsize
    point = fitz.Point(rx0, baseline_y)
    
    # 写入透明文字层 (render_mode=3)
    page.insert_text(point, text, fontsize=fontsize, fontname=font_name, render_mode=3)
```

## 常见错误速查

| 错误现象 / 错误信息 | 原因 | 修复方法 |
|---|---|---|
| `Unknown argument: use_gpu` | PaddleOCR 3.x 已删除该参数 | 改用 `paddle.device.set_device()` 设置全局设备。 |
| `Unknown argument: use_angle_cls` | 参数被重命名 | 改为 `use_textline_orientation=True`。 |
| `not enough values to unpack bbox` | Bbox 格式不一致 (3.x 返回多边形) | 用 `np.array(bbox)` 提取 `min(axis=0)` 和 `max(axis=0)`。 |
| `ValueError: if bbox` | NumPy 数组在布尔判断时抛出 | 将判断改为 `if bbox is None:`。 |
| 置信度转换结果极其夸张 (例如 8329%) | 重复百分比转换 | `total_conf_sum += conf * num_lines / 100.0`（注意 OCR 返回值本身是否带 %）。 |
| **Edge/Chrome 等浏览器中中文显示为 ??? 乱码** | PDF 未正确嵌入 Unicode 映射表或缺少字体文件 | 使用 `page.insert_font()` 显式传入物理字体文件/字节流 buffer。 |
| **划词复制/高亮位置严重偏移、换行重叠** | 使用 `insert_textbox` 会因边框舍入导致自动折行 | 改用 `insert_text` 单行写入，并使用宽度匹配字号与基线居中公式。 |

## 已知限制

- **版面阅读顺序**：复杂的多列、插图排版在纯文本导出（`.txt`）时，识别顺序可能不完全符合人类阅读习惯（受 PaddleOCR 检测框检测顺序影响）。
- **极小或超大字符**：字号缩放有 `1.0` 的下限限制，极小的干扰噪点可能被放大为 1pt 字体写入。
- **系统字体依赖**：在 Windows、macOS 和 Linux 上自动搜索常用中文字体，若完全未检测到，将降级使用 PyMuPDF 的内置 `cjk` 字体包（`Droid Sans Fallback`）。
- **模型管理**：OCR 模型自动缓存于用户家目录的 `~/.paddleocr/` 与 `~/.paddlex/`，如需重置模型可清空该文件夹。
