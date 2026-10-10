<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
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
import GenerationForm from "./components/GenerationForm.vue";
import SettingsPanel from "./components/SettingsPanel.vue";

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
  "edit" | "generate" | "link" | "history" | "preview" | "project" | "review" | "delete" | null
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
const gen = ref<GenerationInput>({mode:'qwen',prompt:'',ratio:'16:9',megapixels:1,seconds:5,seed:'42',steps:0,cinema:false,cinema_strength:.4,quad_lora:true,qwen_int8:false,styles:[],scale:2,references:[]});
const suggestion=ref<Suggestion|null>(null);
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
  completed: "已完成", new:"待执行", submitting:"提交中",downloading:"保存结果",cancel_requested:"取消中",unknown:"状态未知",detached:"已断开",
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
async function saveEdit() {
  if (!edit.value.name.trim() && !target.value) return;
  if(target.value)await store.editAsset(targetId.value,edit.value.name.trim(),edit.value.description);
  else await store.addAsset(edit.value.kind,edit.value.name.trim(),edit.value.description);
  modal.value=null;store.notify('资料已保存');
}
async function openGenerate(id:string,kind:'image'|'video'='image',s?:Suggestion,previous?:GenerationInput){
  targetId.value=id;if(!target.value){store.notify('此操作的目标已移除');return;}
  suggestion.value=s || null;
  gen.value=JSON.parse(JSON.stringify(previous || s?.generation || await store.defaults(id,kind==='video'?'h3_i2v':undefined)));
  modal.value='generate';
}
async function confirmGeneration(){
  if(suggestion.value)await store.reviewSuggestion(suggestion.value,true,gen.value);
  else await store.queueGeneration(targetId.value,gen.value);
  modal.value=null;suggestion.value=null;
}
async function cancelGeneration(){if(suggestion.value)await store.reviewSuggestion(suggestion.value,false);modal.value=null;suggestion.value=null;}
function openLink(id: string) {
  targetId.value = id;
  const item = target.value;
  selectedLinks.value = item && "assetIds" in item ? [...item.assetIds] : [];
  modal.value = "link";
}
async function saveLinks(){await store.link(targetId.value,selectedLinks.value);modal.value=null;store.notify('素材关联已更新');}
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
  if(s)store.fold(id,false);
  search.value = "";
  await nextTick();
  document
    .getElementById(`shot-${id}`)
    ?.scrollIntoView({ block: "start", behavior: "smooth" });
}
async function addShot() {
  const id = await store.newShot();
  locate(id);
}
function allCollapsed(value: boolean) {
  store.project.shots.forEach((s) => (store.fold(s.id,value)));
}
async function review(s:Suggestion){suggestion.value=s;if(s.name==='generate' && s.targetId)await openGenerate(s.targetId,s.generation?.mode.startsWith('h3')?'video':'image',s);else modal.value='review';}
async function persist(){await store.save();store.notify('项目已保存');}
async function toggleStory(){if(storyEditing.value)await store.saveStory(store.project.story);storyEditing.value=!storyEditing.value;}
function confirmDelete(id:string){targetId.value=id;modal.value='delete';}
async function deleteTarget(){await store.remove(targetId.value);modal.value=null;}
const reviewText=computed(()=>JSON.stringify(suggestion.value?.args,null,2));
const pendingRecords=computed(()=>store.project.tasks.filter(t=>t.targetId===targetId.value && t.status!=='completed'));
watch(()=>store.project.id,()=>{modal.value=null;search.value='';});
void store.initialize();
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
      ><button class="save-status" :disabled="!store.hasProject" @click="persist">
        <CloudCheck :size="14" />{{
          store.hasProject ? "保存项目" : "尚未打开"
        }}<span>本地项目</span>
      </button>
      <div class="top-spacer" />
      <span class="prototype-badge">Vue 创作工作台</span
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
          :title="item.title" :disabled="!store.hasProject && item.page!=='projects'"
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
            ><span>让故事，发生。<small>Workbench / v{{store.state?.version}}</small></span>
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
                  />{{ store.paused ? "继续待执行队列" : "暂停待执行队列" }}
                </button>
              </div>
            </header>
            <div v-if="store.connectionError" class="error-banner">{{store.connectionError}}<button class="text-action" @click="store.connectionError=''">已了解</button></div><div v-if="store.state?.error" class="error-banner">{{store.state.error}}<button class="text-action" @click="store.api('error.clear')">已了解</button></div><div v-if="store.persistenceError" class="error-banner">
              {{ store.persistenceError }}
            </div>
            <template v-if="store.page === 'shots'">
              <section class="story-card surface">
                <div class="flex items-center justify-between mb-2">
                  <h2>故事描述</h2>
                  <button
                    class="icon-btn"
                    :aria-label="storyEditing ? '保存故事描述' : '编辑故事描述'"
                    @click="toggleStory"
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
                  @delete="confirmDelete" @edit="openEdit"
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
                  @delete="confirmDelete" @edit="openEdit"
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
  <div class="project-grid"><button v-for="p in store.projects" :key="p.id" class="project-card surface" @click="store.openProject(p.id)"><div class="project-cover"><FolderOpen :size="32" :stroke-width="1.3"/></div><div><span class="project-card-caption">最近打开的项目</span><h3>{{p.name}}</h3><p>{{p.story}}</p><footer>打开项目<ArrowUpRight :size="16"/></footer></div></button></div>
  <section class="welcome-note"><span class="welcome-icon"><Sparkles :size="23"/></span><div><h3>从一个想法，到一个完整的故事。</h3><p>打开已有 project.json，或在新文件夹创建项目。旧项目的素材、ID 和历史会保留。</p><div class="flex gap-3 mt-4"><button class="btn btn-primary" @click="store.openProject()"><FolderOpen :size="15"/>打开项目</button><button v-if="store.hasProject" class="btn" @click="store.folder"><ExternalLink :size="15"/>打开项目文件夹</button></div></div></section>
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
                      store.project.tasks.filter((t) => t.status === "completed")
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
                  <h2>生成记录<span class="mock-tag ml-2">真实任务</span></h2>
                  <select v-model="taskFilter" aria-label="任务状态筛选">
                    <option value="all">全部状态</option>
                    <option value="running">生成中</option>
                    <option value="new">待执行</option><option value="queued">等待中</option><option value="detached">已断开</option><option value="unknown">状态未知</option><option value="submitting">提交中</option><option value="downloading">保存结果</option>
                    <option value="completed">已完成</option>
                    <option value="cancelled">已取消</option>
                    <option value="failed">失败</option>
                  </select>
                </div>
                <div v-if="!tasks.length" class="empty-state">
                  <ListTodo :size="30" />
                  <h3>这里还没有任务</h3>
                  <p>生成进度、取消结果和恢复记录会显示在这里。</p>
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
                  <div class="task-row-status"><small v-if="t.node">节点 {{t.node}} · {{t.steps ? `${t.steps.value}/${t.steps.max}` : '处理中'}}</small>
                    <span
                      class="status-pill"
                      :class="{
                        completed: t.status === 'completed',
                        error: t.status === 'failed',
                      }"
                      >{{ statusNames[t.status] }}
                      {{ t.status === "running" && t.progress!==null ? `节点 ${Math.round(t.progress)}%` : "" }}</span
                    >
                    <div
                      v-if="t.status==='running' && t.progress!==null"
                      class="mini-progress"
                    >
                      <i :style="{ width: `${t.progress}%` }" />
                    </div>
                  </div>
                  <button
                    v-if="['new','running','queued','cancel_requested'].includes(t.status)"
                    class="btn"
                    @click="store.cancelTask(t.id)"
                  >
                    取消</button
                  ><button
                    v-else-if="t.status === 'completed'"
                    class="btn"
                    @click="
                      targetId = t.targetId;
                      openHistory(t.targetId);
                    "
                  >
                    查看结果</button
                  ><button v-else-if="['unknown','detached','queued','running'].includes(t.status)" class="btn" @click="store.resumeTask(t.id)">
                    <RotateCcw :size="13" />恢复查询
                  </button><button v-if="(t.raw as {prompt_id?:string}).prompt_id && store.state?.activeJob!==t.id && ['queued','running','failed','cancel_requested'].includes(t.status)" class="btn" @click="store.resumeTask(t.id)">恢复查询</button><button v-if="!['new','submitting','running','queued','downloading','cancel_requested'].includes(t.status)" class="btn" @click="openGenerate(t.targetId,t.kind,undefined,t.generation)">再次生成</button><details class="task-details"><summary>任务详情</summary><pre>{{JSON.stringify(t.raw,null,2)}}</pre><button v-for="file in (t.raw as {outputs?:string[]}).outputs" :key="file" class="text-action" @click="store.openFile(file)">打开原文件</button></details>
                </div>
              </div>
            </template>
            <template v-else-if="store.page==='settings'"><SettingsPanel/></template>
          </div>
        </div>
        <TimelinePanel v-if="store.page === 'shots'" @locate="locate" />
        <footer v-else class="workspace-bottom">
          <span>XY Studio · v{{store.state?.version}}</span
          ><span>{{ store.project.name }} / 项目文件存储</span>
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
            type="number" disabled title="真实视频时长由媒体或生成参数决定"
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
          ><button class="btn btn-primary">创建项目</button>
        </footer>
      </form></StudioDialog
    >
