/** Opening projects: shared by the home page and the project switcher. */
import { goto } from "$app/navigation";
import { api, type PendingAttachment } from "./api";
import { studio } from "./studio.svelte";
import { assistant } from "./assistant.svelte";
import { voice } from "./voice.svelte";
import { ui } from "./ui.svelte";
import { settings } from "./settings.svelte";
import { joinPath } from "./api";

export type EnterOptions = { render?: boolean; prompt?: string; files?: PendingAttachment[] };

/** Opens a project folder in the editor; optionally renders or sends a first prompt. */
export async function enterProject(dir: string, opts: EnterOptions = {}) {
  await studio.openProject(dir);
  await assistant.loadChats(dir);
  voice.loadMeta();
  ui.sideTab = "project";
  ui.mainTab = opts.prompt ? "assistant" : "code";
  await goto("/editor");
  if (opts.prompt) {
    assistant.newChat();
    assistant.send(opts.prompt, opts.files ?? []);
  } else if (opts.render && studio.currentScene) {
    studio.renderCurrent();
  }
}

/** Creates a project folder with the default frame shape from Settings. */
export async function newProject(name: string, template = "blank") {
  const dir = await api.createProject(name, template);
  const aspect = settings.value.defaultAspect;
  if (aspect !== "16:9") await api.writeText(joinPath(dir, "project.json"), JSON.stringify({ version: 2, aspect }, null, 2));
  return dir;
}

/** Creates a project (blank or from a template) and opens it. */
export async function createAndEnter(name: string, template = "blank", opts: EnterOptions = {}) {
  const dir = await newProject(name, template);
  await enterProject(dir, { render: template !== "blank", ...opts });
  return dir;
}
