<script lang="ts">
  import { tick } from "svelte";
  import { goto } from "$app/navigation";
  import { open as openDialog } from "@tauri-apps/plugin-dialog";
  import { api, mediaUrl, type ProjectSummary } from "#lib/api.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import { enterProject, createAndEnter } from "#lib/navigation.ts";
  import templates from "#lib/templates.json";
  import Icon from "./Icon.svelte";

  let open = $state(false);
  let button: HTMLButtonElement;
  let pop: HTMLDivElement | undefined = $state();
  let recent = $state<ProjectSummary[]>([]);
  let busy = $state<string | null>(null);
  let error = $state<string | null>(null);
  let pos = $state({ left: 0, top: 0 });

  const others = $derived(recent.filter((p) => p.dir.toLowerCase() !== studio.dir?.toLowerCase()).slice(0, 10));
  const gallery = templates.filter((t) => t.id !== "blank");

  async function toggle() {
    if (open) return (open = false);
    const zoom = parseFloat(getComputedStyle(document.documentElement).zoom || "1") || 1;
    const r = button.getBoundingClientRect();
    pos = { left: r.left / zoom, top: r.bottom / zoom + 6 };
    open = true;
    error = null;
    api.listProjects().then((l) => (recent = l.recent)).catch(() => {});
    await tick();
    pop?.focus();
  }

  async function run(key: string, fn: () => Promise<unknown>) {
    busy = key;
    error = null;
    try {
      if (studio.dirty) await studio.save();
      await fn();
      open = false;
    } catch (e) {
      error = String(e);
    } finally {
      busy = null;
    }
  }

  async function openFolder() {
    const dir = await openDialog({ directory: true, title: "Open a project folder" });
    if (typeof dir === "string") await run("folder", () => enterProject(dir));
  }

  function ago(ms: number) {
    const s = (Date.now() - ms) / 1000;
    if (s < 3600) return `${Math.max(1, Math.floor(s / 60))} min ago`;
    if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
    return `${Math.floor(s / 86400)} d ago`;
  }

  function outside(e: PointerEvent) {
    if (open && !pop?.contains(e.target as Node) && !button.contains(e.target as Node)) open = false;
  }
</script>

<svelte:window onpointerdown={outside} onkeydown={(e) => open && e.key === "Escape" && (open = false)} />

<button bind:this={button} class="trigger" class:open aria-haspopup="menu" aria-expanded={open} onclick={toggle} title="Switch project">
  <span class="name">{studio.projectName}</span>
  <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5 5 6.5 8 3.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg>
</button>

