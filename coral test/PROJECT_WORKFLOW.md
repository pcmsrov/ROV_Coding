# Coral Garden 标准化执行流程文档

## 项目名称
Coral Garden 水下水管结构二维识别 + CAD 三维重建

## 1. 项目目标
- 基于水下正面/背面图像，自动识别水管主体二维外轮廓。
- 自动识别 90° 转角红色正方形标记点并输出二维坐标。
- 通过已知长度完成像素-物理尺寸标定，推算真实尺寸。
- 输出 CAD 可导入数据并完成 30cm 纵深三维重建。
- 使用背面图像完成尺寸与点位复核，形成最终交付模型。

## 2. 输入与输出规范

### 2.1 输入
- 正面图：`coral_front.jpg`
- 背面图：`coral_back.jpg`
- 已知参考长度（实长，cm）：例如 `10.0`
- 已知参考像素长度（可选）：不填则自动使用主体包围盒主边估算

### 2.2 输出（默认目录 `outputs/`）
- `front_annotated.jpg`：正面识别结果图（轮廓 + 红标）
- `back_annotated.jpg`：背面识别结果图（轮廓 + 红标）
- `front_enhanced.jpg`、`back_enhanced.jpg`：预处理增强图
- `front_red_mask.jpg`、`back_red_mask.jpg`：红色分割掩码图
- `front_red_marks.csv`、`back_red_marks.csv`：标记点坐标和面积
- `reconstruction_report.json`：完整识别、标定、校验报告
- `coral_reconstruction.dxf`：CAD 交换文件（轮廓/拉伸线/标记点）

## 3. 环境要求
- Python 3.9+
- 依赖：
  - `opencv-python`
  - `numpy`

安装示例：

```bash
pip install opencv-python numpy
```

## 4. 标准执行流程（SOP）

### 步骤 1：图像采集
- 采集正面、背面各 1 张，镜头尽量垂直结构平面。
- 保持同一拍摄距离、焦段与光照条件。
- 结构纵深按项目设定为 30cm，照片内应包含可用于标定的已知长度区域。

### 步骤 2：图像预处理
程序自动执行：
- 高斯降噪（去除随机噪点）
- LAB + CLAHE（提亮细节、提升对比度）
- 生成增强图与后续分析灰度图

### 步骤 3：水管主体二维轮廓识别
程序自动执行：
- Canny 边缘检测
- 膨胀连接边缘
- 外轮廓提取并按面积筛选主体
- 输出主体轮廓点和包围盒尺寸

### 步骤 4：红色正方形标记点识别
程序自动执行：
- HSV 双区间红色阈值分割（低 hue 与高 hue）
- 开/闭运算降噪
- 四边形拟合与长宽比筛选
- 输出中心点、包围框、面积信息

### 步骤 5：像素尺寸标定换算
程序自动执行：
- `scale_cm_per_px = known_length_cm / known_length_px`
- 将轮廓坐标、标记点坐标同步换算为 cm
- 若未提供 `known_length_px`，自动估算并在报告中记录

### 步骤 6：CAD 三维建模数据导出
程序自动执行：
- 输出正面轮廓（z=0）
- 按 30cm 拉伸到背面轮廓（z=30）
- 输出前后轮廓连接边和红标点（前后各一套）
- 产出 `coral_reconstruction.dxf` 供 CAD 导入

### 步骤 7：数据校验与收尾
程序自动执行：
- 对比正背面包围盒实长宽差异（cm）
- 在 `reconstruction_report.json` 给出一致性建议
- 若差异 > 2cm，建议重拍或重新标定

## 5. 执行命令

## 基础执行（推荐）
```bash
python test2.py --front coral_front.jpg --back coral_back.jpg --known-length-cm 10
```

## 指定已知像素长度（更精准）
```bash
python test2.py --front coral_front.jpg --back coral_back.jpg --known-length-cm 10 --known-length-px 186.5
```

## 修改拉伸深度并显示窗口
```bash
python test2.py --front coral_front.jpg --back coral_back.jpg --known-length-cm 10 --depth-cm 30 --show
```

## 6. 交付物清单（可直接上交）
- 程序文件：`test2.py`
- 标准流程文档：`PROJECT_WORKFLOW.md`
- 输出成果目录：`outputs/`（图像、CSV、JSON、DXF）

## 7. 风险与优化建议
- 若水体浑浊严重或反光强，建议补光并增加偏振处理。
- 红色阈值在不同水域需微调，可在脚本中调整 `red_hsv_ranges`。
- 推荐增加现场标定尺，避免自动估算参考像素带来的系统误差。
- 若需工业级精度，可叠加相机标定（畸变矫正）和多视几何重建。
