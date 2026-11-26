<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { studio } from "#lib/studio.svelte.ts";
  import { api } from "#lib/api.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";
  import FileTree from "./FileTree.svelte";
  import SceneBin from "./SceneBin.svelte";
  import AudioBin from "./AudioBin.svelte";

  const store = typeof localStorage !== "undefined" ? localStorage : null;
  let filesOpen = $state(store?.getItem("mp.filesOpen") !== "0");
  let tab = $state<"scenes" | "audio">((store?.getItem("mp.binTab") as "scenes" | "audio") || "scenes");
  let tree: FileTree | undefined = $state();
  let adding = $state(false);

  const sceneCount = $derived(studio.files.reduce((n, f) => n + (studio.scenes[f]?.length ?? 0), 0));
  const view = $derived(tab === "scenes" ? settings.value.sceneView : settings.value.audioView);

  function toggleFiles() {
    filesOpen = !filesOpen;
    store?.setItem("mp.filesOpen", filesOpen ? "1" : "0");
  }

  function setTab(t: "scenes" | "audio") {
    tab = t;
    store?.setItem("mp.binTab", t);
  }

  function setView(v: "grid" | "list") {
    settings.set(tab === "scenes" ? "sceneView" : "audioView", v);
  }

  function newItem(kind: "file" | "folder") {
    if (!filesOpen) toggleFiles();
    queueMicrotask(() => tree?.startNew(kind));
  }

  async function addAll() {
    adding = true;
    try {
      await studio.addAllScenes();
    } finally {
      adding = false;
    }
  }

  async function openFolder() {
    const dir = await open({ directory: true, title: "Open a project folder" });
    if (typeof dir === "string") await studio.openProject(dir);
  }

  async function importAudio() {
    const files = await open({
      multiple: true,
      title: "Import music or voiceovers",
      filters: [{ name: "Audio", extensions: ["mp3", "wav", "m4a", "aac", "ogg", "flac", "opus"] }],
    });
    if (!files || !studio.dir) return;
    for (const f of Array.isArray(files) ? files : [files]) {
      const path = await api.importMedia(studio.dir, f);
      if (!studio.audioFiles.includes(path)) studio.audioFiles = [...studio.audioFiles, path].sort();
    }
  }
</script>

