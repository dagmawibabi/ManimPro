<script lang="ts">
  import { onDestroy } from "svelte";
  import { ask } from "@tauri-apps/plugin-dialog";
  import { revealItemInDir } from "@tauri-apps/plugin-opener";
  import { studio } from "#lib/studio.svelte.ts";
  import { basename, mediaUrl } from "#lib/api.ts";
  import { shortTime } from "#lib/time.ts";
  import Icon from "./Icon.svelte";
  import ContextMenu, { type MenuItem } from "./ContextMenu.svelte";

  let { view }: { view: "grid" | "list" } = $props();

  let player: HTMLAudioElement | null = null;
  let playing = $state<string | null>(null);
  let menu = $state<{ x: number; y: number; items: MenuItem[] } | null>(null);
  let renaming = $state<{ path: string; value: string } | null>(null);
  let error = $state<string | null>(null);

  // Waveforms and lengths load lazily for files on screen.
  $effect(() => {
    for (const p of studio.audioFiles) if (!studio.waveforms[p]) studio.loadWaveform(p);
  });

  onDestroy(() => player?.pause());

  function folderOf(path: string) {
    const rel = studio.dir ? path.slice(studio.dir.length + 1) : path;
    const parts = rel.split("\\");
    return parts.length > 2 ? parts.slice(1, -1).join("/") : "";
  }

  function toggle(path: string) {
    if (playing === path && player) {
      player.pause();
      playing = null;
      return;
    }
    player?.pause();
    player = new Audio(mediaUrl(path));
    player.onended = () => (playing = null);
    player.play().then(() => (playing = path)).catch(() => (playing = null));
  }

  function wave(peaks: number[] | undefined, n = 60) {
    if (!peaks?.length) return "";
    const step = peaks.length / n;
    let d = "";
    for (let i = 0; i < n; i++) {
      let m = 0;
      for (let j = Math.floor(i * step); j < Math.floor((i + 1) * step); j++) m = Math.max(m, peaks[j] ?? 0);
      const h = Math.max(1, m * 44);
      const x = (i + 0.5) * (100 / n);
      d += `M${x.toFixed(2)} ${50 - h}V${50 + h}`;
    }
    return d;
  }

  async function remove(path: string) {
    if (!(await ask(`Move “${basename(path)}” to the Recycle Bin?`, { title: "Delete audio", kind: "warning" }))) return;
    if (playing === path) player?.pause();
    try {
      await studio.trashPath(path);
    } catch (e) {
      error = String(e);
    }
  }

  async function commitRename() {
    const r = renaming;
    renaming = null;
    if (!r || !r.value.trim()) return;
    try {
      await studio.renamePath(r.path, r.value.trim());
    } catch (e) {
      error = String(e);
    }
  }

  function itemMenu(e: MouseEvent, path: string) {
    e.preventDefault();
    menu = {
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: playing === path ? "Pause" : "Play", icon: playing === path ? "pauseFill" : "play", action: () => toggle(path) },
        { label: "Add to timeline at playhead", icon: "plus", action: () => studio.placeAudio(path) },
        "separator",
        { label: "Rename", icon: "pencil", action: () => (renaming = { path, value: basename(path).replace(/\.[^.]+$/, "") }) },
        { label: "Show in folder", icon: "reveal", action: () => revealItemInDir(path) },
        "separator",
        { label: "Delete", icon: "trash", danger: true, action: () => remove(path) },
      ],
    };
  }

  function dragAudio(e: DragEvent, path: string) {
    e.dataTransfer?.setData("application/x-mp-audio", path);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "copy";
  }

  function focusSelect(el: HTMLInputElement) {
    el.focus();
    el.select();
  }
</script>

