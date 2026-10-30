---
name: anime-style-transfer
description: 将照片或现有图片转换为动漫/二次元/卡通风格。提供 14 种内置风格预设（日系赛璐璐、电影级光影、手绘水彩、90 年代 OVA 复古、黑白日漫网点、美式卡通厚线稿、3D 动画电影渲染、扁平二次元、厚涂半写实、手游立绘、水彩插画、像素点阵、墨线线稿、黏土定格），自动构建提示词、控制人脸保真度、批量转换，以及零积分的本地滤镜兜底。此技能应在用户要求把图片转成动漫/二次元/漫画/插画/卡通风格、需要风格预设参考、或需要照片动漫化时使用。触发词：动漫风格、二次元、动漫化、转成动漫、照片变漫画、anime style、convert to anime、cartoonify、漫画风、赛璐璐、像素化、线稿。
agent_created: true
---

# 图片转动漫风格

## 概述

把用户的照片或图片转换成动漫风格图。主路径使用 `ImageGen` 的图生图能力（理解画面内容，能保住人脸与构图）；副路径使用本地 Pillow 滤镜（零积分、纯离线）作为快速预览或无积分兜底。

**核心判断：能否用图生图模型保住「这是同一个人/同一个画面」。** 滤镜做不到这一点，只适合做草稿级效果。

## 何时使用

- 用户给出一张图，要求变成动漫/二次元/漫画/插画/卡通/像素/线稿风格
- 用户问「用哪种风格做头像/封面/插图」
- 用户需要批量把一组图统一风格化
- 用户想要照片动漫化的离线/免费方案

不适用：纯文字生成动漫图（无原图）→ 直接用 `ImageGen` 文生图；视频风格化 → 用 `VideoGen`；修图类需求（去水印、美颜、抠图）→ 用 `buddy-image-processing`。

## 执行流程

### 第 1 步：确认输入与目标风格

确认三件事，缺失项做合理假设而非追问：

1. **原图** — 用户给的路径、URL 或上传的附件
2. **目标风格** — 从 `references/style-guide.md` 的 14 种预设中选，或按用户描述匹配
3. **保真度** — 默认 `medium`；人像且用户强调「要像本人」时用 `high`；Q 版/夸张化用 `low`

风格选型不确定时，先读 `references/style-guide.md` 的「按场景选风格」表。

### 第 2 步：预处理原图（可选但推荐）

原图比例与目标尺寸不一致会导致裁切或拉伸。用脚本统一：

```bash
PY="C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
$PY <SKILL_DIR>/scripts/prepare_image.py --input "原图路径" --out-dir "输出目录"
```

脚本会修正 EXIF 旋转、压平透明背景、按目标比例裁切并输出 JSON 报告（含最终尺寸）。
已知尺寸直接用 `--size 1024x1536` 等，不要手写路径猜测。

支持的输出尺寸：`1024x1024`、`1024x1536`、`1536x1024`。

#### 输入是截图时（抖音/小红书/视频帧）

截图常带 UI 装饰与烧录文字，**必须先裁干净再转换**，否则模型会把它们一起画进动漫图。

需要清除的三类杂质：
1. 左右两侧的 UI 栏（点赞/评论/分享/头像）
2. 顶部叠加的评论文字条
3. 底部烧录的黄色视频文案

用像素统计定位边界，不要凭肉眼猜：

```bash
$PY -c "
from PIL import Image
im = Image.open(r'<截图路径>').convert('RGB')
px = im.load()
def sharp(x):
    t=n=0
    for y in range(200,1700,37):
        a,b = px[x,y], px[x+1,y]
        t += abs(a[0]-b[0])+abs(a[1]-b[1])+abs(a[2]-b[2]); n+=1
    return t/max(1,n)
for x in list(range(240,300,6)):  print('L',x, round(sharp(x),1))
for x in list(range(1330,1400,6)): print('R',x, round(sharp(x),1))
"
```

- **竖直边界**：相邻列梯度出现突变峰处即内容边缘（截图左右两侧是纯色/模糊底，梯度接近 0）
- **顶部白字**：统计每行近白像素（r,g,b 均 > 235）数量
- **底部黄字**：统计每行满足 r>190 且 g>170 且 b<120 的像素数量

裁切时上边界略低于白字末行、下边界略高于黄字首行，留 5-10px 余量。
裁完再跑 `prepare_image.py` 归一到目标尺寸。

### 第 3 步：构建提示词

```bash
$PY <SKILL_DIR>/scripts/build_prompt.py --preset japanese-tv-cel \
  --subject "a young woman with short black hair wearing a red hoodie, standing under cherry blossom trees" \
  --fidelity medium
```

输出 JSON，含 `prompt`、`input_fidelity`、`recommended_size`、`quality`。

要点：

