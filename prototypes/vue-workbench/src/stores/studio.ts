import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";
import { demoProject } from "../mock";
import type {
  Asset,
  ChatMessage,
  GenerationInput,
  Page,
  ProjectState,
  Shot,
  Suggestion,
  Task,
} from "../types";

const STORAGE_KEY = "xy-studio-vue-prototype-v1";
const uid = () => crypto.randomUUID();
const time = () =>
  new Date().toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });

export const useStudio = defineStore("studio", () => {
  let initial = [demoProject()];
  let initialId = initial[0]!.id;
  let storageError = "";
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      if (
        saved.schema !== "xy-vue-mock-1" ||
        !Array.isArray(saved.projects) ||
        !saved.projects.length
      )
        throw new Error("原型存档无法识别");
      for (const p of saved.projects) {
        if (
          !p.id ||
          !Array.isArray(p.assets) ||
          !Array.isArray(p.shots) ||
          !Array.isArray(p.tasks) ||
          !Array.isArray(p.chat)
        )
          throw new Error("原型存档不完整");
        p.tasks.forEach((task: Task) => {
          if (task.status === "running") task.status = "queued";
        });
      }
      initial = saved.projects;
      initialId = saved.activeId;
    }
  } catch (e) {
    storageError = `本地原型存档读取失败：${String(e)}。本次显示示例，可重新保存。`;
  }
  const projects = ref<ProjectState[]>(initial);
  const activeId = ref(
    initial.some((p) => p.id === initialId) ? initialId : initial[0]!.id,
  );
  const project = computed(
    () => projects.value.find((p) => p.id === activeId.value)!,
  );
  const page = ref<Page>("shots");
  const assistantOpen = ref(true);
  const selectedId = ref<string | null>("shot-02");
  const model = ref("DeepSeek Flash");
  const online = ref(false);
  const paused = ref(
    initial.some((p) => p.tasks.some((t) => t.status === "queued")),
  );
  const toast = ref(storageError);
  const persistenceError = ref(storageError);
  const busy = ref(false);
  const selection = computed(
    () =>
      project.value.shots.find((s) => s.id === selectedId.value) ||
      project.value.assets.find((a) => a.id === selectedId.value) ||
      null,
  );
  const totalDuration = computed(() =>
    project.value.shots.reduce((n, s) => n + s.duration, 0),
  );
  const pendingTasks = computed(
    () =>
      project.value.tasks.filter(
        (t) => t.status === "running" || t.status === "queued",
      ).length,
  );
  const timers = new Map<string, ReturnType<typeof setInterval>>();
  let toastTimer: ReturnType<typeof setTimeout>;
  function notify(text: string) {
    toast.value = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast.value = ""), 4200);
  }
  function save() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          schema: "xy-vue-mock-1",
          activeId: activeId.value,
          projects: projects.value,
        }),
      );
      persistenceError.value = "";
    } catch (e) {
      persistenceError.value = `浏览器保存失败：${String(e)}`;
    }
  }
  watch([projects, activeId], save, { deep: true });
  function select(id: string) {
    selectedId.value = id;
  }
  function openProject(id: string) {
    activeId.value = id;
    selectedId.value = null;
    page.value = "shots";
  }
  function createProject(name: string) {
    name = name.trim();
    if (!name) {
      notify("请输入项目名称");
      return;
    }
    const p: ProjectState = {
      id: uid(),
      name,
      story: "",
      updated: "刚刚",
      assets: [],
      shots: [],
      tasks: [],
      chat: [
        {
          id: uid(),
          role: "assistant",
          text: "从一个故事开始吧。你可以添加角色和场景，再把它们连接成镜头。这里的对话和生成都是本地模拟。",
          time: time(),
        },
      ],
    };
    projects.value.push(p);
    openProject(p.id);
    notify("已创建本地原型项目");
  }
  function newShot() {
    const id = uid();
    project.value.shots.push({
      id,
      name: "新的镜头",
      description: "",
      duration: 5,
      assetIds: [],
      versions: [],
      imageVersion: null,
      videoVersion: null,
      collapsed: false,
    });
    selectedId.value = id;
    notify("已添加镜头，可编辑描述并关联素材");
    return id;
  }
  function addAsset(kind: Asset["kind"], name: string, description: string) {
    const id = uid();
    project.value.assets.push({
      id,
      name,
      kind,
      description,
      tags: [],
      versions: [],
      current: "",
    });
    selectedId.value = id;
    notify("素材已添加，点击生成新版本开始探索");
  }
  function remove(id: string) {
    if (
      project.value.tasks.some(
        (t) =>
          t.targetId === id &&
          (t.status === "running" || t.status === "queued"),
      )
    ) {
      notify("请先取消此条目的生成任务");
      return;
    }
    project.value.assets = project.value.assets.filter((a) => a.id !== id);
    project.value.shots = project.value.shots.filter((s) => s.id !== id);
    project.value.shots.forEach(
      (s) => (s.assetIds = s.assetIds.filter((a) => a !== id)),
    );
    if (selectedId.value === id) selectedId.value = null;
    notify("条目已移除，相关镜头已解除素材关联");
  }
  function useVersion(targetId: string, versionId: string) {
    const s = project.value.shots.find((s) => s.id === targetId);
    const a = project.value.assets.find((a) => a.id === targetId);
    const v = (s || a)?.versions.find((v) => v.id === versionId);
    if (!v) return;
    if (s) {
      if (v.kind === "image") s.imageVersion = v.id;
      else s.videoVersion = v.id;
    }
    if (a) a.current = v.id;
    notify("已设为当前版本，其他版本仍保留");
  }
  function taskStatus(targetId: string) {
    return [...project.value.tasks]
      .reverse()
      .find((t) => t.targetId === targetId);
  }
  function queueGeneration(input: GenerationInput) {
    const target =
      project.value.shots.find((s) => s.id === input.targetId) ||
      project.value.assets.find((a) => a.id === input.targetId);
    if (!target) {
      notify("目标已移除，未加入任务");
      return false;
    }
    const task: Task = {
      id: uid(),
      targetId: target.id,
      targetName: target.name,
      kind: input.kind,
      status: "queued",
      progress: 0,
      prompt: input.prompt,
      time: time(),
    };
    project.value.tasks.push(task);
    if ("duration" in target && input.kind === "video")
      target.duration = input.duration;
    notify("模拟任务已加入队列，结果将保存在原条目中");
    pump();
    return true;
  }
  function pump() {
    if (paused.value || timers.size) return;
    const p = projects.value.find((p) =>
      p.tasks.some((t) => t.status === "queued"),
    );
    const task = p?.tasks.find((t) => t.status === "queued");
    if (!p || !task) return;
    task.status = "running";
    const timer = setInterval(() => {
      if (paused.value) return;
      task.progress = Math.min(100, task.progress + 20);
      if (task.progress < 100) return;
      clearInterval(timer);
      timers.delete(task.id);
      const target: Shot | Asset | undefined =
        p.shots.find((s) => s.id === task.targetId) ||
        p.assets.find((a) => a.id === task.targetId);
      if (!target) {
        task.status = "failed";
        task.error = "目标条目已移除，结果未写入其他素材";
        pump();
        return;
      }
      const fallback =
        "duration" in target
          ? target.assetIds.includes("scene-inside")
            ? "conversation"
            : "arrival"
          : target.kind === "characters"
            ? "girl"
            : "outside";
      const current = target.versions.find(
        (v) =>
          v.id ===
          ("duration" in target ? target.imageVersion : target.current),
      );
      const media =
        task.kind === "image" && current?.media === "girl"
          ? "arrival"
          : current?.media || fallback;
      const version = {
        id: uid(),
        media,
        kind: task.kind,
        prompt: task.prompt,
        time: `今天 ${time()}`,
        label: `模拟版本 ${target.versions.length + 1}`,
      };
      target.versions.unshift(version);
      if ("duration" in target) {
        if (task.kind === "video") target.videoVersion = version.id;
        else target.imageVersion = version.id;
      } else target.current = version.id;
      task.status = "done";
      notify(`${task.targetName} · 模拟生成完成`);
      pump();
    }, 500);
    timers.set(task.id, timer);
  }
  function toggleQueue() {
    paused.value = !paused.value;
    if (!paused.value) pump();
  }
  function cancelTask(id: string) {
    const task = project.value.tasks.find((t) => t.id === id);
    if (!task || !["running", "queued"].includes(task.status)) return;
    const timer = timers.get(id);
    if (timer) clearInterval(timer);
    timers.delete(id);
    task.status = "cancelled";
    notify("已取消模拟任务");
    pump();
  }
  function retryTask(id: string) {
    const task = project.value.tasks.find((t) => t.id === id);
    if (!task) return;
    task.status = "queued";
    task.progress = 0;
    task.error = undefined;
    pump();
  }
  function sendChat(text: string) {
    if (busy.value || !text.trim()) return;
    const p = project.value;
    const target = selection.value;
    p.chat.push({
      id: uid(),
      role: "user",
      text: text.trim(),
      time: time(),
      targetName: target?.name,
    });
    busy.value = true;
    setTimeout(() => {
      const msg: ChatMessage = {
        id: uid(),
        role: "assistant",
        time: time(),
        text: target
          ? `我会围绕「${target.name}」整理这个修改：${text.trim()}。保留已有素材关联与满意的版本，下面是可审阅的生成建议。`
          : `收到：${text.trim()}。先选中一个角色、场景或镜头，我就能把建议关联到具体对象。当前是本地模拟助手。`,
      };
      if (target)
        msg.suggestion = {
          id: uid(),
          targetId: target.id,
          targetName: target.name,
          prompt: `${text.trim()}。保留原有角色外观、构图关系与环境光线。`,
          status: "pending",
        };
      p.chat.push(msg);
      busy.value = false;
    }, 700);
  }
  function reviewSuggestion(suggestion: Suggestion, accepted: boolean) {
    suggestion.status = accepted ? "approved" : "rejected";
  }
  function createStressProject() {
    const p = demoProject();
    p.id = uid();
    p.name = "长项目 · 120 镜头";
    p.story = "用于检查大量镜头和长文本的示例项目。".repeat(12);
    p.shots = Array.from({ length: 120 }, (_, i) => ({
      ...structuredClone(p.shots[i % 3]!),
      id: uid(),
      name: `长项目镜头 ${i + 1}`,
      description:
        "雨夜街道上的光影与人物的情绪相互呼应，镜头需要保留前景遮挡、人物朝向和动作节奏。".repeat(
          12,
        ),
      collapsed: i > 1,
    }));
    p.chat = [];
    p.tasks = [];
    projects.value.push(p);
    openProject(p.id);
  }
  function exportMock() {
    const blob = new Blob(
      [
        JSON.stringify(
          {
            schema: "xy-vue-mock-1",
            activeId: activeId.value,
            projects: projects.value,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "xy-studio-prototype.json";
    a.click();
    URL.revokeObjectURL(url);
    notify("已导出原型存档");
  }
  return {
    projects,
    activeId,
    project,
    page,
    assistantOpen,
    selectedId,
    selection,
    model,
    online,
    toast,
    persistenceError,
    paused,
    busy,
    totalDuration,
    pendingTasks,
    notify,
    save,
    select,
    openProject,
    createProject,
    newShot,
    addAsset,
    remove,
    useVersion,
    taskStatus,
    queueGeneration,
    toggleQueue,
    cancelTask,
    retryTask,
    sendChat,
    reviewSuggestion,
    createStressProject,
    exportMock,
  };
});
