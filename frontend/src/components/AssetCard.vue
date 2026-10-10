<script setup lang="ts">
import { computed } from "vue";
import {
  MoreHorizontal,
  Pencil,
  Sparkles,
  History,
  Send,
  Trash2,
  Check,
  ImagePlus,
} from "lucide-vue-next";
import {
  ContextMenuRoot,
  ContextMenuTrigger,
  ContextMenuPortal,
  ContextMenuContent,
  ContextMenuItem,
  DropdownMenuRoot,
  DropdownMenuTrigger,
  DropdownMenuPortal,
  DropdownMenuContent,
  DropdownMenuItem,
} from "reka-ui";
import type { Asset } from "../types";
import { useStudio } from "../stores/studio";
import MediaThumb from "./MediaThumb.vue";
const props = defineProps<{ asset: Asset }>();
const emit = defineEmits<{
  edit: [id: string];
  delete: [id:string];
  generate: [id: string];
  history: [id: string];
  preview: [id: string];
}>();
const store = useStudio();
const current = computed(() =>
  props.asset.versions.find((v) => v.id === props.asset.current),
);
const items = [{action:"import",name:"导入图片",icon:ImagePlus},
  { action: "context", name: "发送给 AI", icon: Send },
  { action: "edit", name: "编辑资料", icon: Pencil },
  { action: "generate", name: "生成新版本", icon: Sparkles },
  { action: "history", name: "查看历史版本", icon: History },
  { action: "delete", name: "删除素材", icon: Trash2 },
];
function act(action: string) {
  if (action === "context") {
    store.pin(props.asset.id);
    store.notify(`已将「${props.asset.name}」发送到 AI 上下文`);
  } else if (action === "delete") emit("delete",props.asset.id);
  else if (action === "import") void store.importImage(props.asset.id);
  else emit(action as "edit", props.asset.id);
}
</script>
<template>
  <ContextMenuRoot
    ><ContextMenuTrigger as-child>
      <article
        class="asset-card surface"
        :class="{ selected: store.selectedId === asset.id }"
        :data-testid="`asset-${asset.id}`"
        @click="store.select(asset.id)"
      >
        <button
          class="asset-image"
          :aria-label="`查看${asset.name}大图`"
          @dblclick="emit('preview', asset.id)"
        >
          <MediaThumb :media="current?.media" :label="asset.name" /><span
            v-if="store.selectedId === asset.id"
            class="selection-check"
            ><Check :size="13" /></span
          ><span class="version-chip">{{
            asset.versions.length
              ? `${asset.versions.length} 个版本`
              : "等待生成"
          }}</span>
        </button>
        <div class="asset-info">
          <div class="flex items-center justify-between gap-2">
            <h3>{{ asset.name }}</h3>
            <DropdownMenuRoot
              ><DropdownMenuTrigger
                class="icon-btn"
                :aria-label="`${asset.name}更多操作`"
                ><MoreHorizontal :size="19" /></DropdownMenuTrigger
              ><DropdownMenuPortal
                ><DropdownMenuContent class="menu-content" align="end"
                  ><DropdownMenuItem
                    v-for="item in items"
                    :key="item.action"
                    class="menu-item"
                    :class="{ danger: item.action === 'delete' }"
                    @select="act(item.action)"
                    ><component :is="item.icon" :size="15" />{{
                      item.name
                    }}</DropdownMenuItem
                  ></DropdownMenuContent
                ></DropdownMenuPortal
              ></DropdownMenuRoot
            >
          </div>
          <p class="asset-description" :title="asset.description">
            {{ asset.description || "添加描述，让这个素材拥有自己的故事。" }}
          </p>
          <div class="asset-tags">
            <span v-for="tag in asset.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
        <footer>
          <button @click.stop="emit('generate', asset.id)">
            <ImagePlus :size="15" />生成新版本</button
          ><button
            :aria-label="`${asset.name}历史版本`"
            @click.stop="emit('history', asset.id)"
          >
            <History :size="15" />历史
          </button>
        </footer>
      </article> </ContextMenuTrigger
    ><ContextMenuPortal
      ><ContextMenuContent class="menu-content"
        ><ContextMenuItem
          v-for="item in items"
          :key="item.action"
          class="menu-item"
          :class="{ danger: item.action === 'delete' }"
          @select="act(item.action)"
          ><component :is="item.icon" :size="15" />{{
            item.name
          }}</ContextMenuItem
        ></ContextMenuContent
      ></ContextMenuPortal
    ></ContextMenuRoot
  >
</template>
