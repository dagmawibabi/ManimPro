import { api, basename, joinPath, type AgentEventPayload, type AgentStatus, type FileChange, type PendingAttachment, type Provider } from "./api";
import { studio } from "./studio.svelte";
import { settings } from "./settings.svelte";
import "./voice.svelte"; // registers the voiceover tools for assistants

export type ItemKind = "user" | "assistant" | "tool" | "error" | "note" | "plan" | "changes";

export type Plan = { title: string; scenes: { file: string; scene: string; summary: string; seconds?: number }[] };

export type Item = {
  id: string;
  kind: ItemKind;
  text: string;
  status?: "running" | "ok" | "error" | "skipped";
  detail?: string;
  /** A fix the UI can offer next to an error. */
  action?: "login" | "latex";
  plan?: Plan;
  tool?: string;
  input?: Record<string, any>;
  /** Files attached to a user message (paths in the project). */
  files?: string[];
  /** "changes" items: what a run changed, and the checkpoint taken before it. */
  checkpoint?: string;
  changes?: FileChange[];
  reverted?: boolean;
};

export type Chat = {
  id: string;
  title: string;
  provider: Provider;
  /** CLI session id per provider, so a chat can be resumed. */
  sessions: Partial<Record<Provider, string>>;
  items: Item[];
  updated: number;
};

export const PROVIDERS: { id: Provider; name: string; plan: string; key?: boolean }[] = [
  { id: "claude", name: "Claude Code", plan: "Uses your Claude subscription" },
  { id: "codex", name: "Codex", plan: "Uses your ChatGPT plan" },
  { id: "opencode", name: "OpenCode", plan: "Uses your OpenCode providers" },
  { id: "openrouter", name: "OpenRouter", plan: "Uses your OpenRouter API key", key: true },
  { id: "vercel", name: "Vercel AI Gateway", plan: "Uses your AI Gateway API key", key: true },
];
export const isKeyed = (p: Provider) => !!PROVIDERS.find((x) => x.id === p)?.key;

const MODEL_LABELS: Record<string, string> = { opus: "Opus", sonnet: "Sonnet", haiku: "Haiku" };
export const modelLabel = (m: string) => MODEL_LABELS[m] ?? m;
export const providerName = (p: Provider) => PROVIDERS.find((x) => x.id === p)?.name ?? p;

const uid = () => Math.random().toString(36).slice(2, 10);
const store = typeof localStorage !== "undefined" ? localStorage : null;
const LOGIN_TROUBLE = /login expired|not logged in|please run \/login|re-?authenticate|invalid api key|oauth token/i;

/** Short, human description of a tool call; `running` uses the present tense. */
function describeTool(name: string, input: Record<string, any> = {}, running = false): string {
  const file = input.file_path ?? input.filePath ?? input.path ?? input.file;
  const short = name.replace(/^mcp__manimpro__|^manimpro_/, "");
  const f = file ? basename(String(file)) : "";
  if (running) {
    switch (short) {
      case "Write":
      case "write":
        return `Writing ${f || "code"}…`;
      case "Edit":
      case "edit":
      case "MultiEdit":
        return `Editing ${f || "code"}…`;
      case "Read":
      case "read":
        return `Reading ${f || "a file"}…`;
      case "render_scene":
        return `Rendering ${input.scene ?? "the scene"}…`;
      case "view_scene":
        return `Looking at ${input.scene ?? "the scene"}…`;
      case "view_timeline":
        return "Watching the timeline…";
      case "arrange_timeline":
        return "Arranging the timeline…";
      case "outline_video":
        return "Planning the scenes…";
      case "Glob":
      case "glob":
      case "Grep":
      case "grep":
        return "Looking through the project…";
    }
  }
  switch (short) {
    case "Read":
    case "read":
      return `Read ${file ? basename(String(file)) : "a file"}`;
    case "Edit":
    case "edit":
    case "MultiEdit":
      return `Edited ${file ? basename(String(file)) : "a file"}`;
    case "Write":
    case "write":
      return `Wrote ${file ? basename(String(file)) : "a file"}`;
    case "Glob":
    case "glob":
    case "Grep":
    case "grep":
    case "list":
      return "Looked through the project";
    case "render_scene":
      return `Rendered ${input.scene ?? "a scene"}`;
    case "view_scene":
      return `Looked at ${input.scene ?? "a scene"}`;
    case "view_timeline":
      return "Watched the timeline";
    case "add_to_timeline":
      return `Added ${input.scene ?? "a scene"} to the timeline`;
    case "list_scenes":
      return "Checked the scenes";
    case "get_timeline":
      return "Checked the timeline";
    case "remove_from_timeline":
      return "Removed a clip";
    case "clear_timeline":
      return "Cleared the timeline";
    case "outline_video":
      return "Planned the scenes";
    case "arrange_timeline":
      return `Arranged ${Array.isArray(input.scenes) ? input.scenes.length : ""} scenes on the timeline`.replace("  ", " ");
    case "TodoWrite":
    case "todowrite":
      return "Planned the steps";
    case "ToolSearch":
    case "toolsearch":
      return "Loaded its tools";
    case "list_voices":
      return "Checked the voices";
    case "generate_voiceover":
      return running ? "Recording a voiceover…" : "Recorded a voiceover";
    case "WebFetch":
    case "webfetch":
      return "Read a web page";
    default: {
      // CamelCase / snake_case → "Camel case"
      const words = short.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim().toLowerCase();
      return words ? words[0].toUpperCase() + words.slice(1) : short;
    }
  }
}

