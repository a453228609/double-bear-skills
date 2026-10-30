# 风格选择与提示词手册

本文件是「动漫风格转换」技能的风格库与提示词构造参考。按需查阅，不必一次读完。

---

## 一、14 个内置风格速查

| id | 中文名 | 一句话特征 | 最适合 | 默认保真度 |
|---|---|---|---|---|
| `japanese-tv-cel` | 日系 TV 赛璐璐 | 平涂色块 + 硬边阴影 + 细线稿 | 人物、校园、日常场景 | medium-high |
| `luminous-cinematic` | 电影级透亮光影 | 体积光、云层、大气透视、逆光 | 风景、天空、城市远景 | medium |
| `ghibli-watercolor` | 手绘水彩动画 | 柔和水彩背景、温暖低饱和 | 乡野、田园、日常叙事 | medium-high |
| `retro-90s-ova` | 90 年代 OVA 复古 | 有限色板、模拟柔化、胶片颗粒 | 怀旧场景、复古氛围 | medium |
| `shonen-manga-bw` | 黑白日漫网点 | 墨线 + 网点纸 + 高对比 | 人物特写、动作场面 | high |
| `american-cartoon-cel` | 美式卡通厚线稿 | 粗黑描边、夸张头身比 | Q 版、宠物、搞笑表情 | low-medium |
| `cgi-animation` | 3D 动画电影渲染 | 次表面散射、柔和全局光 | 人物、拟人化物品 | medium |
| `flat-moe` | 扁平二次元插画 | 干净平涂 + 极简阴影 | 头像、表情包、社媒图 | high |
| `painterly-anime` | 厚涂半写实动漫 | 笔触混色 + 柔和明暗 | 半身像、角色设定稿 | medium-high |
| `game-character-art` | 二次元手游立绘 | 服装细节 + 动态姿态 + 戏剧光效 | 立绘、卡面、宣传图 | medium |
| `watercolor-illustration` | 水彩插画 | 纸纹、晕染、颜料沉淀 | 植物、静物、手账 | medium-high |
| `pixel-art` | 像素点阵 | 有限调色板、可见像素格 | 图标、精灵、头像 | medium |
| `ink-lineart` | 墨线线稿 | 纯黑白线稿、不上色 | 上色底稿、临摹参考 | high |
| `claymation-cute` | 黏土定格 | 手捏纹理、圆润体块 | 摆拍公仔、萌化头像 | low-medium |

---

## 二、按场景选风格

**人像 / 照片转二次元**
- 想要「这就是本人但变成动漫」→ `japanese-tv-cel`（保真度 high）或 `flat-moe`
- 想要高级感立绘 → `game-character-art` 或 `painterly-anime`
- 想要头像直接可用 → `flat-moe`

**风景 / 旅行照**
- `luminous-cinematic`（逆光天空最出彩）
- `ghibli-watercolor`（安静治愈）
- `retro-90s-ova`（怀旧胶片感）

**静物 / 食物 / 植物**
- `watercolor-illustration`（最贴合）
- `ghibli-watercolor`

**梗图 / 表情包**
- `american-cartoon-cel`（夸张化）
- `claymation-cute`（萌化）
- `pixel-art`（像素小人）

**漫画分镜草稿**
- `shonen-manga-bw`
- `ink-lineart`

---

## 三、提示词构造公式

`build_prompt.py` 按以下顺序拼装：

```
1. 风格句   Convert the image into <风格名>: <特征词列表>
2. 主体句   Subject to render: <你描述的画面内容>
3. 保真句   <按保真度选定的保持约束>
4. 质量句   high quality finished illustration, clean coherent linework...
5. 附加句   --extra 传入的自定义要求
6. 否定句   Avoid: <全局负面词> + <风格专属负面词>
```

### 为什么否定词要内联

`ImageGen` 没有独立的 `negative_prompt` 参数，只能把否定词写进 `prompt`。
`build_prompt.py` 默认会自动加上全局负面词；不需要时用 `--no-negative` 关闭。

### 主体描述写法

用英文写主体描述，风格迁移结果最稳定：

- 好：`a young woman with short black hair wearing a red hoodie, standing in front of a cherry blossom tree`
- 差：`一个人`

要素清单：**主体类型 + 发型发色 + 服装及颜色 + 动作姿态 + 关键场景元素**。

### 保真度选择

