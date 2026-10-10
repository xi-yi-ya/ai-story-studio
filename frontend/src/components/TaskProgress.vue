<script setup lang="ts">
import { computed } from 'vue';
import type { Task } from '../types';

const props = defineProps<{ task?: Task; paused?: boolean }>();
const visible = computed(() => !!props.task && ['new', 'submitting', 'queued', 'running', 'downloading', 'cancel_requested', 'unknown', 'detached'].includes(props.task.status));
const percent = computed(() => {
  const t = props.task;
  return t?.status === 'running' && t.progress !== null && Number.isFinite(t.progress)
    ? Math.max(0, Math.min(100, t.progress)) : null;
});
const label = computed(() => {
  const t = props.task;
  if (!t) return '';
  if (t.status === 'running') {
    const node = t.node ? ` · 节点 ${t.node}` : '';
    return percent.value === null
      ? `生成中${node} · 等待节点进度`
      : `生成中${node} · ${t.steps ? `${t.steps.value}/${t.steps.max} 步 · ` : ''}${Math.round(percent.value)}%`;
  }
  return ({ new: props.paused ? '等待执行 · 队列已暂停' : '等待执行', submitting: '正在提交到 ComfyUI', queued: 'ComfyUI 排队中', downloading: '正在保存生成结果', cancel_requested: '正在请求取消', unknown: '状态待核对 · 请恢复查询', detached: '查询已断开 · 请恢复查询' } as Record<string, string>)[t.status] || '';
});
</script>

<template>
  <div v-if="visible && task" class="generation-progress" :data-task-id="task.id" @click.stop>
    <div class="generation-progress-label"><span>{{ label }}</span><small v-if="percent !== null">当前节点</small></div>
    <div
      class="generation-progress-track"
      :class="{ 'without-percent': percent === null }"
      role="progressbar"
      :aria-label="`${task.targetName}生成节点进度`"
      :aria-valuenow="percent === null ? undefined : percent"
      :aria-valuemin="0"
      :aria-valuemax="100"
      :aria-valuetext="label"
      title="进度来自 ComfyUI 当前节点；节点达到 100% 后仍可能解码或保存，结果保存完成才算任务完成。"
    ><span v-if="percent !== null" :style="{ width: `${percent}%` }" /></div>
  </div>
</template>
