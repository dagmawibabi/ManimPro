import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export type SceneInfo = { name: string; line: number };
export type WorkerError = {
  message: string;
  line?: number | null;
  traceback?: string;
  cancelled?: boolean;
  /** A fix the app can offer, e.g. "fetch_3b1b" (download 3Blue1Brown's shared code). */
  action?: string | null;
};

export type ProjectInfo = {
  dir: string;
  media_dir: string;
  files: string[];
  folders: string[];
  audio: string[];
  /** Every other file in the project: data, images, notes. */
  others: string[];
  timeline: unknown | null;
};

export type RenderResult = {
  video: string;
  /** Preview frame of the scene, when one could be saved. */
  thumb?: string;
  /** Filmstrip of evenly spaced frames (for timeline clips). */
  strip?: string;
  stripFrames?: number;
  /** Lines spoken with self.voiceover(...), in scene seconds. */
  narration?: { start: number; end: number; text: string }[];
  warning?: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
};

export type WorkerEvent =
  | { event: "ready"; manim: string }
  | { event: "progress"; job: number | null; animations?: number; time?: number | null; fraction?: number }
  | { event: "job"; job: number; method: string }
  | { event: "exit" };

export type ProjectSummary = {
  name: string;
  dir: string;
  modified: number;
  scenes: number;
  clips: number;
  thumbnail: string | null;
  preview: string | null;
};

export type UserTemplate = { id: string; title: string; description: string; thumbnail: string | null; scenes: string[]; created: number };

export type MusicTrack = { id: string; title: string; mood: string; bpm: number; duration: number; file: string; path: string };

export type FileChange = { path: string; status: "added" | "modified" | "deleted" };

export type PythonPackage = { name: string; version: string; summary: string };
export type PackagesResult = { ok: boolean; error?: string; log?: string; packages?: PythonPackage[]; dir?: string };

export type RootInfo = { path: string; default: string; local: string; onedrive: boolean };

export type Provider = "claude" | "codex" | "opencode" | "openrouter" | "vercel";

export type AgentStatus = {
  installed: boolean;
  version: string | null;
  signed_in: boolean;
  account: string | null;
  install_hint: string;
};

export type LatexStatus = { installed: boolean; complete: boolean; installing: boolean; path: string | null };

export type AgentEventPayload = {
  run: number;
  event?: Record<string, any>;
  text?: string;
  done?: boolean;
  code?: number | null;
};

export type CatalogModel = {
  name?: string;
  family?: string;
  context?: number;
  output?: number;
  input_cost?: number;
  output_cost?: number;
  reasoning?: boolean;
  tool_call?: boolean;
  attachment?: boolean;
  open_weights?: boolean;
  release_date?: string;
};
export type Catalog = Record<string, { name?: string; env?: string[]; models: Record<string, CatalogModel> }>;

/** A file picked or pasted in the composer, before it is copied into the project. */
export type PendingAttachment = {
  name: string;
  /** Path on disk (picked with the file dialog)… */
  source?: string;
  /** …or base64 data (pasted or dropped). */
  data?: string;
  /** Thumbnail for images. */
  preview?: string;
  image: boolean;
};

export type Voice = {
  id: string;
  name: string;
  category: string;
  description: string;
  labels: string[];
  preview_url: string | null;
};

export type BridgeCall = { call: number; tool: string; args: Record<string, any> };