/** Which kind of step a tool is, for its icon in the chat. */
export function toolKind(name = ""): "write" | "read" | "search" | "render" | "plan" | "voice" | "other" {
  const n = name.replace(/^mcp__manimpro__|^manimpro_/, "").toLowerCase();
  if (/^(write|edit|multiedit)$/.test(n)) return "write";
  if (n === "read") return "read";
  if (/glob|grep|list$|search/.test(n)) return "search";
  if (/render|timeline|view_scene/.test(n)) return "render";
  if (/outline|todo/.test(n)) return "plan";
  if (/voice/.test(n)) return "voice";
  return "other";
}

class Assistant {
  provider = $state<Provider>((store?.getItem("mp.provider") as Provider) || "claude");
  models = $state<Record<string, string>>(JSON.parse(store?.getItem("mp.models") ?? "{}"));
  status = $state<Partial<Record<Provider, AgentStatus>>>({});
  modelLists = $state<Partial<Record<Provider, string[]>>>({});
  checking = $state(false);
  chats = $state<Chat[]>([]);
  activeId = $state<string | null>(null);
  run = $state<number | null>(null);
  #runChat = $state<string | null>(null);
  /** The chat a run belongs to. Set before the assistant process starts, cleared when it ends;
   *  while set, the project's files, scenes and that chat can't be deleted. */
  get runChatId() {
    return this.#runChat;
  }
  set runChatId(id: string | null) {
    this.#runChat = id;
    studio.locked = id !== null;
  }

  #dir: string | null = null;
  #logTail: string[] = [];
  #streaming: Item | null = null; // assistant text being streamed (Claude deltas)
  #toolItems = new Map<string, Item>();
  #sawError = false;
  #started = false;
  #runProvider: Provider = "claude";
  #rendered = false;
  #blocks = new Map<number, { id: string; json: string }>();
  #saveTimer: ReturnType<typeof setTimeout> | undefined;