<StudioDialog :open="modal==='generate'" @update:open="v=>!v&&cancelGeneration()" :title="gen.mode.startsWith('h3')?'生成视频 · 参数审阅':'生成图片 · 参数审阅'" :description="`结果保存至「${target?.name}」，保留已有版本。确认后才提交 ComfyUI。`"><form class="form-content" @submit.prevent="confirmGeneration"><div class="target-pill"><Link2 :size="14"/>{{target?.name}}<span>{{targetId.slice(0,8)}} · 新版本</span></div><GenerationForm v-model="gen" :target-id="targetId"/><footer class="dialog-actions"><button type="button" class="btn" @click="cancelGeneration">取消生成</button><button class="btn btn-primary">加入生成队列</button></footer></form></StudioDialog>
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
          <p class="version-prompt">{{ v.prompt }}</p><details class="version-details"><summary>完整参数与素材快照</summary><pre>{{JSON.stringify({generation:v.generation,materials:v.materials},null,2)}}</pre></details>
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
      </div><details v-if="pendingRecords.length" class="version-details"><summary>未完成记录 · {{pendingRecords.length}}</summary><div v-for="t in pendingRecords" :key="t.id"><p>{{statusNames[t.status]}} · {{t.time}} · {{t.error}}</p><pre>{{t.prompt}}</pre></div></details></StudioDialog
    >
