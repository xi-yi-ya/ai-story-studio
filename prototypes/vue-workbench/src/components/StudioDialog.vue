<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "reka-ui";
import { X } from "lucide-vue-next";
defineProps<{
  open: boolean;
  title: string;
  description?: string;
  wide?: boolean;
}>();
defineEmits<{ "update:open": [value: boolean] }>();
</script>
<template>
  <DialogRoot :open="open" @update:open="$emit('update:open', $event)">
    <DialogPortal
      ><DialogOverlay class="dialog-overlay" />
      <DialogContent class="dialog-content" :class="{ wide }">
        <header class="dialog-head">
          <div>
            <DialogTitle class="dialog-title">{{ title }}</DialogTitle
            ><DialogDescription class="muted text-sm mt-1">{{
              description || "所有改动仅作用于当前浏览器的原型数据。"
            }}</DialogDescription>
          </div>
          <DialogClose class="icon-btn" aria-label="关闭弹窗"
            ><X :size="18"
          /></DialogClose>
        </header>
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