| 保真度 | 效果 | 何时用 |
|---|---|---|
| `high` | 只换画风，五官/姿势/构图几乎不动 | 人像、需要「认出是同一个人」 |
| `medium` | 守构图，允许重绘细节与光影 | 大多数场景的默认值 |
| `low` | 大幅重构，只保留大致轮廓 | Q 版、夸张化、材质重构 |

---

## 四、进阶用法

### 4.1 双图输入（参考图 + 待转换图）

`ImageGen` 支持 `image1` / `image2` / `image3` 三个输入。

- `image1` = 待转换的原图
- `image2` = 风格参考图（放一张喜欢的动漫截图，让模型模仿它的画风）
- `image3` = 构图参考（可选）

```python
ImageGen(
    prompt="Convert the subject in image1 into the rendering style of image2. ...",
    image1="原图.jpg",
    image2="参考风格.png",
    input_fidelity="high",
    size="1024x1536",
    quality="high",
)
```

### 4.2 保持人脸一致

1. `input_fidelity` 设为 `high`
2. 主体句里写清发型、发色、脸型特征
3. 提示词中加入：`keep the same facial structure and identity, do not change the person's appearance`
4. 如果仍然不像，改用 `--fidelity high` + `--extra "same age, same ethnicity, same facial proportions"`

### 4.3 批量转换

对多张图使用同一风格时，**固定同一套 prompt 与 `input_fidelity`**，只替换 `image1`。
风格词表不变才能保证批量结果风格一致。

批量后统一重命名，把 prompt 截断出来的长文件名换成可读名称：

```bash
$PY <SKILL_DIR>/scripts/finalize_output.py --input-dir "输出目录" --source "原图.jpg" --label "赛璐璐"
```

目录内有多张图时自动追加 `_1`、`_2` 序号。加 `--dry-run` 可先预览重命名结果。

### 4.4 透明背景角色图

1. 用 `ImageGen` 生成主体（`background="transparent"` 或纯色背景）
2. 需要真透明背景时，调用 `buddy-image-processing` 技能的 `matting` 操作
3. 注意：`matting` 只返回透明背景主体，换白色/彩色/其他背景需要额外的合成步骤

---

## 五、后期处理衔接

动漫化之后如果还需要修图，使用 `buddy-image-processing`：

| 需求 | 操作 |
|---|---|
| 提升清晰度、降噪 | `enhance` |
| 去除水印/文字 | `erase` |
| 人像磨皮微调 | `beauty` |
| 抠出透明背景 | `matting` |

调用方式见该技能自带的 `SKILL.md`（脚本路径 `buddy-image-processing/scripts/buddy-image-processing.py`）。

---

## 六、常见问题排查

| 症状 | 原因 | 处理 |
|---|---|---|
| 出来还是照片质感 | 特征词不够强 / 保真度太高 | 提高风格词密度，保真度降到 `medium` 或 `low` |
| 人脸不像本人 | 保真度不够 / 主体描述缺特征 | 保真度调 `high`，补足发型发色脸型描述 |
| 构图被改写 | 保真度过低 | 提高保真度，或加 `keep the same framing and composition` |
| 出现文字/水印 | 模型默认生成文字 | 保留全局否定词（`text`, `watermark`, `signature`） |
| 手指/肢体畸变 | 常见生成缺陷 | 保留 `extra fingers`, `deformed hands`, `mutated anatomy` 否定词 |
| 风格过强认不出原图 | 特征词过激 | 降保真度优先级、减少特征词数量 |
| 背景被抹平 | 提示词未约束背景 | 加 `--extra "keep the original background details"` |
| 输出被裁切 | 源图比例与目标尺寸不一致 | 先跑 `prepare_image.py` 统一比例 |

---

## 七、离线滤镜的定位

`scripts/offline_cartoon.py` 是**纯本地、无需联网、不消耗积分**的滤镜：

| 模式 | 效果 |
|---|---|
| `cartoon` | 色块化 + 深色轮廓线，通用卡通感 |
| `cel` | 明暗分层赛璐璐 + 高饱和 |
| `manga` | 灰度网点 + 墨线，漫画草稿感 |

用途：快速预览、批量粗筛、没有积分时的兜底。
局限：它不理解画面内容，只做像素级处理，人物不像原图、细节会糊。
**要真正「照片里的这个人变成动漫角色」，必须走 `ImageGen` 路线。**
