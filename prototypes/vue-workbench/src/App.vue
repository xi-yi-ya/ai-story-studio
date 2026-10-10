<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import {
  PanelLeft,
  LayoutGrid,
  UsersRound,
  Mountain,
  Clapperboard,
  ListTodo,
  Settings2,
  ChevronDown,
  Sparkles,
  Plus,
  Search,
  Cloud as CloudCheck,
  ArrowUpRight,
  FolderOpen,
  MoreHorizontal,
  Film,
  History,
  Check,
  ImagePlus,
  Download,
  Pencil,
  X,
  Pause,
  Play,
  RotateCcw,
  CircleCheck,
  Clock3,
  ZoomIn,
  ZoomOut,
  Link2,
  ExternalLink,
} from "lucide-vue-next";
import { useStudio } from "./stores/studio";
import type {
  Asset,
  GenerationInput,
  Page,
  Shot,
  Suggestion,
  Version,
} from "./types";
import AssetCard from "./components/AssetCard.vue";
import ShotCard from "./components/ShotCard.vue";
import MediaThumb from "./components/MediaThumb.vue";
import StudioDialog from "./components/StudioDialog.vue";
import AssistantPanel from "./components/AssistantPanel.vue";
import TimelinePanel from "./components/TimelinePanel.vue";
import VideoPreview from "./components/VideoPreview.vue";

const store = useStudio();
const nav = [
  { page: "projects", title: "项目", icon: LayoutGrid },
  { page: "characters", title: "角色资产", icon: UsersRound },
  { page: "scenes", title: "场景资产", icon: Mountain },
  { page: "shots", title: "分镜工作区", icon: Clapperboard },
  { page: "tasks", title: "任务与历史", icon: ListTodo },
] as const;
const titles: Record<Page, string> = {
  projects: "你的创作空间",
  characters: "角色资产",
  scenes: "场景资产",
  shots: "分镜工作区",
  tasks: "任务与历史",
  settings: "工作台设置",
};
const subtitles: Record<Page, string> = {
  projects: "每一个故事，都值得被认真记录。",
  characters: "让故事里的每个人，有自己的模样。",
  scenes: "为你的故事，搭建一个可以回到的世界。",
  shots: "把想象连成镜头，让故事慢慢发生。",
  tasks: "每一次尝试，都留在它所属的故事里。",
  settings: "按照你的习惯，安排创作空间。",
};
const search = ref("");
const assets = computed(() =>
  store.project.assets.filter(
    (a) =>
      a.kind === store.page &&
      `${a.name} ${a.description}`.includes(search.value),
  ),
);
const shots = computed(() =>
  store.project.shots.filter((s) =>
    `${s.name} ${s.description}`.includes(search.value),
  ),
);
const taskFilter = ref("all");
const tasks = computed(() =>
  [...store.project.tasks]
    .reverse()
    .filter((t) => taskFilter.value === "all" || t.status === taskFilter.value),
);
const modal = ref<
  "edit" | "generate" | "link" | "history" | "preview" | "project" | null
>(null);
const targetId = ref("");
const target = computed(
  () =>
    store.project.assets.find((a) => a.id === targetId.value) ||
    store.project.shots.find((s) => s.id === targetId.value),
);
const edit = ref({
  name: "",
  description: "",
  duration: 5,
  kind: "characters" as Asset["kind"],
});
const gen = ref<GenerationInput>({
  targetId: "",
  kind: "image",
  prompt: "",
  ratio: "16:9",
  resolution: "1 MP",
  duration: 5,
  lora: true,
  upscale: 2,
});
const workflow = ref("Qwen Image 2.1");
const suggestion = ref<Suggestion | null>(null);
const selectedLinks = ref<string[]>([]);
const preview = ref<Version | null>(null);
const zoom = ref(1);
const projectName = ref("");
const storyEditing = ref(false);
const contentArea = ref<HTMLElement>();
const compact = ref(false);
const statusNames: Record<string, string> = {
  ready: "待制作",
  queued: "等待中",
  running: "生成中",
  done: "已完成",
  cancelled: "已取消",
  failed: "失败",
};

