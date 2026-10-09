# AI Story Studio — v0.1.0

面向个人短故事创作者的 Windows 原生桌面工作台。PySide6/Qt Widgets 界面，调用本机 ComfyUI；DeepSeek 用于对话、故事组织和生成建议。

## 启动

1. 启动已安装节点和模型的 ComfyUI，默认 `http://127.0.0.1:8188`。
2. 双击 `releases/v0.1.0/AI-Story-Studio/AI-Story-Studio.exe`。
3. 新建空项目文件夹，或打开已有 `project.json`。项目可放在任意可写目录。
4. 在设置中填 DeepSeek API Key（可以暂时不填，手工生成正常使用）。密钥存入 Windows 凭据管理器，不写入项目或 Git。

源码运行：Python 3.12，`pip install -r requirements.txt`，`python main.py`。本机已创建 `.venv`，可运行 `run.ps1`。开发测试：`python -m pytest tests --basetemp local-data/pytest-local`（仅用此专用临时目录）。

## 使用

- 顶部角色、场景、分镜板。角色/场景可新建、改描述、导入图、右击发送给 AI、查看版本或删除；有分镜引用时先解除关联。
- 分镜板顶部保存故事，下面每行一个分镜，按描述和素材、图片、视频排列。
- 生成参数窗口选择工作流、比例、MP、H3 秒数、种子、步数及 LoRA。参考图按列表顺序使用，可从已有项目素材选择或导入。
- 生成图片和视频均加入串行队列。任务记录可取消或恢复查询。已完成的输出复制到项目，使用相对路径；输出版本可重新设为当前版本。
- 素材发生修改时，引用它的分镜标记为待检查，保留已有结果。
- 右侧 AI 对话可隐藏。AI 可建议新增/修改条目、故事或生成；每项改动可审阅，生成仍经过同一个参数窗口。文本、条目描述、相对文件名会发送给 DeepSeek；图片像素不会上传给 DeepSeek。

## 工作流范围

| 功能 | 工作流与控制 |
|---|---|
| Qwen Image 2.1 文生图 / 编辑 | BF16 原配置；可显式选本机 INT8；MP、比例；最多 16 张编辑参考 |
| Krea2 文生图 | 9 种风格 LoRA 分别启停，启用时自动附对应触发词 |
| Krea2 角色四视图 | QuadView LoRA 启停，参考图和输出尺寸 |
| H3 图生视频 | 10Eros beta4 INT8，电影 LoRA 启停和强度，比例、MP、秒数 |
| H3 参考生视频 | 同底模，1–9 张有序参考图片，电影 LoRA 启停和强度 |
| RFMSR | 1–8 倍（0.1 步进）、采样步数、预期输出尺寸 |

另提供 H3 文生、首尾帧模式，由同一 H3 节点建立；具体实测范围见 `docs/VALIDATION.md`。

**按用户要求排除独立“电影感10Eros+Beta3”工作流；不接入断开的 Turbo LoRA；忽略之后新增的工作流。** 普通 H3 的电影质感 LoRA 保留。不开启的 LoRA 从 API 图中移除，不依赖编辑器 mode 标记。

## 第一版边界

- DeepSeek 已接代码和有界工具调用，真实密钥和在线端到端验证待用户补充。模型名在设置中可改，默认 deepseek-flash。
- H3 使用 24fps，按原表达式向上对齐为 `17k+5` 帧。输入 2 秒得到 56 帧，约 2.33 秒；界面显示实际时长。默认低规格方便首测，高规格没有可运行保证。
- Qwen 编辑将第一张参考图居中裁剪到所选输出尺寸；其他参考保持各自比例。普通图片保存为 8-bit PNG，未保留原 Qwen SaveImageAdvanced 的 16-bit 导出。
- H3 参考模式本版只接图片；视频参考、音频参考、时间线剪辑、成片拼接、自动连续性审片尚未实现。
- 版本记录保存生成意图、参数、引用素材快照；没有完整的素材分支合并或镜头首尾帧自动比较。
- 程序不安装/下载模型，不改写用户 ComfyUI 工作流，不打包模型。需要同样的节点和模型文件名。`docs/workflow-sources.json` 记录六份批准来源的文件哈希。
- 任务提交超时标记未知，不自动重交；有 prompt_id 可以恢复查询。ComfyUI 重启会丢失其内存队列/历史，未知任务需人工核对。任务日志可在项目 `jobs` 文件夹查看。
- 不要同时用两个程序实例编辑同一项目；项目 JSON 是单用户存储。

## 目录与迭代

`studio/` 应用和后端；`tests/` 离线测试；`scripts/` 构建与显式人工启动的本机生成测试；`docs/` 需求、来源及验证。

源码通过 Git 提交和 `v0.1.0` 标签留档。`releases/v0.1.0/` 保存可运行包；后续版本使用新目录，保留旧包。`.venv`、生成素材、日志、项目、发布二进制不提交 Git。项目外部图片在导入时复制，原文件不修改。

## 实现依据

原生独立实现，没有复制 EasyAI 等项目代码。DeepSeek 接口依据官方 [Tool Calls 文档](https://api-docs.deepseek.com/guides/tool_calls/)，发布依据 [PyInstaller 文档](https://pyinstaller.org/en/stable/usage.html)。ComfyUI 适配以本机 `/object_info` 和批准工作流为准。