  model = $derived(this.models[this.provider] ?? "");
  current = $derived(this.status[this.provider]);
  busy = $derived(this.run !== null || this.#runChat !== null);
  active = $derived(this.chats.find((c) => c.id === this.activeId) ?? null);
  items = $derived(this.active?.items ?? []);
  sortedChats = $derived([...this.chats].sort((a, b) => b.updated - a.updated));

  async init() {
    if (this.#started) return;
    this.#started = true;
    await api.onAgentEvent((e) => this.onEvent(e));
    await api.onAgentLog((e) => {
      if (e.run !== this.run) return;
      this.#logTail.push(e.line);
      if (this.#logTail.length > 30) this.#logTail.shift();
    });
    studio.onOutline = (plan) => {
      this.push({ kind: "plan", text: plan.title, plan });
      this.persist();
    };
    await this.refresh();
    // People sign in in another window; re-check when they come back.
    window.addEventListener("focus", () => {
      if (!this.busy && !this.checking) this.refresh();
    });
  }

  setProvider(p: Provider) {
    this.provider = p;
    store?.setItem("mp.provider", p);
    if (!this.status[p]) this.refresh(p);
  }

  setModel(m: string) {
    this.models = { ...this.models, [this.provider]: m };
    store?.setItem("mp.models", JSON.stringify(this.models));
  }

  async refresh(p: Provider = this.provider) {
    this.checking = true;
    try {
      const s = await api.agentStatus(p);
      this.status = { ...this.status, [p]: s };
      if (s.installed && !this.modelLists[p]) {
        api.agentModels(p).then((m) => (this.modelLists = { ...this.modelLists, [p]: m })).catch(() => {});
      }
    } finally {
      this.checking = false;
    }
  }

  async login() {
    if (isKeyed(this.provider)) {
      settings.show("assistant");
      return;
    }
    try {
      await api.agentLogin(this.provider);
      this.note(`Finish signing in to ${providerName(this.provider)} in the window that opened. ManimPro checks again when you come back.`);
    } catch (e) {
      this.error(String(e));
    }
  }

  // ------------------------------------------------------------------ chats
  /** Loads the chat history saved in the project (called when a project opens). */
  async loadChats(dir: string) {
    if (this.#dir === dir) return;
    this.#dir = dir;
    this.chats = [];
    this.activeId = null;
    try {
      const raw = JSON.parse(await api.readText(joinPath(dir, ".manimpro\\chats.json")));
      if (Array.isArray(raw?.chats)) {
        this.chats = raw.chats.map((c: Chat) => ({
          ...c,
          items: c.items.map((i) => (i.status === "running" ? { ...i, status: "ok" as const } : i)),
        }));
      }
    } catch {
      /* no history yet */
    }
    this.activeId = this.sortedChats[0]?.id ?? null;
  }

  private persist() {
    clearTimeout(this.#saveTimer);
    const dir = this.#dir;
    if (!dir) return;
    this.#saveTimer = setTimeout(() => {
      const data = { version: 1, chats: this.chats.slice(-50) };
      api.writeText(joinPath(dir, ".manimpro\\chats.json"), JSON.stringify(data));
    }, 500);
  }

  newChat() {
    this.activeId = null;
  }

  openChat(id: string) {
    this.activeId = id;
    const chat = this.active;
    if (chat && !this.busy) this.setProvider(chat.provider);
  }

  #checkpoint: string | null = null;

  /** Puts the project back the way it was before a run (its files and timeline). */
  async revert(itemId: string) {
    const item = this.items.find((i) => i.id === itemId);
    if (!item?.checkpoint || !studio.dir || this.busy) return;
    if (studio.dirty) await studio.save();
    await api.checkpointRestore(studio.dir, item.checkpoint);
    item.reverted = true;
    const file = studio.activeFile;
    await studio.openProject(studio.dir);
    if (file && studio.files.includes(file)) await studio.openFile(file);
    this.note("Undid the assistant's changes from this request. Files it created were moved to .manimpro/checkpoints.");
    this.persist();
  }

  deleteChat(id: string) {
    if (this.runChatId === id) return;
    this.chats = this.chats.filter((c) => c.id !== id);
    if (this.activeId === id) this.activeId = this.sortedChats[0]?.id ?? null;
    this.persist();
  }

  /** The chat a running assistant writes into (it keeps going if you switch chats). */
  private get target(): Item[] {
    const chat = this.chats.find((c) => c.id === (this.runChatId ?? this.activeId));
    return chat ? chat.items : [];
  }

  /** Sends a prompt to the selected assistant, working in the open project. */
  async send(prompt: string, attachments: PendingAttachment[] = []) {
    const text = prompt.trim();
    if ((!text && !attachments.length) || this.busy || !studio.dir) return;
    await this.loadChats(studio.dir);

    let chat = this.active;
    if (!chat) {
      chat = {
        id: uid(),
        title: text.length > 60 ? text.slice(0, 57) + "…" : text,
        provider: this.provider,
        sessions: {},
        items: [],
        updated: Date.now(),
      };
      this.chats.push(chat);
      this.activeId = chat.id;
      chat = this.chats[this.chats.length - 1];
    }

    // Slash commands belong to the CLIs' interactive mode; handle the useful ones here.
    if (text.startsWith("/")) {
      const cmd = text.split(/\s+/)[0].toLowerCase();
      chat.items.push({ id: uid(), kind: "user", text });
      if (cmd === "/login") await this.login();
      else if (cmd === "/new" || cmd === "/clear") this.newChat();
      else this.note("Slash commands aren't available here. Describe what you want in plain words.");
      this.persist();
      return;
    }

    if (studio.dirty) await studio.save();
    // Copy attachments into the project so every assistant can read them.
    const files: string[] = [];
    for (const a of attachments) {
      try {
        files.push(a.source ? await api.saveAttachment(studio.dir, a.source) : await api.saveAttachmentData(studio.dir, a.name, a.data ?? ""));
      } catch (e) {
        this.note(`Could not attach ${a.name}: ${e}`);
      }
    }
    const rel = (p: string) => p.slice(studio.dir!.length + 1).replaceAll("\\", "/");
    const prompt_ = files.length
      ? `${text || "See the attached files."}\n\nAttached files (in the project folder):\n${files.map((f) => `- ${rel(f)}`).join("\n")}`
      : text;
    chat.items.push({ id: uid(), kind: "user", text: text || "(attachments)", files });
    chat.updated = Date.now();
    chat.provider = this.provider;
    this.#logTail = [];
    this.#sawError = false;
    this.#streaming = null;
    this.#toolItems.clear();
    this.#runProvider = this.provider;
    this.#rendered = false;
    this.runChatId = chat.id;
    this.persist();
    // A copy of the project's files, so this run's edits can be undone.
    this.#checkpoint = await api.checkpointCreate(studio.dir).catch(() => null);
    try {
      this.run = await api.agentRun({
        provider: this.provider,
        model: this.model || null,
        prompt: prompt_,
        projectDir: studio.dir,
        session: chat.sessions[this.provider] ?? null,
        instructions: await this.instructionsWithPackages(),
        files,
        web: settings.value.agentWeb,
        localFiles: settings.value.agentLocalFiles,
      });
    } catch (e) {
      this.runChatId = null;
      this.error(String(e));
    }
  }

  /** Standing instructions plus which extra packages scenes can import. */
  private async instructionsWithPackages(): Promise<string | null> {
    const base = this.instructions();
    try {
      const [pk, gl] = await Promise.all([api.packagesList(), api.manimglStatus()]);
      const names = (pk.packages ?? []).map((p) => p.name);
      const extra = [
        names.length ? `Extra Python packages installed for scenes: ${names.join(", ")}.` : "",
        gl.installed ? "ManimGL is installed (files with `from manimlib import *` render with it)." : "",
      ].filter(Boolean).join(" ");
      return [base, extra].filter(Boolean).join("\n") || null;
    } catch {
      return base;
    }
  }

  private instructions(): string | null {
    const s = settings.value;
    const { id, w, h } = studio.aspectInfo;
    const u = studio.frameUnits();
    const frame =
      id === "16:9"
        ? ""
        : `This project's video frame is ${id} (${w >= h ? "landscape" : "portrait"}): the visible area is ` +
          `${u.width.toFixed(2)} units wide and ${u.height.toFixed(2)} units tall (config.frame_width / config.frame_height). ` +
          `Lay out and scale everything to fill that shape well, and keep every element inside it.`;
    const parts = [
      frame,
      s.multiSceneByDefault ? "" : "Keep the work in a single scene unless the user asks for more.",
      s.extraInstructions.trim(),
    ].filter(Boolean);
    return parts.length ? parts.join("\n") : null;
  }

  async stop() {
    if (this.run !== null) await api.agentCancel(this.run);
  }

  // --------------------------------------------------------------- events
  private push(item: Omit<Item, "id"> & { id?: string }) {
    const list = this.target;
    list.push({ id: uid(), ...item });
    return list[list.length - 1];
  }

  private note(text: string) {
    this.push({ kind: "note", text });
  }

  private error(text: string, action?: Item["action"]) {
    this.#sawError = true;
    this.push({ kind: "error", text, action });
  }

  private loginTrouble(text: string) {
    // Drop the assistant echo of the same message, then show one actionable error.
    const list = this.target;
    const last = list[list.length - 1];
    if (last?.kind === "assistant" && LOGIN_TROUBLE.test(last.text)) list.pop();
    this.error(`${providerName(this.#runProvider)} needs you to sign in again. (${text.trim()})`, "login");
    const st = this.status[this.#runProvider];
    if (st) this.status = { ...this.status, [this.#runProvider]: { ...st, signed_in: false } };
  }

  private say(text: string, id?: string) {
    if (!text.trim()) return;
    const existing = id ? this.target.find((i) => i.id === id) : undefined;
    if (existing) existing.text = text;
    else this.push({ id, kind: "assistant", text });
  }

  private toolStart(key: string, name: string, input?: Record<string, any>) {
    let item = this.#toolItems.get(key);
    if (!item) {
      if (/render_scene|add_to_timeline|arrange_timeline/.test(name)) this.#rendered = true;
      item = this.push({ kind: "tool", text: describeTool(name, input, true), status: "running", tool: name, input });
      this.#toolItems.set(key, item);
    } else if (input && Object.keys(input).length) {
      item.input = input;
      item.text = describeTool(name, input, item.status === "running");
    }
    return item;
  }

  /** Claude streams a tool call's arguments; show the file and lines as they arrive. */
  private toolStreaming(key: string, partialJson: string) {
    const item = this.#toolItems.get(key);
    if (!item || item.status !== "running" || !item.tool) return;
    const file = /"(?:file_path|filePath|path)"\s*:\s*"([^"]+)"/.exec(partialJson)?.[1];
    const body = /"(?:content|new_string)"\s*:\s*"/.exec(partialJson);
    const lines = body ? partialJson.slice(body.index).split("\\n").length : 0;
    const base = describeTool(item.tool, file ? { file_path: file.replace(/\\\\/g, "\\") } : {}, true).replace(/…$/, "");
    item.text = lines > 1 ? `${base} · ${lines} lines…` : `${base}…`;
  }

  private toolEnd(key: string, ok: boolean, detail?: string) {
    const item = this.#toolItems.get(key);
    if (!item) return;
    if (item.tool) item.text = describeTool(item.tool, item.input ?? {}, false);
    if (!ok && detail && /rejected permission|permission to use|not allowed|outside/i.test(detail)) {
      item.status = "skipped";
      item.detail = "Skipped: assistants may only use files inside this project.";
      return;
    }
    item.status = ok ? "ok" : "error";
    if (detail && ok) {
      item.detail = detail.length > 6000 ? detail.slice(0, 6000) + "\n…" : detail;
      return;
    }
    if (detail) {
      try {
        const parsed = JSON.parse(detail);
        if (parsed && typeof parsed === "object" && parsed.error) {
          item.detail = [parsed.error, parsed.hint].filter(Boolean).join("\n");
          if (parsed.latex_missing || /LaTeX is not installed/.test(parsed.error)) item.action = "latex";
          return;
        }
      } catch {
        /* plain text */
      }
      item.detail = detail.slice(0, 600);
      if (/LaTeX is not installed/.test(detail)) item.action = "latex";
    }
  }

  private saveSession(id: unknown) {
    const chat = this.chats.find((c) => c.id === this.runChatId);
    if (chat && typeof id === "string" && id) chat.sessions[this.#runProvider] = id;
  }

  onEvent(e: AgentEventPayload) {
    if (e.run !== this.run) return;
    if (e.done) {
      for (const item of this.#toolItems.values()) if (item.status === "running") item.status = "ok";
      if (e.code && e.code !== 0 && !this.#sawError) {
        const tail = this.#logTail.filter((l) => l.trim()).slice(-6).join("\n");
        if (LOGIN_TROUBLE.test(tail)) this.loginTrouble(tail.split("\n").pop() ?? "");
        else this.error(tail || `The assistant stopped (exit code ${e.code}).`);
      }
      const chat = this.chats.find((c) => c.id === this.runChatId);
      if (chat) chat.updated = Date.now();
      this.run = null;
      this.runChatId = null;
      this.persist();
      const cp = this.#checkpoint;
      this.#checkpoint = null;
      if (cp && chat && studio.dir) {
        api
          .checkpointChanges(studio.dir, cp)
          .then((changes) => {
            if (!changes.length) return;
            chat.items.push({ id: uid(), kind: "changes", text: "", checkpoint: cp, changes });
            this.persist();
          })
          .catch(() => {});
      }
      const rendered = this.#rendered;
      studio.refreshFromDisk().then(() => {
        // Show the result even when the assistant didn't render it itself.
        if (!rendered && !this.#sawError && settings.value.autoRenderAfterAssistant && studio.currentScene) {
          studio.renderCurrent();
        }
      });
      return;
    }
    const ev = e.event;
    if (!ev) return;
    if (this.#runProvider === "claude") this.claude(ev);
    else if (this.#runProvider === "codex") this.codex(ev);
    else this.opencode(ev);
  }

  private claude(ev: Record<string, any>) {
    switch (ev.type) {
      case "system":
        if (ev.subtype === "init") this.saveSession(ev.session_id);
        break;
      case "stream_event": {
        const s = ev.event ?? {};
        if (s.type === "message_start") {
          this.#streaming = null;
          this.#blocks.clear();
        }
        // A tool call starts streaming: show it right away ("Writing scenes.py…").
        if (s.type === "content_block_start" && s.content_block?.type === "tool_use") {
          this.#blocks.set(s.index, { id: s.content_block.id, json: "" });
          this.toolStart(s.content_block.id, s.content_block.name, {});
          this.#streaming = null;
        }
        if (s.type === "content_block_delta" && s.delta?.type === "input_json_delta") {
          const b = this.#blocks.get(s.index);
          if (b) {
            b.json += s.delta.partial_json ?? "";
            this.toolStreaming(b.id, b.json);
          }
        }
        if (s.type === "content_block_delta" && s.delta?.type === "text_delta") {
          if (!this.#streaming) this.#streaming = this.push({ kind: "assistant", text: "" });
          this.#streaming.text += s.delta.text;
        }
        break;
      }
      case "assistant":
        for (const b of ev.message?.content ?? []) {
          if (b.type === "text" && !this.#streaming) this.say(b.text);
          if (b.type === "tool_use") this.toolStart(b.id, b.name, b.input);
        }
        this.#streaming = null;
        break;
      case "user":
        for (const b of ev.message?.content ?? []) {
          if (b.type === "tool_result") {
            const detail = Array.isArray(b.content) ? b.content.map((c: any) => c.text ?? "").join("\n") : String(b.content ?? "");
            this.toolEnd(b.tool_use_id, !b.is_error && !/"ok":\s*false/.test(detail), detail || undefined);
          }
        }
        break;
      case "result": {
        this.saveSession(ev.session_id);
        const text = typeof ev.result === "string" ? ev.result : "";
        if (LOGIN_TROUBLE.test(text)) this.loginTrouble(text);
        else if (ev.is_error || (ev.subtype && ev.subtype !== "success")) {
          this.error(text || `The assistant stopped: ${ev.subtype}.`);
        }
        break;
      }
    }
  }

  private codex(ev: Record<string, any>) {
    switch (ev.type) {
      case "thread.started":
        this.saveSession(ev.thread_id);
        break;
      case "item.started":
      case "item.updated":
      case "item.completed": {
        const it = ev.item ?? {};
        const done = ev.type === "item.completed";
        if (it.type === "agent_message") {
          if (done) this.say(it.text ?? "", it.id);
        } else if (it.type === "mcp_tool_call") {
          this.toolStart(it.id, it.tool ?? "tool", it.arguments ?? {});
          if (done) {
            const out = it.error?.message ?? (it.result ? JSON.stringify(it.result, null, 1) : undefined);
            this.toolEnd(it.id, it.status !== "failed", out);
          }
        } else if (it.type === "file_change") {
          const files = (it.changes ?? []).map((c: any) => basename(String(c.path ?? ""))).filter(Boolean);
          this.toolStart(it.id, "Edit", { file_path: files.join(", ") || undefined });
          if (done) this.toolEnd(it.id, it.status !== "failed");
        } else if (it.type === "command_execution") {
          this.toolStart(it.id, `Ran ${String(it.command ?? "a command").slice(0, 60)}`);
          if (done) this.toolEnd(it.id, (it.exit_code ?? 0) === 0, it.aggregated_output ?? undefined);
        } else if (it.type === "error") {
          this.error(it.message ?? "Codex reported an error.");
        }
        break;
      }
      case "turn.failed": {
        const msg = ev.error?.message ?? "Codex could not finish the task.";
        if (LOGIN_TROUBLE.test(msg)) this.loginTrouble(msg);
        else this.error(msg);
        break;
      }
      case "error":
        this.error(ev.message ?? "Codex reported an error.");
        break;
    }
  }

  private opencode(ev: Record<string, any>) {
    this.saveSession(ev.sessionID);
    const part = ev.part ?? {};
    switch (ev.type) {
      case "text":
        this.say(part.text ?? "", part.id);
        break;
      case "tool_use": {
        const key = part.callID ?? part.id;
        const state = part.state ?? {};
        this.toolStart(key, part.tool ?? "tool", state.input ?? {});
        if (state.status === "completed") {
          const out = String(state.output ?? "");
          this.toolEnd(key, !/"ok":\s*false/.test(out), out || undefined);
        }
        if (state.status === "error") this.toolEnd(key, false, state.error ?? state.output);
        break;
      }
      case "error": {
        const msg = ev.error?.data?.message ?? ev.error?.message ?? "OpenCode reported an error.";
        if (LOGIN_TROUBLE.test(msg)) this.loginTrouble(msg);
        else this.error(msg);
        break;
      }
    }
  }
}

export const assistant = new Assistant();