function navigate(page: Page) {
  store.page = page;
  search.value = "";
  if (contentArea.value) contentArea.value.scrollTop = 0;
}
function openEdit(id?: string) {
  targetId.value = id || "";
  const item = target.value;
  edit.value = {
    name: item?.name || "",
    description: item?.description || "",
    duration: item && "duration" in item ? item.duration : 5,
    kind: store.page === "scenes" ? "scenes" : "characters",
  };
  modal.value = "edit";
}
function saveEdit() {
  if (!edit.value.name.trim()) return;
  const item = target.value;
  if (item) {
    item.name = edit.value.name.trim();
    item.description = edit.value.description;
    if ("duration" in item) item.duration = edit.value.duration;
  } else
    store.addAsset(
      edit.value.kind,
      edit.value.name.trim(),
      edit.value.description,
    );
  modal.value = null;
  store.notify("资料已保存到原型项目");
}
function openGenerate(
  id: string,
  kind: "image" | "video" = "image",
  s?: Suggestion,
) {
  targetId.value = id;
  if (!target.value) {
    store.notify("此建议的目标已移除，请重新讨论");
    return;
  }
  const item = target.value;
  suggestion.value = s || null;
  const last = item.versions.find((v) => v.kind === kind);
  gen.value = {
    targetId: id,
    kind,
    prompt: s?.prompt || last?.prompt || item.description,
    ratio: "16:9",
    resolution: "1 MP",
    duration: "duration" in item ? item.duration : 5,
    lora: true,
    upscale: 2,
  };
  workflow.value = kind === "image" ? "Qwen Image 2.1" : "H3 图生视频";
  modal.value = "generate";
}
function confirmGeneration() {
  if (!gen.value.prompt.trim()) return;
  if (store.queueGeneration(gen.value)) {
    if (suggestion.value) store.reviewSuggestion(suggestion.value, true);
    modal.value = null;
  }
}
function openLink(id: string) {
  targetId.value = id;
  const item = target.value;
  selectedLinks.value = item && "assetIds" in item ? [...item.assetIds] : [];
  modal.value = "link";
}
function saveLinks() {
  const item = target.value;
  if (item && "assetIds" in item) item.assetIds = [...selectedLinks.value];
  modal.value = null;
  store.notify("素材关联已更新");
}
function openHistory(id: string) {
  targetId.value = id;
  modal.value = "history";
}
function openPreview(v: Version) {
  preview.value = v;
  zoom.value = 1;
  modal.value = "preview";
}
function previewAsset(id: string) {
  const a = store.project.assets.find((a) => a.id === id);
  const v = a?.versions.find((v) => v.id === a.current);
  if (v) openPreview(v);
  else store.notify("这个素材还没有图片");
}
async function locate(id: string) {
  store.select(id);
  const s = store.project.shots.find((s) => s.id === id);
  if (s) s.collapsed = false;
  search.value = "";
  await nextTick();
  document
    .getElementById(`shot-${id}`)
    ?.scrollIntoView({ block: "start", behavior: "smooth" });
}
function addShot() {
  const id = store.newShot();
  locate(id);
}
function allCollapsed(value: boolean) {
  store.project.shots.forEach((s) => (s.collapsed = value));
}
function review(s: Suggestion) {
  openGenerate(s.targetId, "image", s);
}
function persist() {
  store.save();
  store.notify(store.persistenceError || "已保存到此浏览器的原型存档");
}
onMounted(() => {
  if (window.innerWidth < 1100) store.assistantOpen = false;
});
</script>
<template>
  <div class="studio-shell" :class="{ compact }">
    <header class="topbar">
      <button
        class="brand"
        @click="navigate('projects')"
        aria-label="XY Studio 项目"
      >
        <img src="/media/xy-logo.jpg" alt="XY" /><strong
          >XY Studio</strong
        ></button
      ><span class="top-divider" /><button
        class="project-switch"
        @click="navigate('projects')"
      >
        {{ store.project.name }}<ChevronDown :size="14" /></button
      ><button class="save-status" @click="persist">
        <CloudCheck :size="14" />{{
          store.persistenceError ? "保存失败" : "已保存"
        }}<span>本地原型</span>
      </button>
      <div class="top-spacer" />
      <span class="prototype-badge">Vue 界面原型</span
      ><button
        class="btn assistant-toggle"
        aria-label="AI 助手"
        :class="{ active: store.assistantOpen }"
        @click="store.assistantOpen = !store.assistantOpen"
      >
        <Sparkles :size="16" /><span>AI 助手</span>
      </button>
    </header>
    <div class="shell-body">
      <nav class="sidebar" aria-label="主导航">
        <div class="sidebar-label">工作空间</div>
        <button
          v-for="item in nav"
          :key="item.page"
          class="nav-item"
          :class="{ active: store.page === item.page }"
          :aria-label="item.title"
          :title="item.title"
          :aria-current="store.page === item.page ? 'page' : undefined"
          @click="navigate(item.page)"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.6" /><span>{{
            item.title
          }}</span
          ><span
            v-if="item.page === 'tasks' && store.pendingTasks"
            class="nav-count"
            >{{ store.pendingTasks }}</span
          >
        </button>
        <div class="sidebar-project">
          <div><span class="project-dot" /><span>当前项目</span></div>
          <strong>{{ store.project.name }}</strong>
          <p>
            {{ store.project.shots.length }} 个镜头 ·
            {{ store.totalDuration }} 秒
          </p>
        </div>
        <div class="sidebar-bottom">
          <button
            class="nav-item"
            :class="{ active: store.page === 'settings' }"
            aria-label="设置"
            title="设置"
            @click="navigate('settings')"
          >
            <Settings2 :size="18" :stroke-width="1.6" /><span>设置</span>
          </button>
          <div class="workspace-signature">
            <span class="tiny-logo">XY</span
            ><span>让故事，发生。<small>Workbench / Prototype 01</small></span>
          </div>
        </div>
      </nav>
      <main class="main-workspace">
        <div ref="contentArea" class="workspace-scroll">
          <div class="workspace-content">
            <header class="page-heading">
              <div>
                <div class="breadcrumb">
                  {{ store.project.name }}<span>/</span>{{ titles[store.page] }}
                </div>
                <h1>{{ titles[store.page] }}</h1>
                <p>{{ subtitles[store.page] }}</p>
              </div>
              <div class="page-heading-actions">
                <template v-if="store.page === 'shots'"
                  ><button
                    class="btn"
                    @click="
                      allCollapsed(
                        !store.project.shots.every((s) => s.collapsed),
                      )
                    "
                  >
                    <PanelLeft :size="14" />{{
                      store.project.shots.every((s) => s.collapsed)
                        ? "展开全部"
                        : "折叠全部"
                    }}</button
                  ><button class="btn btn-primary" @click="addShot">
                    <Plus :size="16" />添加镜头
                  </button></template
                ><button
                  v-else-if="
                    store.page === 'characters' || store.page === 'scenes'
                  "
                  class="btn btn-primary"
                  @click="openEdit()"
                >
                  <Plus :size="16" />{{
                    store.page === "characters" ? "创建角色" : "创建场景"
                  }}</button
                ><button
                  v-else-if="store.page === 'projects'"
                  class="btn btn-primary"
                  @click="
                    projectName = '';
                    modal = 'project';
                  "
                >
                  <Plus :size="16" />新建项目</button
                ><button
                  v-else-if="store.page === 'tasks'"
                  class="btn"
                  @click="store.toggleQueue"
                >
                  <Play v-if="store.paused" :size="15" /><Pause
                    v-else
                    :size="15"
                  />{{ store.paused ? "继续模拟队列" : "暂停模拟队列" }}
                </button>
              </div>
            </header>
            <div v-if="store.persistenceError" class="error-banner">
              {{ store.persistenceError }}
            </div>
            <template v-if="store.page === 'shots'">
              <section class="story-card surface">
                <div class="flex items-center justify-between mb-2">
                  <h2>故事描述</h2>
                  <button
                    class="icon-btn"
                    :aria-label="storyEditing ? '保存故事描述' : '编辑故事描述'"
                    @click="storyEditing = !storyEditing"
                  >
                    <Check v-if="storyEditing" :size="15" /><Pencil
                      v-else
                      :size="15"
                    />
                  </button>
                </div>
                <textarea
                  v-if="storyEditing"
                  v-model="store.project.story"
                  aria-label="故事描述"
                  rows="3"
                />
                <p v-else>
                  {{
                    store.project.story || "写下一段故事，从一句话开始也可以。"
                  }}
                </p>
                <footer>
                  <span class="story-tag"><Film :size="12" />短故事</span
                  ><span>{{ store.project.shots.length }} 个镜头</span
                  ><span>{{ store.totalDuration }} 秒</span
                  ><span class="story-caption">素材 → 分镜图 → 视频</span>
                </footer>
              </section>
              <div class="section-toolbar">
                <div class="flex items-center gap-2">
                  <h2>镜头列表</h2>
                  <span class="number-badge">{{
                    store.project.shots.length
                  }}</span>
                </div>
                <label class="search-field"
                  ><Search :size="14" /><input
                    v-model="search"
                    aria-label="搜索镜头"
                    placeholder="搜索镜头…"
                /></label>
              </div>
              <div class="shot-list">
                <ShotCard
                  v-for="shot in shots"
                  :key="shot.id"
                  :shot="shot"
                  :index="
                    store.project.shots.findIndex((s) => s.id === shot.id)
                  "
                  @edit="openEdit"
                  @generate="openGenerate"
                  @link="openLink"
                  @preview="openPreview"
                />
                <div v-if="!shots.length" class="empty-state surface">
                  <Clapperboard :size="35" :stroke-width="1.2" />
                  <h3>{{ search ? "没有找到这个镜头" : "你的第一个镜头" }}</h3>
                  <p>
                    {{
                      search
                        ? "试试镜头名称或描述中的其他词。"
                        : "把故事拆成一个画面，再让角色走进来。"
                    }}
                  </p>
                  <button
                    class="btn btn-primary"
                    @click="search ? (search = '') : addShot()"
                  >
                    {{ search ? "清除搜索" : "添加镜头" }}
                  </button>
                </div>
                <button
                  v-if="shots.length"
                  class="add-shot-row"
                  @click="addShot"
                >
                  <Plus :size="17" />添加下一个镜头
                </button>
              </div>
            </template>
            <template
              v-else-if="store.page === 'characters' || store.page === 'scenes'"
            >
              <div class="section-toolbar asset-toolbar">
                <span class="muted"
                  >{{ assets.length }} 个{{
                    store.page === "characters" ? "角色" : "场景"
                  }}<span class="toolbar-hint"
                    >右键查看更多操作 · 双击图片放大</span
                  ></span
                ><label class="search-field"
                  ><Search :size="14" /><input
                    v-model="search"
                    aria-label="搜索素材"
                    placeholder="搜索名称或描述…"
                /></label>
              </div>
              <div class="asset-grid">
                <AssetCard
                  v-for="asset in assets"
                  :key="asset.id"
                  :asset="asset"
                  @edit="openEdit"
                  @generate="openGenerate"
                  @history="openHistory"
                  @preview="previewAsset"
                /><button
                  v-if="!search"
                  class="create-asset"
                  @click="openEdit()"
                >
                  <span><Plus :size="25" :stroke-width="1.3" /></span
                  ><strong>{{
                    store.page === "characters"
                      ? "创建一个角色"
                      : "创建一个场景"
                  }}</strong
                  ><small>给故事一个新的可能</small>
                </button>
              </div>
              <div v-if="!assets.length && search" class="empty-state">
                <Search :size="30" />
                <h3>没有找到这个素材</h3>
                <button class="btn" @click="search = ''">清除搜索</button>
              </div>
            </template>
            <template v-else-if="store.page === 'projects'">
              <div class="project-grid">
                <button
                  v-for="p in store.projects"
                  :key="p.id"
                  class="project-card surface"
                  :class="{ selected: p.id === store.activeId }"
                  @click="store.openProject(p.id)"
                >
                  <MediaThumb
                    :media="p.shots[0]?.versions[0]?.media"
                    :label="p.name"
                  />
                  <div>
                    <span class="project-card-caption">{{
                      p.id === store.activeId ? "当前项目" : "本地原型项目"
                    }}</span>
                    <h3>{{ p.name }}</h3>
                    <p>{{ p.story || "新的故事，等待开始。" }}</p>
                    <footer>
                      {{ p.shots.length }} 个镜头<span>{{ p.updated }}</span
                      ><ArrowUpRight :size="16" />
                    </footer>
                  </div>
                </button>
              </div>
              <section class="welcome-note">
                <span class="welcome-icon"
                  ><Sparkles :size="23" :stroke-width="1.4"
                /></span>
                <div>
                  <h3>从一个想法，到一个完整的故事。</h3>
                  <p>
                    建立角色与场景，逐镜头探索画面，把每次尝试留在原来的位置。
                  </p>
                  <div class="flex gap-3 mt-4">
                    <button class="btn" @click="store.exportMock">
                      <Download :size="15" />导出原型存档</button
                    ><button class="btn" @click="store.createStressProject">
                      <ListTodo :size="15" />打开 120 镜头示例
                    </button>
                  </div>
                </div>
              </section>
            </template>
            <template v-else-if="store.page === 'tasks'">
              <div class="task-stats">
                <div class="surface">
                  <Clock3 :size="19" /><span
                    >进行中<strong>{{ store.pendingTasks }}</strong></span
                  >
                </div>
                <div class="surface">
                  <CircleCheck :size="19" /><span
                    >已完成<strong>{{
                      store.project.tasks.filter((t) => t.status === "done")
                        .length
                    }}</strong></span
                  >
                </div>
                <div class="surface">
                  <History :size="19" /><span
                    >全部记录<strong>{{
                      store.project.tasks.length
                    }}</strong></span
                  >
                </div>
              </div>
              <div class="task-table surface">
                <div class="task-table-head">
                  <h2>生成记录<span class="mock-tag ml-2">本地模拟</span></h2>
                  <select v-model="taskFilter" aria-label="任务状态筛选">
                    <option value="all">全部状态</option>
                    <option value="running">生成中</option>
                    <option value="queued">等待中</option>
                    <option value="done">已完成</option>
                    <option value="cancelled">已取消</option>
                    <option value="failed">失败</option>
                  </select>
                </div>
                <div v-if="!tasks.length" class="empty-state">
                  <ListTodo :size="30" />
                  <h3>这里还没有任务</h3>
                  <p>模拟生成的进度与结果会显示在这里。</p>
                </div>
                <div v-for="t in tasks" :key="t.id" class="task-row">
                  <span class="task-type"
                    ><Clapperboard
                      v-if="t.kind === 'video'"
                      :size="19" /><ImagePlus v-else :size="19"
                  /></span>
                  <div class="task-main">
                    <strong>{{ t.targetName }}</strong>
                    <p>
                      {{ t.kind === "video" ? "H3 · 视频" : "Qwen Image · 图片"
                      }}<span> {{ t.time }}</span>
                    </p>
                    <span v-if="t.error" class="danger text-xs">{{
                      t.error
                    }}</span>
                  </div>
                  <div class="task-row-status">
                    <span
                      class="status-pill"
                      :class="{
                        completed: t.status === 'done',
                        error: t.status === 'failed',
                      }"
                      >{{ statusNames[t.status] }}
                      {{ t.status === "running" ? `${t.progress}%` : "" }}</span
                    >
                    <div
                      v-if="['running', 'queued'].includes(t.status)"
                      class="mini-progress"
                    >
                      <i :style="{ width: `${t.progress}%` }" />
                    </div>
                  </div>
                  <button
                    v-if="['running', 'queued'].includes(t.status)"
                    class="btn"
                    @click="store.cancelTask(t.id)"
                  >
                    取消</button
                  ><button
                    v-else-if="t.status === 'done'"
                    class="btn"
                    @click="
                      targetId = t.targetId;
                      openHistory(t.targetId);
                    "
                  >
                    查看结果</button
                  ><button v-else class="btn" @click="store.retryTask(t.id)">
                    <RotateCcw :size="13" />重试
                  </button>
                </div>
              </div>
            </template>
            <template v-else-if="store.page === 'settings'">
              <div class="settings-card surface">
                <h2>创作工作台</h2>
                <p>这些设置仅改变本地原型的显示与模拟行为。</p>
                <label class="setting-row"
                  ><div>
                    <strong>紧凑视图</strong
                    ><span>稍微缩小卡片间距，容纳更多镜头。</span>
                  </div>
                  <input
                    v-model="compact"
                    type="checkbox"
                    role="switch"
                    aria-label="紧凑视图" /></label
                ><label class="setting-row"
                  ><div>
                    <strong>默认助手模型</strong
                    ><span>原型展示模型选择，不查询真实账户。</span>
                  </div>
                  <select v-model="store.model">
                    <option>DeepSeek Flash</option>
                    <option>DeepSeek Pro</option>
                  </select></label
                ><label class="setting-row"
                  ><div>
                    <strong>AI 助手侧栏</strong
                    ><span>收起时保留对话和选中素材上下文。</span>
                  </div>
                  <input
                    v-model="store.assistantOpen"
                    type="checkbox"
                    role="switch"
                    aria-label="显示 AI 助手"
                /></label>
                <div class="setting-row">
                  <div>
                    <strong>本地原型存档</strong
                    ><span>自动保存至此浏览器，与 Qt 项目完全独立。</span>
                  </div>
                  <button class="btn" @click="store.exportMock">
                    <Download :size="14" />导出存档
                  </button>
                </div>
              </div>
              <div class="prototype-note">
                <span class="mock-tag">PROTOTYPE 01</span>
                <h3>这是视觉与交互验证版本</h3>
                <p>
                  所有生成、联网和 AI 回复都在本地模拟。此版本没有连接
                  Python、ComfyUI、DeepSeek 或桌面壳。
                </p>
              </div>
            </template>
          </div>
        </div>
        <TimelinePanel v-if="store.page === 'shots'" @locate="locate" />
        <footer v-else class="workspace-bottom">
          <span>XY Studio · 界面原型</span
          ><span>{{ store.project.name }} / 浏览器本地存档</span>
        </footer>
      </main>
      <button
        v-if="store.assistantOpen"
        class="assistant-backdrop"
        aria-label="关闭 AI 抽屉"
        @click="store.assistantOpen = false"
      /><AssistantPanel v-if="store.assistantOpen" @review="review" /><button
        v-else
        class="assistant-rail"
        aria-label="展开 AI 助手"
        @click="store.assistantOpen = true"
      >
        <Sparkles :size="18" /><span>AI 助手</span>
      </button>
    </div>
    <div v-if="store.toast" class="toast" role="status">
      <CircleCheck :size="17" />{{ store.toast }}
    </div>

    <StudioDialog
      :open="modal === 'edit'"
      @update:open="(v) => !v && (modal = null)"
      :title="
        target
          ? '编辑资料'
          : edit.kind === 'characters'
            ? '创建角色'
            : '创建场景'
      "
      ><form @submit.prevent="saveEdit" class="form-content">
        <label
          >名称<input
            v-model="edit.name"
            required
            maxlength="100"
            placeholder="为它取一个名字" /></label
        ><label
          >描述<textarea
            v-model="edit.description"
            rows="5"
            placeholder="外观、性格，或环境的光线与氛围…"
          /></label
        ><label v-if="target && 'duration' in target"
          >镜头时长（秒）<input
            v-model.number="edit.duration"
            type="number"
            min="1"
            max="30"
            required
        /></label>
        <footer class="dialog-actions">
          <button type="button" class="btn" @click="modal = null">取消</button
          ><button class="btn btn-primary">
            {{ target ? "保存修改" : "确认创建" }}
          </button>
        </footer>
      </form></StudioDialog
    >
    <StudioDialog
      :open="modal === 'project'"
      @update:open="(v) => !v && (modal = null)"
      title="一个新的故事"
      ><form
        class="form-content"
        @submit.prevent="
          store.createProject(projectName.trim());
          modal = null;
        "
      >
        <label
          >项目名称<input
            v-model="projectName"
            required
            maxlength="100"
            placeholder="你的故事叫什么名字？"
        /></label>
        <footer class="dialog-actions">
          <button type="button" class="btn" @click="modal = null">取消</button
          ><button class="btn btn-primary">创建原型项目</button>
        </footer>
      </form></StudioDialog
    >
    <StudioDialog
      :open="modal === 'generate'"
      @update:open="(v) => !v && (modal = null)"
      :title="
        gen.kind === 'image' ? '生成图片 · 参数审阅' : '生成视频 · 参数审阅'
      "
      :description="`结果将保存至「${target?.name || '原条目'}」，保留已有版本。此操作仅为本地模拟。`"
      ><form class="form-content" @submit.prevent="confirmGeneration">
        <div class="target-pill">
          <Link2 :size="14" />{{ target?.name }}<span>原条目 · 新版本</span>
        </div>
        <label
          >工作流<select v-model="workflow" aria-label="生成工作流">
            <template v-if="gen.kind === 'image'"
              ><option>Qwen Image 2.1</option>
              <option>Krea 角色四视图</option>
              <option>高清放大 RFMSR</option></template
            ><template v-else
              ><option>H3 图生视频</option>
              <option>H3 参考生视频</option></template
            >
          </select></label
        ><label
          >提示词<textarea
            v-model="gen.prompt"
            rows="4"
            required
            aria-label="生成提示词"
          />
        </label>
        <div class="form-row">
          <label
            >画面比例<select v-model="gen.ratio">
              <option>16:9</option>
              <option>9:16</option>
              <option>1:1</option>
              <option>4:3</option>
              <option>2.35:1</option>
            </select></label
          ><label
            >分辨率<select v-model="gen.resolution">
              <option>0.5 MP</option>
              <option>1 MP</option>
              <option>2 MP</option>
            </select></label
          >
        </div>
        <label v-if="gen.kind === 'video'"
          >视频时长 · {{ gen.duration }} 秒<input
            v-model.number="gen.duration"
            type="range"
            min="2"
            max="15"
            step="1" /></label
        ><label v-if="gen.kind === 'video'" class="checkbox-label"
          ><input v-model="gen.lora" type="checkbox" />启用电影质感 LoRA</label
        ><label v-if="workflow === '高清放大 RFMSR'"
          >放大倍数 · {{ gen.upscale }}×<input
            v-model.number="gen.upscale"
            type="range"
            min="1"
            max="8"
            step=".5"
        /></label>
        <p class="form-note">
          模拟任务只展示进度，并从示例素材创建新版本，不运行图像或视频模型。
        </p>
        <footer class="dialog-actions">
          <button type="button" class="btn" @click="modal = null">取消</button
          ><button class="btn btn-primary">
            <Sparkles :size="15" />确认并模拟生成
          </button>
        </footer>
      </form></StudioDialog
    >
    <StudioDialog
      :open="modal === 'link'"
      @update:open="(v) => !v && (modal = null)"
      title="关联角色与场景"
      ><div class="link-picker">
        <label
          v-for="asset in store.project.assets"
          :key="asset.id"
          class="link-option"
          :class="{ selected: selectedLinks.includes(asset.id) }"
          ><MediaThumb
            :media="asset.versions.find((v) => v.id === asset.current)?.media"
            :label="asset.name" />
          <div>
            <strong>{{ asset.name }}</strong
            ><small>{{ asset.kind === "characters" ? "角色" : "场景" }}</small>
          </div>
          <input v-model="selectedLinks" type="checkbox" :value="asset.id"
        /></label>
        <p v-if="!store.project.assets.length" class="empty-state">
          先创建一个角色或场景，再与镜头建立关联。
        </p>
      </div>
      <footer class="dialog-actions">
        <button class="btn" @click="modal = null">取消</button
        ><button class="btn btn-primary" @click="saveLinks">保存关联</button>
      </footer></StudioDialog
    >
    <StudioDialog
      :open="modal === 'history'"
      @update:open="(v) => !v && (modal = null)"
      :title="`${target?.name || '素材'} · 生成历史`"
      wide
      ><div v-if="!target?.versions.length" class="empty-state">
        <History :size="32" />
        <h3>每次尝试，都会留在这里</h3>
        <p>生成新版本后，可随时比较和重新选定。</p>
      </div>
      <div class="version-grid">
        <article v-for="v in target?.versions" :key="v.id" class="version-card">
          <button @dblclick="openPreview(v)">
            <MediaThumb :media="v.media" :label="v.label" />
          </button>
          <div class="flex items-center justify-between mt-3">
            <h3>{{ v.label }}</h3>
            <span class="muted text-xs">{{
              v.kind === "image" ? "图片" : "视频"
            }}</span>
          </div>
          <p>{{ v.time }}</p>
          <p class="version-prompt">{{ v.prompt }}</p>
          <button
            class="btn"
            :class="{
              active:
                target &&
                ('current' in target
                  ? target.current === v.id
                  : target.imageVersion === v.id ||
                    target.videoVersion === v.id),
            }"
            @click="store.useVersion(targetId, v.id)"
          >
            设为当前版本
          </button>
        </article>
      </div></StudioDialog
    >
    <StudioDialog
      :open="modal === 'preview'"
      @update:open="(v) => !v && (modal = null)"
      title="素材预览"
      description="示例画面来自你提供的参考设计图；视频为静帧模拟预览。"
      wide
      ><div class="preview-toolbar">
        <button
          class="icon-btn"
          aria-label="缩小图片"
          @click="zoom = Math.max(0.5, zoom - 0.25)"
        >
          <ZoomOut :size="18" /></button
        ><span>{{ Math.round(zoom * 100) }}%</span
        ><button
          class="icon-btn"
          aria-label="放大图片"
          @click="zoom = Math.min(3, zoom + 0.25)"
        >
          <ZoomIn :size="18" /></button
        ><button class="btn" @click="zoom = 1">适应窗口</button>
      </div>
      <div class="large-preview">
        <VideoPreview
          v-if="preview?.kind === 'video'"
          :media="preview.media"
          :duration="5"
          label="模拟视频预览"
        /><MediaThumb
          v-else
          :media="preview?.media"
          label="大图预览"
          :style="{ width: `${zoom * 100}%`, minWidth: `${zoom * 100}%` }"
        /></div
    ></StudioDialog>
  </div>
</template>