- `ImageGen` **没有独立的 negative_prompt 参数**，否定词由脚本内联进 prompt
- 主体描述用**英文**写，风格迁移结果最稳定
- 需要时加 `--artist` 启用可选艺术家风格引用
- 需要时加 `--extra "自定义要求"`

### 第 4 步：调用 ImageGen

用 `ImageGen` 工具（若未加载，先用工具检索取得 schema）：

```python
ImageGen(
    prompt="<build_prompt.py 输出的 prompt>",
    image1="<预处理后的图片路径>",
    size="1024x1536",
    quality="high",
    input_fidelity="medium",
    output_dir="<输出目录>",
)
```

参数要点：

| 参数 | 用法 |
|---|---|
| `image1` | 待转换的原图（必填，否则变成文生图） |
| `image2` / `image3` | 可选风格参考图 / 构图参考图 |
| `input_fidelity` | `high` 严格保留人脸与构图，`medium` 默认，`low` 大幅重构 |
| `size` | 与预处理输出一致 |
| `quality` | 成品交付用 `high` |
| `output_dir` | 显式指定，便于用户找文件 |

**两个实测细节**：

1. **输出文件名由 prompt 截断生成**（形如 `Convert_the_image_into_Japanes_2026-10-27T08-27-30.png`），
   又长又不好认。生成后用 `scripts/finalize_output.py` 重命名为可读名称再交付。
2. **右下角会有平台水印**（如「AI生成 WORKBUDDY」）。这是平台统一添加的 AI 生成内容标识，
   保留即可；交付时向用户说明水印来历，若用户需要无水印素材请引导其使用平台提供的官方渠道。

**成本提示**：`ImageGen` 每次调用约消耗 5-10 积分。批量转换前先告知用户总消耗量，并建议先出一张样片确认风格再批量。

### 第 5 步：重命名与交付

ImageGen 生成的文件名由 prompt 截断而来，先重命名再交付：

```bash
$PY <SKILL_DIR>/scripts/finalize_output.py --input-dir "<输出目录>" --source "<原图路径>" --label "赛璐璐"
```

然后调用 `present_files` 展示结果文件，并在回复中给出完整路径、所用风格与保真度参数。

**交付格式**：`ImageGen` 输出的 PNG 约 2.4 MB（1024×1536 RGB），体积偏大。
转成 JPEG（quality=95, subsampling=0）后约 0.7 MB，视觉上无损，交付用 JPEG 更合适：

```bash
$PY -c "
from PIL import Image
Image.open(r'<结果图.png>').convert('RGB').save(r'<结果图.jpg>','JPEG',quality=95,subsampling=0,optimize=True)
"
```

## 离线滤镜兜底

无积分、需要立即出结果，或用户只想看大致效果时使用：

```bash
$PY <SKILL_DIR>/scripts/offline_cartoon.py --input "原图.jpg" --output "输出.png" --mode cel
```

模式：`cartoon`（色块+轮廓线）、`cel`（赛璐璐分层）、`manga`（灰度墨线）。

**必须向用户说明局限**：滤镜不理解画面内容，人物不会像原图，细节会糊，只适合草稿级效果。若用户要的是「照片里这个人变成动漫角色」，仍需走 `ImageGen` 路径。

## 关键规则

1. **图生图优先** — 涉及人脸、构图还原时必须用 `ImageGen`，不要用滤镜糊弄
2. **主体描述用英文** — 中文描述会削弱风格迁移的稳定性
3. **否定词内联** — `ImageGen` 无 `negative_prompt` 参数
4. **告知积分消耗** — 调用前告知用户约 5-10 积分/张
5. **批量前先出样片** — 避免一批图风格跑偏
6. **批量用同一 prompt** — 只换 `image1`，保证风格一致
7. **不承诺滤镜效果** — 滤镜结果必须标注为预览级
8. **修复人脸** — 若结果不像本人，提高 `input_fidelity` 到 `high` 并补足发型发色脸型描述后重试

## 风格与提示词细节

完整的 14 种风格列表、场景选型表、提示词构造公式、双图参考用法、批量转换、后期处理衔接、问题排查表，见 `references/style-guide.md`。

## 资源

```
scripts/
  build_prompt.py     预设库查询 + 提示词构建（JSON 输出）
  prepare_image.py    EXIF 修正、比例裁切、尺寸归一
  offline_cartoon.py  零积分本地滤镜（cartoon / cel / manga）
  finalize_output.py  重命名 ImageGen 输出为可读文件名
assets/
  style-presets.json  14 种风格预设库、负面词表、尺寸与保真度规则
references/
  style-guide.md      风格选型、提示词公式、进阶用法、排查表
```

依赖：Python 3.9+ 与 Pillow（已安装于托管 venv `C:/Users/Administrator/.workbuddy/binaries/python/envs/default`）。
