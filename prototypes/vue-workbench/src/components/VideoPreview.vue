<script setup lang="ts">
import { ref, computed, onUnmounted } from "vue";
import { Play, Pause, Maximize2, VolumeX } from "lucide-vue-next";
import MediaThumb from "./MediaThumb.vue";
import type { MediaKey } from "../types";
const props = defineProps<{
  media?: MediaKey | null;
  duration: number;
  label: string;
}>();
defineEmits<{ enlarge: [] }>();
const playing = ref(false);
const progress = ref(0);
const timestamp = computed(
  () => `00:${String(Math.floor(progress.value)).padStart(2, "0")}`,
);
let timer: ReturnType<typeof setInterval> | undefined;
function toggle() {
  if (!props.media) return;
  playing.value = !playing.value;
  clearInterval(timer);
  if (playing.value) {
    if (progress.value >= props.duration) progress.value = 0;
    timer = setInterval(() => {
      progress.value = Math.min(props.duration, progress.value + 0.1);
      if (progress.value >= props.duration) {
        playing.value = false;
        clearInterval(timer);
      }
    }, 100);
  }
}
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <div class="video-preview" :class="{ playing }">
    <MediaThumb :media="media" :label="media ? label : '视频尚未生成'" />
    <span v-if="media" class="preview-watermark">模拟预览</span>
    <button
      v-if="media && !playing"
      class="big-play"
      aria-label="播放模拟预览"
      @click.stop="toggle"
    >
      <Play :size="24" fill="currentColor" />
    </button>
    <div v-if="media" class="video-controls" @click.stop>
      <button :aria-label="playing ? '暂停预览' : '播放预览'" @click="toggle">
        <Pause v-if="playing" :size="15" /><Play
          v-else
          :size="15"
          fill="currentColor"
        />
      </button>
      <input
        v-model.number="progress"
        type="range"
        min="0"
        :max="duration"
        step=".1"
        aria-label="预览进度"
      />
      <span>{{ timestamp }} / 00:{{ String(duration).padStart(2, "0") }}</span
      ><VolumeX :size="14" /><button
        aria-label="放大预览"
        @click="$emit('enlarge')"
      >
        <Maximize2 :size="14" />
      </button>
    </div>
  </div>
</template>