{#if menu}<ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => (menu = null)} />{/if}

{#if !studio.audioFiles.length}
  <p class="tip">Music and voiceovers you import or generate appear here.</p>
{:else}
  <div class={view}>
    {#each studio.audioFiles as path (path)}
      {@const dur = studio.audioDurations[path]}
      {@const sub = folderOf(path)}
      <div class="item" class:playing={playing === path} role="listitem" draggable="true" ondragstart={(e) => dragAudio(e, path)} oncontextmenu={(e) => itemMenu(e, path)}>
        <button class="play" aria-label={playing === path ? "Pause" : `Play ${basename(path)}`} onclick={() => toggle(path)}>
          {#if view === "grid"}
            <svg class="wave" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><path d={wave(studio.waveforms[path])} /></svg>
          {/if}
          <span class="icon"><Icon name={playing === path ? "pauseFill" : "play"} size={view === "grid" ? 13 : 11} /></span>
        </button>
        {#if renaming?.path === path}
          <input
            class="rename"
            use:focusSelect
            bind:value={renaming.value}
            aria-label="New name"
            onkeydown={(e) => {
              if (e.key === "Enter") commitRename();
              if (e.key === "Escape") renaming = null;
            }}
            onblur={commitRename}
          />
        {:else}
          <div class="meta">
            <span class="name" title={basename(path)}>{basename(path).replace(/\.[^.]+$/, "")}</span>
            <span class="sub">{dur ? shortTime(dur) : "…"}{sub ? ` · ${sub}` : ""}</span>
          </div>
        {/if}
        <button class="add" title="Add to timeline at playhead" aria-label="Add {basename(path)} to timeline" onclick={() => studio.placeAudio(path)}>
          <Icon name="plus" size={12} />
        </button>
      </div>
    {/each}
  </div>
{/if}
{#if error}<p class="error" role="alert">{error}</p>{/if}

<style>
  .list {
    display: grid;
    gap: 2px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(124px, 1fr));
    gap: 10px;
  }
  .item {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 6px;
    border-radius: 11px;
    cursor: grab;
  }
  .grid .item {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    padding: 6px;
    border-radius: 14px;
  }
  .item:hover,
  .item.playing {
    background: var(--panel-2);
  }
  .play {
    position: relative;
    flex: none;
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: #213021;
    color: #9fd88a;
  }
  .grid .play {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
    border-radius: 10px;
    background: #141c14;
    overflow: hidden;
  }
  .wave {
    position: absolute;
    inset: 14% 6%;
    width: 88%;
    height: 72%;
  }
  .wave path {
    stroke: #83c167;
    stroke-width: 1;
    opacity: 0.7;
    vector-effect: non-scaling-stroke;
  }
  .grid .icon {
    position: relative;
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: rgb(12 12 14 / 0.75);
    color: var(--text);
    opacity: 0;
    transition: opacity 0.12s;
  }
  .grid .item:hover .icon,
  .grid .item.playing .icon {
    opacity: 1;
  }
  .meta {
    display: grid;
    gap: 1px;
    flex: 1;
    min-width: 0;
    padding: 0 2px;
  }
  .name {
    font-weight: 600;
    font-size: 12.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sub {
    font-size: 11px;
    color: var(--faint);
  }
  .add {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: var(--raised);
    color: var(--text);
    opacity: 0;
    transition: opacity 0.12s;
  }
  .grid .add {
    position: absolute;
    top: 11px;
    right: 11px;
    background: rgb(12 12 14 / 0.82);
  }
  .item:hover .add,
  .item:focus-within .add {
    opacity: 1;
  }
  .add:hover {
    background: var(--accent);
    color: var(--accent-ink);
  }
  .rename {
    flex: 1;
    min-width: 0;
    height: 28px;
    border-radius: 8px;
    user-select: text;
  }
  .tip {
    margin: 4px 8px 0;
    color: var(--faint);
    font-size: 12px;
    line-height: 1.5;
  }
  .error {
    margin: 6px 8px;
    color: #f3c7c3;
    font-size: 12px;
  }
</style>
