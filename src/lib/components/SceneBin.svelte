<script lang="ts">
  import { studio, sceneKey } from "#lib/studio.svelte.ts";
  import { basename, mediaUrl } from "#lib/api.ts";
  import { shortTime } from "#lib/time.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";
  import PythonIcon from "./PythonIcon.svelte";
  import ContextMenu, { type MenuItem } from "./ContextMenu.svelte";
  import { ask } from "@tauri-apps/plugin-dialog";
  import { revealItemInDir } from "@tauri-apps/plugin-opener";
  import type { SceneInfo } from "#lib/api.ts";

  let menu = $state<{ x: number; y: number; items: MenuItem[] } | null>(null);
  let renaming = $state<{ file: string; scene: string; value: string } | null>(null);
  let error = $state<string | null>(null);

  async function attempt(fn: () => Promise<unknown>) {
    error = null;
    try {
      await fn();
    } catch (e) {
      error = (e as { message?: string }).message ?? String(e);
    }
  }

  function sceneMenu(e: MouseEvent, file: string, s: SceneInfo) {
    e.preventDefault();
    const key = sceneKey(file, s.name);
    const r = studio.renders[key];
    menu = {
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: "Open code", icon: "file", action: () => select(file, s.name, s.line) },
        { label: "Play", icon: "play", disabled: !r, action: () => studio.showSource(key) },
        { label: r ? "Render again" : "Render", icon: "render", disabled: !!studio.job, action: () => render(file, s.name) },
        { label: "Render at 1080p", icon: "bolt", disabled: !!studio.job, action: () => studio.render(file, s.name, "high", true) },
        { label: "Add to timeline", icon: "plus", action: () => studio.addToTimeline(file, s.name) },
        "separator",
        { label: "Rename", icon: "pencil", disabled: studio.locked, action: () => (renaming = { file, scene: s.name, value: s.name }) },
        { label: "Duplicate", icon: "copy", action: () => attempt(() => studio.duplicateScene(file, s.name)) },
        { label: "Copy name", icon: "copy", action: () => navigator.clipboard.writeText(s.name) },
        { label: "Show video in folder", icon: "reveal", disabled: !r, action: () => r && revealItemInDir(r.video) },
        "separator",
        { label: "Delete scene", icon: "trash", danger: true, disabled: studio.locked, hint: studio.locked ? "Not while the assistant is working" : undefined, action: () => removeScene(file, s.name) },
      ],
    };
  }

  async function removeScene(file: string, scene: string) {
    const clips = studio.clips.filter((c) => c.file === file && c.scene === scene).length;
    const msg = `Delete the ${scene} class from ${basename(file)}?` + (clips ? ` Its ${clips === 1 ? "clip" : `${clips} clips`} on the timeline will be removed too.` : "");
    if (!(await ask(msg, { title: "Delete scene", kind: "warning" }))) return;
    await attempt(() => studio.deleteScene(file, scene));
  }

  async function commitRename() {
    const r = renaming;
    renaming = null;
    if (r && r.value.trim() && r.value.trim() !== r.scene) await attempt(() => studio.renameScene(r.file, r.scene, r.value.trim()));
  }

  function focusSelect(el: HTMLInputElement) {
    el.focus();
    el.select();
  }

  let { view }: { view: "grid" | "list" } = $props();

  /** Every scene in the project, grouped by file (the open file first). */
  const groups = $derived(
    [...studio.files]
      .sort((a, b) => (a === studio.activeFile ? -1 : b === studio.activeFile ? 1 : a.localeCompare(b)))
      .map((file) => ({ file, scenes: studio.scenes[file] ?? [] }))
      .filter((g) => g.scenes.length),
  );

  function relative(file: string) {
    return studio.dir ? file.slice(studio.dir.length + 1) : basename(file);
  }

  function dragScene(e: DragEvent, file: string, scene: string) {
    e.dataTransfer?.setData("application/x-manim-scene", sceneKey(file, scene));
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "copy";
  }

  /** Jump to the scene's code; show its render if there is one. */
  async function select(file: string, scene: string, line: number) {
    if (file !== studio.activeFile) await studio.openFile(file);
    ui.mainTab = "code";
    studio.goToLine(line);
    const key = sceneKey(file, scene);
    if (studio.renders[key]) studio.showSource(key);
  }

  async function render(file: string, scene: string) {
    if (file === studio.activeFile) return studio.renderCurrent(scene);
    await studio.render(file, scene, studio.previewQuality, true);
  }
</script>

