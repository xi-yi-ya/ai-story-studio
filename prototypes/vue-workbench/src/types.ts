export type Page =
  | "projects"
  | "characters"
  | "scenes"
  | "shots"
  | "tasks"
  | "settings";
export type MediaKey =
  | "arrival"
  | "conversation"
  | "girl"
  | "clerk"
  | "outside"
  | "inside";
export type Status =
  | "ready"
  | "queued"
  | "running"
  | "done"
  | "cancelled"
  | "failed";
export interface Version {
  id: string;
  media: MediaKey;
  kind: "image" | "video";
  prompt: string;
  time: string;
  label: string;
}
export interface Asset {
  id: string;
  name: string;
  description: string;
  kind: "characters" | "scenes";
  versions: Version[];
  current: string;
  tags: string[];
}
export interface Shot {
  id: string;
  name: string;
  description: string;
  duration: number;
  assetIds: string[];
  versions: Version[];
  imageVersion: string | null;
  videoVersion: string | null;
  collapsed: boolean;
}
export interface Task {
  id: string;
  targetId: string;
  targetName: string;
  kind: "image" | "video";
  status: Status;
  progress: number;
  prompt: string;
  time: string;
  error?: string;
}
export interface Suggestion {
  id: string;
  targetId: string;
  targetName: string;
  prompt: string;
  status: "pending" | "approved" | "rejected";
}
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  time: string;
  targetName?: string;
  suggestion?: Suggestion;
}
export interface ProjectState {
  id: string;
  name: string;
  story: string;
  updated: string;
  assets: Asset[];
  shots: Shot[];
  tasks: Task[];
  chat: ChatMessage[];
}
export interface GenerationInput {
  targetId: string;
  kind: "image" | "video";
  prompt: string;
  ratio: string;
  resolution: string;
  duration: number;
  lora: boolean;
  upscale: number;
}