<StudioDialog :open="modal==='review'" @update:open="v=>!v&&(modal=null)" :title="suggestion?.title || '审阅 AI 操作'" description="确认后才修改项目；取消会反馈给 Agent 并停止相关续办。"><pre class="review-description">{{reviewText}}</pre><footer class="dialog-actions"><button class="btn" @click="suggestion && store.reviewSuggestion(suggestion,false);modal=null">取消本次操作</button><button class="btn btn-primary" @click="suggestion && store.reviewSuggestion(suggestion,true);modal=null">确认{{suggestion?.title}}</button></footer></StudioDialog>
<StudioDialog :open="modal==='delete'" @update:open="v=>!v&&(modal=null)" title="删除条目" description="文件和历史输出仍保留，相关镜头解除素材关联。"><p>确认删除「{{target?.name}}」？</p><footer class="dialog-actions"><button class="btn" @click="modal=null">保留条目</button><button class="btn btn-primary" @click="deleteTarget">确认删除</button></footer></StudioDialog>
    <StudioDialog
      :open="modal === 'preview'"
      @update:open="(v) => !v && (modal = null)"
      title="素材预览"
      description="项目原始素材 · 等比预览与缩放"
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
      <button v-if="preview" class="btn mb-3" @click="store.openFile(preview.file)">打开原文件</button><div class="large-preview">
        <VideoPreview
          v-if="preview?.kind === 'video'"
          :notice="preview.error" :media="preview.media" :url="preview.url" :file="preview.file" @fallback="store.openFile"
          :duration="0"
          label="视频预览"
        /><MediaThumb
          v-else
          :media="preview?.media"
          label="大图预览"
          :style="{ width: `${zoom * 100}%`, minWidth: `${zoom * 100}%` }"
        /></div
    ></StudioDialog>
  </div>
</template>