{#if menu}<ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => (menu = null)} />{/if}
{#if error}<p class="error" role="alert">{error}</p>{/if}

{#if !groups.length}
  <p class="tip">No scenes yet. In the editor, type <code>scene</code> and press Tab, or ask the assistant.</p>
{/if}

{#each groups as g (g.file)}
  {#if groups.length > 1}<div class="group"><PythonIcon size={12} /> {relative(g.file)}</div>{/if}
  <div class={view}>
    {#each g.scenes as s (s.name)}
      {@const key = sceneKey(g.file, s.name)}
      {@const r = studio.renders[key]}
      {@const busy = studio.job?.kind === "render" && studio.job.label === s.name}
      <div
        class="card"
        class:current={g.file === studio.activeFile && studio.currentScene?.name === s.name}
        class:showing={studio.sourceKey === key && studio.viewerMode === "source"}
        draggable="true"
        role="listitem"
        ondragstart={(e) => dragScene(e, g.file, s.name)}
        oncontextmenu={(e) => sceneMenu(e, g.file, s)}
      >
        <button class="thumb" aria-label="Open {s.name}" onclick={() => select(g.file, s.name, s.line)}>
          {#if r?.thumb}
            <img src={mediaUrl(r.thumb, r.version)} alt="" loading="lazy" />
          {:else}
            <span class="empty"><Icon name="film" size={view === "grid" ? 16 : 13} />{#if view === "grid"}<span>{r ? "Rendered" : "Not rendered"}</span>{/if}</span>
          {/if}
          {#if r && view === "grid"}<span class="dur">{shortTime(r.duration)}</span>{/if}
          {#if busy}<span class="busy"><span class="spinner"></span></span>{/if}
        </button>
        {#if renaming?.file === g.file && renaming.scene === s.name}
          <input
            class="rename"
            aria-label="New scene name"
            bind:value={renaming.value}
            use:focusSelect
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename();
              if (e.key === "Escape") renaming = null;
            }}
            onblur={commitRename}
          />
        {:else}
        <button class="label" onclick={() => select(g.file, s.name, s.line)}>
          <span class="scene-name">{s.name}</span>
          <span class="sub">{r ? `${shortTime(r.duration)} · ${r.height}p` : "Not rendered"}{view === "list" ? ` · line ${s.line}` : ""}</span>
        </button>
        {/if}
        <div class="actions">
          {#if r}<button class="pill" title="Play" aria-label="Play {s.name}" onclick={() => studio.showSource(key)}><Icon name="play" size={11} /></button>{/if}
          <button class="pill" title="Render" aria-label="Render {s.name}" disabled={!!studio.job} onclick={() => render(g.file, s.name)}><Icon name="render" size={12} /></button>
          <button class="pill" title="Add to timeline" aria-label="Add {s.name} to timeline" onclick={() => studio.addToTimeline(g.file, s.name)}><Icon name="plus" size={12} /></button>
        </div>
      </div>
    {/each}
  </div>
{/each}

<style>
  .rename {
    min-width: 0;
    height: 26px;
    margin: 2px 4px;
    padding: 0 8px;
    border-radius: 8px;
    font-size: 12px;
    user-select: text;
  }
  .error {
    margin: 6px 8px;
    color: #f3c7c3;
    font-size: 12px;
  }
  .group {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 10px 8px 6px;
    font-size: 11.5px;
    color: var(--faint);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 10px;
  }
  .list {
    display: grid;
    gap: 2px;
  }
  .card {
    position: relative;
    border-radius: 14px;
    cursor: grab;
  }
  .grid .card {
    display: grid;
    gap: 6px;
    padding: 6px;
  }
  .list .card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 6px;
    border-radius: 11px;
  }
  .card:hover,
  .card.showing {
    background: var(--panel-2);
  }
  .thumb {
    position: relative;
    display: grid;
    place-items: center;
    aspect-ratio: 16 / 9;
    border-radius: 10px;
    overflow: hidden;
    isolation: isolate;
    background: #0a0a0b;
    color: var(--faint);
  }
  .list .thumb {
    flex: none;
    width: 64px;
    border-radius: 7px;
  }
  .thumb::after {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: inherit;
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.06);
    pointer-events: none;
  }
  .card.showing .thumb::after {
    box-shadow: inset 0 0 0 2px var(--accent);
  }
  .card.current .thumb::after {
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .empty {
    display: grid;
    justify-items: center;
    gap: 4px;
    font-size: 10.5px;
  }
  .dur {
    position: absolute;
    right: 5px;
    bottom: 5px;
    padding: 1px 6px;
    border-radius: 6px;
    background: rgb(0 0 0 / 0.7);
    color: var(--text);
    font-family: var(--mono);
    font-size: 10.5px;
  }
  .busy {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.55);
  }
  .spinner {
    width: 16px;
    height: 16px;
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
  .label {
    display: grid;
    gap: 1px;
    padding: 0 2px;
    text-align: left;
    min-width: 0;
    flex: 1;
  }
  .scene-name {
    font-weight: 600;
    font-size: 12.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sub {
    font-size: 11px;
    color: var(--faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  /* Actions float over the preview (grid) or sit at the row's end (list) on hover. */
  .actions {
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.12s;
  }
  .grid .actions {
    position: absolute;
    top: 11px;
    left: 11px;
  }
  .card:hover .actions,
  .card:focus-within .actions {
    opacity: 1;
  }
  .pill {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: rgb(12 12 14 / 0.82);
    backdrop-filter: blur(4px);
    color: var(--text);
  }
  .list .pill {
    background: var(--raised);
  }
  .pill:hover:not(:disabled) {
    background: var(--accent);
    color: var(--accent-ink);
  }
  .pill:disabled {
    opacity: 0.4;
  }
  .tip {
    margin: 4px 8px 0;
    color: var(--faint);
    font-size: 12px;
    line-height: 1.5;
  }
  code {
    font-family: var(--mono);
    color: var(--muted);
  }
</style>
