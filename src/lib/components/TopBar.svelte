<script lang="ts">
  import { studio, ASPECTS, type Aspect, type Quality } from "#lib/studio.svelte.ts";
  import Icon from "./Icon.svelte";
  import { goto } from "$app/navigation";
  import { settings } from "#lib/settings.svelte.ts";
  import Picker from "./Picker.svelte";
  import WindowControls from "./WindowControls.svelte";
  import ProjectSwitcher from "./ProjectSwitcher.svelte";

  let { onExport }: { onExport: () => void } = $props();

  const previewOptions: { id: Quality; label: string }[] = [
    { id: "fast", label: "Fast · 360p" },
    { id: "preview", label: "Preview · 480p" },
    { id: "draft", label: "Draft · 720p" },
    { id: "high", label: "Full · 1080p" },
  ];
</script>

<!-- Doubles as the window title bar: empty areas drag the window, double-click maximizes. -->
<div class="bar" data-tauri-drag-region>
  <div class="brand" data-tauri-drag-region>
    <button class="home" title="Home" aria-label="Home" onclick={async () => { await studio.save(); goto("/"); }}>
      <img src="/logo.svg" alt="" width="20" height="20" />
    </button>
    <ProjectSwitcher />
  </div>

  <div class="center" data-tauri-drag-region>
    <Picker
      label="Preview quality"
      prefix="Preview"
      width={220}
      items={previewOptions.map((o) => ({ value: o.id, label: o.label.split(" · ")[1] ?? o.label, sub: o.label.split(" · ")[0] }))}
      value={studio.previewQuality}
      onChange={(q) => (studio.previewQuality = q as Quality)}
    />
    <Picker
      label="Frame shape"
      prefix="Frame"
      width={240}
      items={ASPECTS.map((a) => ({ value: a.id, label: a.id, sub: a.label }))}
      value={studio.aspect}
      onChange={(a) => studio.setAspect(a as Aspect)}
    />
    <label class="toggle" title="Render the current scene every time you save">
      <input type="checkbox" bind:checked={studio.autoRender} />
      <span class="track"><span class="knob"></span></span>
      Render on save
    </label>
  </div>

  <div class="right" data-tauri-drag-region>
    <button class="icon-btn" title="Settings (Ctrl + ,)" aria-label="Settings" onclick={() => settings.show()}>
      <Icon name="settings" size={16} />
    </button>
    {#if studio.job?.kind === "render"}
      <button class="btn" onclick={() => studio.cancel()}><Icon name="stop" size={12} /> Stop</button>
    {:else}
      <button class="icon-btn" title="Quick look: render only the last frame" aria-label="Quick look at the last frame" disabled={!studio.currentScene} onclick={() => studio.quickLook()}>
        <Icon name="image" size={16} />
      </button>
      <button class="btn" disabled={!studio.currentScene} onclick={() => studio.renderCurrent()}>
        <Icon name="bolt" size={14} /> Render
      </button>
    {/if}
    <button class="btn primary" disabled={!studio.clips.length && !studio.currentScene} onclick={onExport}>
      <Icon name="export" size={14} /> Export
    </button>
    <WindowControls />
  </div>
</div>

<style>
  .bar {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    height: 52px;
    padding: 0 0 0 14px;
    background: var(--bg);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 9px;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.01em;
  }
  .home {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: var(--r-md);
  }
  .home:hover {
    background: var(--raised);
  }
  .center {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
    cursor: pointer;
  }
  .toggle input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
  .track {
    position: relative;
    width: 28px;
    height: 16px;
    border-radius: 8px;
    background: var(--raised);
    transition: background 0.15s;
  }
  .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--muted);
    transition: transform 0.15s, background 0.15s;
  }
  .toggle input:checked + .track {
    background: var(--accent-soft);
  }
  .toggle input:checked + .track .knob {
    transform: translateX(12px);
    background: var(--accent);
  }
  .toggle input:focus-visible + .track {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
  .right {
    display: flex;
    align-items: center;
    align-self: stretch;
    justify-content: flex-end;
    gap: 8px;
  }
</style>
