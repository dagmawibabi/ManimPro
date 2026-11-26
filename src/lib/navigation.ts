/** Opening projects: shared by the home page and the project switcher. */
import { goto } from "$app/navigation";
import { api, type PendingAttachment } from "./api";
import { studio } from "./studio.svelte";
import { assistant } from "./assistant.svelte";
import { voice } from "./voice.svelte";
import { ui } from "./ui.svelte";

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

/** Creates a project (blank or from a template) and opens it. */
export async function createAndEnter(name: string, template = "blank", opts: EnterOptions = {}) {
  const dir = await api.createProject(name, template);
  await enterProject(dir, { render: template !== "blank", ...opts });
  return dir;
}