export const api = {
  openProject: (path?: string) => invoke<ProjectInfo>("open_project", { path: path ?? null }),
  readText: (path: string) => invoke<string>("read_text", { path }),
  writeText: (path: string, contents: string) => invoke<void>("write_text", { path, contents }),
  createSceneFile: (dir: string, name: string) => invoke<string>("create_scene_file", { dir, name }),
  createFolder: (project: string, parent: string, name: string) => invoke<string>("create_folder", { project, parent, name }),
  renamePath: (project: string, path: string, name: string) => invoke<string>("rename_path", { project, path, name }),
  movePath: (project: string, path: string, into: string) => invoke<string>("move_path", { project, path, into }),
  trashPath: (project: string, path: string) => invoke<void>("trash_path", { project, path }),
  call: <T>(method: string, params: Record<string, unknown> = {}) =>
    invoke<T>("worker_call", { method, params }),
  restartWorker: () => invoke<void>("worker_restart"),
  onEvent: (fn: (e: WorkerEvent) => void) => listen<WorkerEvent>("worker-event", (e) => fn(e.payload)),
  onLog: (fn: (line: string) => void) => listen<string>("worker-log", (e) => fn(e.payload)),

  // Projects
  listProjects: () => invoke<{ root: string; recent: ProjectSummary[]; all: ProjectSummary[] }>("list_projects"),
  createProject: (name: string, template?: string) =>
    invoke<string>("create_project", { name, template: template ?? null }),
  importMedia: (projectDir: string, source: string) => invoke<string>("import_media", { projectDir, source }),
  renameProject: (dir: string, name: string) => invoke<string>("rename_project", { dir, name }),
  deleteProject: (dir: string) => invoke<void>("delete_project", { dir }),
  launchPath: () => invoke<string | null>("launch_path"),
  importFiles: (project: string, folder: string, sources: string[]) => invoke<string[]>("import_files", { project, folder, sources }),
  importFileData: (project: string, folder: string, name: string, data: string) =>
    invoke<string>("import_file_data", { project, folder, name, data }),
  checkpointCreate: (project: string) => invoke<string>("checkpoint_create", { project }),
  checkpointChanges: (project: string, id: string) => invoke<FileChange[]>("checkpoint_changes", { project, id }),
  checkpointRestore: (project: string, id: string) => invoke<FileChange[]>("checkpoint_restore", { project, id }),
  musicLibrary: () => invoke<{ license: string; tracks: MusicTrack[] }>("music_library"),
  pluginStartersDir: () => invoke<string>("plugin_starters_dir"),
  exportProjectZip: (project: string, dest: string, includeRenders = false) =>
    invoke<{ path: string; files: number; bytes: number }>("export_project_zip", { project, dest, includeRenders }),
  importProjectZip: (zipPath: string) => invoke<string>("import_project_zip", { zipPath }),
  saveUserTemplate: (project: string, name: string, description = "") => invoke<string>("save_user_template", { project, name, description }),
  listUserTemplates: () => invoke<UserTemplate[]>("list_user_templates"),
  deleteUserTemplate: (id: string) => invoke<void>("delete_user_template", { id }),
  manimglStatus: () => invoke<{ installed: boolean; version?: string | null }>("manimgl_status"),
  manimglInstall: () => invoke<PackagesResult>("manimgl_install"),
  manimglRemove: () => invoke<void>("manimgl_remove"),
  packagesList: () => invoke<PackagesResult>("packages_list"),
  packagesInstall: (spec: string) => invoke<PackagesResult>("packages_install", { spec }),
  packagesRemove: (name: string) => invoke<PackagesResult>("packages_remove", { name }),
  getProjectsRoot: () => invoke<RootInfo>("get_projects_root"),
  setProjectsRoot: (path: string | null) => invoke<RootInfo>("set_projects_root", { path }),
  forgetRecent: (dir: string) => invoke<void>("forget_recent", { dir }),

  // Assistants
  agentStatus: (provider: Provider) => invoke<AgentStatus>("agent_status", { provider }),
  agentModels: (provider: Provider) => invoke<string[]>("agent_models", { provider }),
  agentLogin: (provider: Provider) => invoke<void>("agent_login", { provider }),
  agentRun: (a: {
    provider: Provider;
    model: string | null;
    prompt: string;
    projectDir: string;
    session: string | null;
    instructions: string | null;
    files: string[];
    web: boolean;
    localFiles: boolean;
  }) => invoke<number>("agent_run", a),
  mcpShare: (enable: boolean) => invoke<{ python: string; server: string } | null>("mcp_share", { enable }),
  saveAttachment: (projectDir: string, source: string) => invoke<string>("save_attachment", { projectDir, source }),
  saveAttachmentData: (projectDir: string, name: string, data: string) =>
    invoke<string>("save_attachment_data", { projectDir, name, data }),
  modelsCatalog: (refresh = false) => invoke<Catalog>("models_catalog", { refresh }),
  setApiKey: (provider: string, key: string) => invoke<void>("set_api_key", { provider, key }),
  clearApiKey: (provider: string) => invoke<void>("clear_api_key", { provider }),
  apiKeyHint: (provider: string) => invoke<string | null>("api_key_hint", { provider }),

  // Voiceovers (ElevenLabs)
  voiceAccount: () => invoke<{ tier: string; used: number; limit: number } | null>("voice_account"),
  voiceList: () => invoke<Voice[]>("voice_list"),
  voiceGenerate: (a: {
    projectDir: string;
    text: string;
    voiceId: string;
    modelId?: string | null;
    name?: string | null;
    speed?: number | null;
    stability?: number | null;
  }) => invoke<string>("voice_generate", a),
  agentCancel: (run: number) => invoke<void>("agent_cancel", { run }),
  onAgentEvent: (fn: (e: AgentEventPayload) => void) => listen<AgentEventPayload>("agent-event", (e) => fn(e.payload)),
  onAgentLog: (fn: (e: { run: number; line: string }) => void) =>
    listen<{ run: number; line: string }>("agent-log", (e) => fn(e.payload)),
  onBridgeCall: (fn: (c: BridgeCall) => void) => listen<BridgeCall>("bridge-call", (e) => fn(e.payload)),
  bridgeReply: (call: number, result: unknown) => invoke<void>("bridge_reply", { call, result }),

  // LaTeX
  latexStatus: () => invoke<LatexStatus>("latex_status"),
  latexInstall: () => invoke<void>("latex_install"),
  onLatexProgress: (fn: (p: { stage: string; detail: string; fraction: number | null }) => void) =>
    listen<{ stage: string; detail: string; fraction: number | null }>("latex-progress", (e) => fn(e.payload)),
};

export function mediaUrl(path: string, version?: number): string {
  const url = convertFileSrc(path);
  return version ? `${url}?v=${version}` : url;
}

export function basename(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function joinPath(dir: string, name: string): string {
  return dir.replace(/[\\/]+$/, "") + "\\" + name;
}
