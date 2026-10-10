<script setup lang="ts">
import { computed, ref } from "vue";
import {
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Pencil,
  Plus,
  X,
  History,
  ImagePlus,
  Clapperboard,
  Send,
  Trash2,
  Check,
  Link2,
} from "lucide-vue-next";
import {
  DropdownMenuRoot,
  DropdownMenuTrigger,
  DropdownMenuPortal,
  DropdownMenuContent,
  DropdownMenuItem,
} from "reka-ui";
import type { Shot, Version } from "../types";
import { useStudio } from "../stores/studio";
import MediaThumb from "./MediaThumb.vue";
import VideoPreview from "./VideoPreview.vue";
const props = defineProps<{ shot: Shot; index: number }>();
const emit = defineEmits<{
  edit: [id: string];
  generate: [id: string, kind: "image" | "video"];
  link: [id: string];
  preview: [version: Version];
}>();
const store = useStudio();
const history = ref<"image" | "video" | null>(null);
const currentImage = computed(() =>
  props.shot.versions.find((v) => v.id === props.shot.imageVersion),
);
const currentVideo = computed(() =>
  props.shot.versions.find((v) => v.id === props.shot.videoVersion),
);
const linked = computed(() =>
  props.shot.assetIds
    .map((id) => store.project.assets.find((a) => a.id === id))
    .filter((a) => !!a),
);
const task = computed(() => store.taskStatus(props.shot.id));
const status = computed(() =>
  task.value?.status === "running"
    ? `生成中 ${task.value.progress}%`
    : task.value?.status === "queued"
      ? "等待生成"
      : task.value?.status === "cancelled"
        ? "已取消"
        : task.value?.status === "failed"
          ? "生成失败"
          : props.shot.imageVersion
            ? "已完成"
            : "待制作",
);
function toggleHistory(kind: "image" | "video") {
  history.value = history.value === kind ? null : kind;
}
</script>
<template>
  <article
    class="shot-card surface"
    :class="{
      selected: store.selectedId === shot.id,
      collapsed: shot.collapsed,
    }"
    :id="`shot-${shot.id}`"
    :data-testid="`shot-${shot.id}`"
    @click="store.select(shot.id)"
  >
    <header class="shot-header">
      <button class="shot-heading" @click.stop="store.select(shot.id)">
        <span class="shot-number"
          >SHOT {{ String(index + 1).padStart(2, "0") }}</span
        >
        <h3>{{ shot.name }}</h3>
      </button>
      <div class="flex items-center gap-3">
        <span
          class="status-pill"
          :class="{
            completed: status === '已完成',
            working: task?.status === 'running',
            error: task?.status === 'failed',
          }"
          ><span class="status-dot" />{{ status }}</span
        ><span class="shot-duration">{{ shot.duration }} 秒</span>
        <DropdownMenuRoot
          ><DropdownMenuTrigger
            class="icon-btn"
            :aria-label="`镜头${index + 1}更多操作`"
            ><MoreHorizontal :size="19" /></DropdownMenuTrigger
          ><DropdownMenuPortal
            ><DropdownMenuContent class="menu-content" align="end"
              ><DropdownMenuItem
                class="menu-item"
                @select="emit('edit', shot.id)"
                ><Pencil :size="15" />编辑镜头</DropdownMenuItem
              ><DropdownMenuItem
                class="menu-item"
                @select="
                  store.assistantOpen = true;
                  store.select(shot.id);
                "
                ><Send :size="15" />发送给 AI</DropdownMenuItem
              ><DropdownMenuItem
                class="menu-item danger"
                @select="store.remove(shot.id)"
                ><Trash2 :size="15" />删除镜头</DropdownMenuItem
              ></DropdownMenuContent
            ></DropdownMenuPortal
          ></DropdownMenuRoot
        >
        <button
          class="icon-btn"
          :aria-label="`${shot.collapsed ? '展开' : '折叠'}镜头${index + 1}`"
          :aria-expanded="!shot.collapsed"
          @click.stop="shot.collapsed = !shot.collapsed"
        >
          <ChevronRight v-if="shot.collapsed" :size="18" /><ChevronDown
            v-else
            :size="18"
          />
        </button>
      </div>
    </header>
    <div v-if="!shot.collapsed" class="shot-body">
      <section class="shot-description">
        <div class="section-caption">
          镜头描述<button
            class="icon-btn"
            :aria-label="`编辑镜头${index + 1}`"
            @click.stop="emit('edit', shot.id)"
          >
            <Pencil :size="14" />
          </button>
        </div>
        <p :title="shot.description">
          {{ shot.description || "描述这个镜头里，故事如何发生。" }}
        </p>
        <div class="section-caption mt-5">
          使用素材 <span class="muted text-xs">{{ linked.length }}</span>
        </div>
        <div class="linked-assets">
          <div v-for="asset in linked" :key="asset.id" class="linked-item">
            <button
              class="linked-image"
              :aria-label="`选择素材${asset.name}`"
              @click.stop="store.select(asset.id)"
            >
              <MediaThumb
                :media="
                  asset.versions.find((v) => v.id === asset.current)?.media
                "
                :label="asset.name"
              /></button
            ><button
              class="unlink"
              :aria-label="`解除${asset.name}关联`"
              @click.stop="
                shot.assetIds = shot.assetIds.filter((id) => id !== asset.id)
              "
            >
              <X :size="11" /></button
            ><span>{{ asset.name }}</span>
          </div>
          <button
            class="add-reference"
            :aria-label="`关联镜头${index + 1}素材`"
            @click.stop="emit('link', shot.id)"
          >
            <Plus :size="19" />
          </button>
        </div>
        <button class="text-action" @click.stop="emit('link', shot.id)">
          <Link2 :size="12" />管理素材关联
        </button>
      </section>
      <section class="shot-media">
        <div class="section-caption">
          分镜图
          <span class="subtle-label">{{
            currentImage ? "当前版本" : "等待生成"
          }}</span>
        </div>
        <button
          class="shot-image"
          :aria-label="`查看镜头${index + 1}分镜图`"
          :disabled="!currentImage"
          @dblclick.stop="currentImage && emit('preview', currentImage)"
        >
          <MediaThumb :media="currentImage?.media" label="双击查看分镜大图" />
        </button>
        <div class="media-actions">
          <button
            class="btn btn-soft"
            @click.stop="emit('generate', shot.id, 'image')"
          >
            <ImagePlus :size="15" />生成图片</button
          ><button
            class="btn"
            :class="{ active: history === 'image' }"
            @click.stop="toggleHistory('image')"
          >
            <History :size="14" />历史版本<span class="count">{{
              shot.versions.filter((v) => v.kind === "image").length
            }}</span>
          </button>
        </div>
      </section>
      <section class="shot-media">
        <div class="section-caption">
          生成视频
          <span class="subtle-label">{{
            currentVideo ? `${shot.duration}s · 模拟` : "等待生成"
          }}</span>
        </div>
        <VideoPreview
          :media="currentVideo?.media"
          :duration="shot.duration"
          :label="`${shot.name}模拟视频`"
          @enlarge="currentVideo && emit('preview', currentVideo)"
        />
        <div class="media-actions">
          <button
            class="btn btn-soft"
            @click.stop="emit('generate', shot.id, 'video')"
          >
            <Clapperboard :size="15" />生成视频</button
          ><button
            class="btn"
            :class="{ active: history === 'video' }"
            @click.stop="toggleHistory('video')"
          >
            <History :size="14" />历史版本<span class="count">{{
              shot.versions.filter((v) => v.kind === "video").length
            }}</span>
          </button>
        </div>
      </section>
    </div>
    <div v-if="task?.status === 'running'" class="task-progress">
      <span :style="{ width: `${task.progress}%` }" />
    </div>
    <div v-if="history && !shot.collapsed" class="inline-history">
      <div class="flex items-center justify-between">
        <span class="section-caption"
          >{{ history === "image" ? "分镜图" : "视频" }}版本 ·
          始终保留在此镜头中</span
        ><button
          class="icon-btn"
          aria-label="关闭镜头历史"
          @click.stop="history = null"
        >
          <X :size="15" />
        </button>
      </div>
      <p
        v-if="!shot.versions.some((v) => v.kind === history)"
        class="muted py-5"
      >
        还没有生成记录。尝试制作第一个版本。
      </p>
      <div class="history-strip">
        <button
          v-for="v in shot.versions.filter((v) => v.kind === history)"
          :key="v.id"
          class="history-item"
          :class="{
            active: v.id === shot.imageVersion || v.id === shot.videoVersion,
          }"
          @click.stop="store.useVersion(shot.id, v.id)"
        >
          <MediaThumb :media="v.media" :label="v.label" />
          <div>
            <span>{{ v.label }}</span
            ><Check
              v-if="v.id === shot.imageVersion || v.id === shot.videoVersion"
              :size="13"
            />
          </div>
          <small>{{ v.time }}</small>
        </button>
      </div>
    </div>
  </article>
</template>