<aside class="panel">
  <header>
    <div class="title">
      <span class="project" title={studio.dir ?? ""}>{studio.projectName || "No project"}</span>
      <span class="count">{studio.files.length} {studio.files.length === 1 ? "file" : "files"} · {sceneCount} {sceneCount === 1 ? "scene" : "scenes"} · {studio.audioFiles.length} audio</span>
    </div>
    <button class="icon-btn" title="Open another folder" aria-label="Open project folder" onclick={openFolder}>
      <Icon name="folder" />
    </button>
  </header>

  <div class="scroll">
    <!-- Files: collapsible tree, with new file / new folder on the header line -->
    <section>
      <div class="section-head">
        <button class="head" aria-expanded={filesOpen} onclick={toggleFiles}>
          <span class="chev" class:open={filesOpen}><Icon name="chevron" size={11} /></span>
          <span class="panel-title">Files</span>
          <span class="num">{studio.files.length}</span>
        </button>
        <div class="tools">
          <button class="icon-btn" title="New scene file" aria-label="New scene file" onclick={() => newItem("file")}><Icon name="filePlus" size={14} /></button>
          <button class="icon-btn" title="New folder" aria-label="New folder" onclick={() => newItem("folder")}><Icon name="folderPlus" size={14} /></button>
        </div>
      </div>
      {#if filesOpen}<FileTree bind:this={tree} />{/if}
    </section>

    <!-- Media: scenes or audio, each with its own grid / list view -->
    <section class="media">
      <div class="bar">
        <div class="tabs" role="tablist" aria-label="Media">
          <button role="tab" aria-selected={tab === "scenes"} class:on={tab === "scenes"} onclick={() => setTab("scenes")}>
            <Icon name="film" size={13} /> Scenes <span class="num">{sceneCount}</span>
          </button>
          <button role="tab" aria-selected={tab === "audio"} class:on={tab === "audio"} onclick={() => setTab("audio")}>
            <Icon name="music" size={13} /> Audio <span class="num">{studio.audioFiles.length}</span>
          </button>
        </div>
        <div class="views" role="radiogroup" aria-label="View">
          <button role="radio" aria-checked={view === "grid"} class:on={view === "grid"} title="Grid" aria-label="Grid view" onclick={() => setView("grid")}><Icon name="grid" size={13} /></button>
          <button role="radio" aria-checked={view === "list"} class:on={view === "list"} title="List" aria-label="List view" onclick={() => setView("list")}><Icon name="list" size={13} /></button>
        </div>
      </div>

      {#if tab === "scenes"}
        <div class="actions">
          <button class="action" disabled={!sceneCount || adding} onclick={addAll}>
            {#if adding}<span class="spin"></span>{:else}<Icon name="plus" size={13} />{/if}
            Add all scenes to timeline
          </button>
        </div>
        <SceneBin view={settings.value.sceneView} />
      {:else}
        <div class="actions">
          <button class="action primary" onclick={() => (ui.voiceOpen = true)}><Icon name="mic" size={13} /> Generate</button>
          <button class="action" onclick={importAudio}><Icon name="export" size={13} /> Import</button>
        </div>
        <AudioBin view={settings.value.audioView} />
      {/if}
    </section>
  </div>
</aside>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    background: var(--panel);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 12px 8px 6px 16px;
  }
  .title {
    display: grid;
    gap: 1px;
    min-width: 0;
  }
  .project {
    font-family: var(--font-display);
    font-size: 14px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .count {
    font-size: 11.5px;
    color: var(--faint);
  }
  .scroll {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 0 8px 14px;
  }
  section {
    padding-top: 6px;
  }
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 8px 0 6px;
    border-radius: 8px;
  }
  .head:hover {
    background: var(--panel-2);
  }
  .chev {
    display: grid;
    color: var(--faint);
    transition: transform 0.12s;
  }
  .chev.open {
    transform: rotate(90deg);
  }
  .num {
    font-size: 11px;
    color: var(--faint);
  }
  .tools {
    display: flex;
    gap: 2px;
  }
  .tools .icon-btn {
    width: 28px;
    height: 28px;
  }
  .media {
    margin-top: 8px;
    border-top: 1px solid var(--line);
    padding-top: 10px;
  }
  .bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .tabs,
  .views {
    display: flex;
    gap: 2px;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg);
  }
  .tabs button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 26px;
    padding: 0 10px;
    border-radius: 8px;
    color: var(--muted);
    font-size: 12.5px;
    font-weight: 500;
  }
  .tabs button.on {
    background: var(--raised);
    color: var(--text);
  }
  .tabs button.on .num {
    color: var(--muted);
  }
  .views button {
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    color: var(--faint);
  }
  .views button.on {
    background: var(--raised);
    color: var(--text);
  }
  .actions {
    display: flex;
    gap: 6px;
    margin: 10px 0;
  }
  .action {
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    flex: 1;
    height: 32px;
    padding: 0 10px;
    border-radius: 10px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    color: var(--muted);
    font-size: 12.5px;
    font-weight: 500;
  }
  .action:hover:not(:disabled) {
    color: var(--text);
    border-color: var(--line-strong);
  }
  .action:disabled {
    opacity: 0.5;
  }
  .action.primary {
    background: var(--accent-soft);
    border-color: transparent;
    color: var(--accent);
  }
  .action.primary:hover {
    background: color-mix(in srgb, var(--accent) 22%, transparent);
    color: var(--accent);
  }
  .spin {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--accent-soft);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
