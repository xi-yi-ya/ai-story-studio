<script setup lang="ts">
import {ref,watch} from 'vue';
import {useStudio} from '../stores/studio';
const store=useStudio();
const url=ref(''),key=ref('');watch(()=>store.state?.config.comfy,v=>url.value=v||'',{immediate:true});
async function save(){await store.saveSettings({comfy:url.value,key:key.value});key.value='';store.notify('设置已保存，密钥保留在 Windows 凭据管理器')}
</script>
<template><form class="settings-card surface form-content" @submit.prevent="save"><h2>创作工作台</h2><label>ComfyUI 地址<input v-model="url" type="url" required aria-label="ComfyUI 地址"/></label><label>DeepSeek 模型<select v-model="store.model" aria-label="设置中的模型"><option v-for="model in store.state?.config.models" :key="model">{{model}}</option></select></label><button class="btn" type="button" :disabled="store.state?.modelsBusy" @click="store.refreshModels">{{store.state?.modelsBusy?'正在读取账户模型…':'刷新账户模型'}}</button><label>DeepSeek API Key<input v-model="key" type="password" autocomplete="off" placeholder="留空保留现有密钥" aria-label="DeepSeek API Key"/></label><p class="form-note">{{store.state?.config.keySet?'已有密钥，保存在 Windows 凭据管理器。':'尚未设置密钥，手动生成仍可使用。'}}<br/>对话发送故事、条目描述及相对文件名；不会上传图片像素。联网检索使用同一 DeepSeek Key，会产生 API 费用。</p><button class="btn btn-primary">保存设置</button><section class="prototype-note"><h3>内置技能 · 按需读取</h3><p>Qwen Image 与 MiniMax H3 指南沿用现有版本。助手读取、检索和错误记录会显示在对应回复中。</p></section></form></template>
