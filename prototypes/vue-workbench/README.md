# XY Studio · Vue 前端原型 01

独立的 Vue 3 + TypeScript 创作工作台，使用 Vite、Tailwind CSS、Pinia、Reka UI 和 Lucide。当前阶段只验证视觉、布局和交互，所有业务数据、生成任务和 AI 回复均为本地模拟。

现有 `studio/`、Python 环境、项目数据格式、`main.py` 及 v0.2.0 Windows 发布包保持原状。此目录是单独的前端工程。

## 启动

本机已安装 Node 24.19.0。首次运行：

```powershell
cd D:\Flie\Repository\AI-Story-Studio\prototypes\vue-workbench
npm ci
npm run dev
```

浏览器打开 **http://127.0.0.1:5173/**。仅监听本机，不需要启动 ComfyUI、不需要 API Key。当前已安装依赖，可直接 `npm run dev`。

生产构建与预览：

```powershell
npm run build
npm run preview
```

预览地址 **http://127.0.0.1:4173/**。`dist/` 可交给静态 HTTP 服务运行；不是通过双击 `index.html` 使用的文件协议页面。

保持预览服务运行，在另一终端执行 `node scripts/verify-production.mjs` 可验证生产构建的资源、页面及网络请求，并保存报告。

浏览器端到端测试：

```powershell
npm test
```

测试使用本机 Microsoft Edge 的独立临时浏览器环境，不读取日常浏览器账户或用户配置。测试生成页面截图到 `docs/screenshots/`。首次运行无需下载 Playwright Chromium；若其他电脑没有 Edge，可修改 `playwright.config.ts` 的 channel 并安装相应测试浏览器。

## 可以操作的内容

- 六个入口：项目、角色、场景、分镜、任务、设置。
- 创建空原型项目，打开已有原型项目；自动保存、重开恢复、导出独立原型 JSON。
- 角色/场景共用卡片：选择、编辑、新建、模拟生成、历史版本切换、删除、发送给 AI、右键菜单、大图预览。
- 分镜：新增、编辑名称/描述/时长、删除、关联/解除角色与场景、选择、逐卡片折叠/全部折叠、搜索。
- 图片与视频参数分别审阅。图片比例、分辨率、高清放大倍数；视频时长与电影 LoRA 开关可调整。参数只是模拟设置，不运行真实工作流。
- 每次模拟生成创建一个新版本，始终写回相同目标 ID；分镜历史直接在原卡片展开。取消审阅不执行，已拒绝建议不执行。
- 视频为静帧模拟播放器：播放/暂停、进度滑块、时长显示与放大预览。不是生成好的视频文件。
- 时间轴按镜头顺序展示名称、缩略图和时长；点击展开并定位镜头，同步选中状态与 AI 上下文。
- 助手侧栏展开/收起、用户/AI 分色、长消息展开、定位自己的消息、输入发送、模型与联网模拟开关、工具建议确认/拒绝、参数审阅。
- 模拟串行队列、当前进度、暂停、取消、重试与刷新后显式恢复。
- 120 镜头长文本示例；空项目和无搜索结果状态；窄窗口与助手抽屉；紧凑视图。

## 数据与媒体说明

浏览器存档键为 `xy-studio-vue-prototype-v1`，文件标识为 `xy-vue-mock-1`。它和 Qt 的 `project.json` 是两套独立数据；目前没有原型存档文件导入、Qt 项目导入或磁盘文件夹选择能力。

图片源为本次提供的参考设计图，`MediaThumb.vue` 用 SVG 视窗仅展示其画面区域，原始文件未改写。XY 标识复用现有项目图标。所有资源随原型本地提供，没有外部图片或字体依赖。参考图中的画面分辨率有限，4K 下可能显得柔软；这是示例媒体的限制，不是布局分辨率限制。

模拟生成只从示例画面新增版本。联网开关不执行搜索，模型列表不表示账户实际可用模型。没有读取、存储或调用 DeepSeek Key。浏览器刷新后未完成任务标为待恢复，点击任务页“继续模拟队列”才继续。

## 目录

| 文件/目录 | 作用 |
| --- | --- |
| `src/App.vue` | 工作台框架、六个页面、审阅/资料/历史/预览弹窗 |
| `src/components/` | 素材卡片、分镜卡片、助手、时间轴、模拟播放器与弹窗 |
| `src/stores/studio.ts` | Pinia 共享上下文、原型存档、模拟队列与版本归属 |
| `src/mock.ts`、`src/types.ts` | 示例故事与类型定义，与 Python 格式无耦合 |
| `src/style.css` | Tailwind、视觉规范、响应式布局和缩放适配 |
| `public/media/` | 本地参考图与标识 |
| `tests/` | 浏览器交互和布局验证 |
| `docs/screenshots/` | 真实浏览器截图 |
| `docs/DELIVERY.md` | 验证结果、Qt 覆盖差异、后续接入改造点 |
| `dist/` | `npm run build` 生成的可预览包，Git 忽略 |

构建依据：[Vue 官方快速开始](https://vuejs.org/guide/quick-start.html)、[Tailwind 官方 Vite 接入](https://tailwindcss.com/docs/installation/using-vite)、[Vite 官方指南](https://vite.dev/guide/)。依赖版本通过 `package-lock.json` 固定。
