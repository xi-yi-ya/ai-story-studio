<script setup lang="ts">
import { mediaCrops } from "../mock";
import type { MediaKey } from "../types";
import { Image as ImageIcon } from "lucide-vue-next";
defineProps<{ media?: MediaKey | null; label?: string }>();
</script>
<template>
  <div
    class="media-thumb"
    :role="media ? 'img' : undefined"
    :aria-label="label"
  >
    <svg
      v-if="media"
      :viewBox="mediaCrops[media]!.join(' ')"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <image href="/media/design-reference.png" width="1536" height="1024" />
    </svg>
    <div v-else class="media-empty">
      <ImageIcon :size="25" :stroke-width="1.3" /><span>{{
        label || "等待你的第一个版本"
      }}</span>
    </div>
  </div>
</template>