{#if open}
  <div bind:this={pop} class="pop" role="menu" tabindex="-1" style:left="{pos.left}px" style:top="{pos.top}px">
    <div class="cols">
      <div class="left">
        <div class="actions">
          <button class="action" role="menuitem" disabled={!!busy} onclick={() => run("new", () => createAndEnter("Untitled"))}>
            <span class="tile accent">{#if busy === "new"}<span class="spin"></span>{:else}<Icon name="plus" size={15} />{/if}</span>
            <span class="text"><strong>New project</strong><span>Start from a blank scene</span></span>
          </button>
          <button class="action" role="menuitem" disabled={!!busy} onclick={openFolder}>
            <span class="tile"><Icon name="folder" size={15} /></span>
            <span class="text"><strong>Open folder…</strong><span>Any folder of Manim scenes</span></span>
          </button>
        </div>
        <div class="label">Recent</div>
        <div class="list">
          {#each others as p (p.dir)}
            <button class="row" role="menuitem" disabled={!!busy} onclick={() => run(p.dir, () => enterProject(p.dir))}>
              <span class="thumb">{#if p.thumbnail}<img src={mediaUrl(p.thumbnail, p.modified)} alt="" />{:else}<Icon name="film" size={13} />{/if}</span>
              <span class="text"><strong>{p.name}</strong><span>{ago(p.modified)} · {p.scenes} {p.scenes === 1 ? "scene" : "scenes"}</span></span>
              {#if busy === p.dir}<span class="spin"></span>{/if}
            </button>
          {:else}
            <p class="none">Projects you open show up here.</p>
          {/each}
        </div>
      </div>

      <div class="right">
        <div class="label">Start from a template</div>
        <div class="grid">
          {#each gallery as t (t.id)}
            <button class="card" role="menuitem" disabled={!!busy} onclick={() => run(t.id, () => createAndEnter(t.title, t.id))}>
              <span class="preview">
                {#if t.thumbnail}<img src={t.thumbnail} alt="" loading="lazy" />{:else}<Icon name="film" size={16} />{/if}
                {#if busy === t.id}<span class="busy"><span class="spin"></span></span>{/if}
              </span>
              <span class="card-title">{t.title}</span>
              <span class="card-sub">{t.category}{t.scenes.length > 1 ? ` · ${t.scenes.length} scenes` : ""}</span>
            </button>
          {/each}
        </div>
      </div>
    </div>

    <footer>
      {#if error}<p class="error">{error}</p>{/if}
      <button class="home" role="menuitem" onclick={() => { open = false; goto("/"); }}>
        <Icon name="home" size={14} /> All projects
      </button>
    </footer>
  </div>
{/if}

<style>
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    max-width: 320px;
    height: 32px;
    padding: 0 10px;
    border-radius: 10px;
    font-weight: 600;
    transition: background 0.12s;
  }
  .trigger:hover,
  .trigger.open {
    background: var(--raised);
  }
  .trigger svg {
    flex: none;
    color: var(--muted);
  }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pop {
    position: fixed;
    z-index: 120;
    display: flex;
    flex-direction: column;
    width: min(780px, calc(100vw - 32px));
    height: min(560px, calc(100vh - 90px));
    border-radius: 20px;
    background: #1b1b1e;
    border: 1px solid var(--line-strong);
    box-shadow: 0 26px 70px rgb(0 0 0 / 0.65);
    outline: none;
    overflow: hidden;
    animation: appear 0.12s ease-out;
  }
  @keyframes appear {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
  }
  .cols {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 290px 1fr;
  }
  .left,
  .right {
    min-height: 0;
    overflow: auto;
    padding: 10px;
  }
  .left {
    border-right: 1px solid var(--line);
  }
  .actions {
    display: grid;
    gap: 2px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--line);
  }
  .action,
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 8px;
    border-radius: 12px;
    text-align: left;
  }
  .action:hover:not(:disabled),
  .row:hover:not(:disabled) {
    background: var(--raised);
  }
  .tile {
    flex: none;
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: var(--panel);
    color: var(--muted);
  }
  .tile.accent {
    background: var(--accent-soft);
    color: var(--accent);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 1px;
  }
  .text strong {
    font-size: 12.5px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .text span {
    font-size: 11.5px;
    color: var(--faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .label {
    padding: 12px 8px 6px;
    font-size: 11px;
    font-weight: 600;
    color: var(--faint);
  }
  .right .label {
    padding-top: 4px;
  }
  .list {
    display: grid;
    gap: 2px;
  }
  .thumb {
    flex: none;
    display: grid;
    place-items: center;
    width: 64px;
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    overflow: hidden;
    background: #0a0a0b;
    color: var(--faint);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.06);
  }
  .thumb img,
  .preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 10px;
  }
  .card {
    display: grid;
    gap: 4px;
    padding: 6px;
    border-radius: 14px;
    text-align: left;
  }
  .card:hover:not(:disabled) {
    background: var(--raised);
  }
  .preview {
    position: relative;
    display: grid;
    place-items: center;
    aspect-ratio: 16 / 9;
    border-radius: 10px;
    overflow: hidden;
    background: #0a0a0b;
    color: var(--faint);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.06);
  }
  .busy {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgb(0 0 0 / 0.55);
  }
  .card-title {
    margin-top: 2px;
    padding: 0 2px;
    font-size: 12.5px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .card-sub {
    padding: 0 2px;
    font-size: 11.5px;
    color: var(--faint);
  }
  .none {
    margin: 4px 8px;
    color: var(--faint);
    font-size: 12px;
  }
  footer {
    flex: none;
    display: grid;
    gap: 6px;
    padding: 10px;
    border-top: 1px solid var(--line);
  }
  .home {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 40px;
    border-radius: 12px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    color: var(--text);
    font-size: 13px;
    font-weight: 500;
  }
  .home:hover {
    background: var(--raised);
    border-color: var(--line-strong);
  }
  .spin {
    flex: none;
    width: 14px;
    height: 14px;
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
  .error {
    margin: 0 4px;
    color: #f3c7c3;
    font-size: 12px;
  }
</style>
