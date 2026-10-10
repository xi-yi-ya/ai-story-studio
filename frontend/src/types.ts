export type Page='projects'|'characters'|'scenes'|'shots'|'tasks'|'settings';
export type MediaKey=string;
export type Status='new'|'queued'|'submitting'|'running'|'downloading'|'completed'|'cancel_requested'|'cancelled'|'detached'|'unknown'|'failed';
export interface Generation { mode:string;prompt:string;ratio:string;megapixels:number;seconds:number;seed:string|number;steps:number;cinema:boolean;cinema_strength:number;quad_lora:boolean;qwen_int8:boolean;styles:string[];scale:number;references:string[] }
export interface Version { id:string;media:string;url:string;file:string;kind:'image'|'video';prompt:string;time:string;label:string;generation?:Generation;materials?:unknown[];error?:string }
export interface Asset { id:string;name:string;description:string;kind:'characters'|'scenes';versions:Version[];current:string;tags:string[];imageFile:string;needsReview:boolean }
export interface Shot { id:string;name:string;numberName:string;description:string;duration:number;durationLabel:string;assetIds:string[];versions:Version[];imageVersion:string|null;videoVersion:string|null;collapsed:boolean;imageFile:string;needsReview:boolean;references:{file:string;url:string}[] }
export interface Task { id:string;targetId:string;targetName:string;kind:'image'|'video';status:Status;progress:number|null;steps:{value:number;max:number}|null;node:string|null;prompt:string;time:string;error?:string;generation:Generation;outputs:string[];raw:unknown }
export interface Suggestion { id:string;name:string;title:string;args:Record<string,unknown>;targetId?:string;targetName?:string;generation?:Generation }
export interface ChatMessage { id:string;role:'user'|'assistant'|'tool';text:string;time:string;targetName?:string;activity:{type:string;skill?:string;file?:string;query?:string;sources?:{title:string;url:string}[];message?:string}[] }
export interface ProjectState { id:string;name:string;root:string;story:string;updated:string;assets:Asset[];shots:Shot[];tasks:Task[];chat:ChatMessage[];paused:boolean }
export interface State { version:string;config:{comfy:string;model:string;models:string[];online:boolean;keySet:boolean};catalog:{modes:Record<string,string>;ratios:string[];styles:Record<string,string>;skills:unknown};recent:{path:string;title:string}[];selectedId:string|null;contextIds:string[];activeJob:string|null;busy:boolean;modelsBusy:boolean;status:string;error:string;review:Suggestion|null;project:ProjectState|null }
export type GenerationInput=Generation;
