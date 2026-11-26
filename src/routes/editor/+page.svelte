<script lang="ts">
  import { onMount } from "svelte";
  import { studio } from "#lib/studio.svelte.ts";
  import { clamp } from "#lib/time.ts";
  import TopBar from "#lib/components/TopBar.svelte";
  import Sidebar from "#lib/components/Sidebar.svelte";
  import LatexDialog from "#lib/components/LatexDialog.svelte";
  import VoiceDialog from "#lib/components/VoiceDialog.svelte";
  import { voice } from "#lib/voice.svelte.ts";
  import { assistant } from "#lib/assistant.svelte.ts";
  import { goto } from "$app/navigation";
  import { ui } from "#lib/ui.svelte.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import { fullscreen } from "#lib/fullscreen.svelte.ts";
  import { ask } from "@tauri-apps/plugin-dialog";
  import MainPanel from "#lib/components/MainPanel.svelte";
  import Viewer from "#lib/components/Viewer.svelte";
  import Timeline from "#lib/components/Timeline.svelte";
  import StatusBar from "#lib/components/StatusBar.svelte";
  import ExportDialog from "#lib/components/ExportDialog.svelte";
  import CaptionsDialog from "#lib/components/CaptionsDialog.svelte";

  let viewer: Viewer;
  let exporting = $state(false);
  let bootError = $state<string | null>(null);

  // Resizable layout
  let sideW = $state(300);
  let editorFrac = $state(0.46);
  const previewCenter = $derived(settings.value.editorLayout === "preview-center");
  const sideRight = $derived(settings.value.sidebarSide === "right");
  let timelineH = $state(250);
  let main: HTMLElement;
  let editorEl: HTMLDivElement;
  let previewEl: HTMLDivElement;

  type Panel = "side" | "editor" | "preview";
  /**
   * Grid placement for the three panels. Columns (left to right) alternate
   * panel / 8px gutter; rows are top area / 8px gutter / timeline. The
   * full-height panel, and anything on its far side from the preview, spans
   * all rows; the timeline runs under the rest.
   */
  const layout = $derived.by(() => {
    const work: Panel[] = previewCenter ? ["preview", "editor"] : ["editor", "preview"];
    const order: Panel[] = sideRight ? [...work, "side"] : ["side", ...work];
    const full = settings.value.fullHeight === "project" ? "side" : settings.value.fullHeight === "code" ? "editor" : null;
    const p = order.indexOf("preview");
    const f = full ? order.indexOf(full) : -1;
    // Timeline tracks (1-based, inclusive): from the preview's edge up to the full-height panel.
    const [t0, t1] = f < 0 ? [1, 5] : p < f ? [1, 2 * f - 1] : [2 * f + 3, 5];
    const underTimeline = (track: number) => track >= t0 && track <= t1;
    const place = (track: number) => `1 / ${track} / ${underTimeline(track) ? 2 : 4} / ${track + 1}`;
    const area = Object.fromEntries(order.map((panel, i) => [panel, place(2 * i + 1)])) as Record<Panel, string>;
    const size = (panel: Panel) =>
      panel === "side" ? "var(--side)" : `minmax(0, ${panel === "editor" ? editorFrac : 1 - editorFrac}fr)`;
    const gutterKind = (i: number): "side" | "split" => (order[i] === "side" || order[i + 1] === "side" ? "side" : "split");
    return {
      columns: [size(order[0]), "8px", size(order[1]), "8px", size(order[2])].join(" "),
      area,
      gutters: [0, 1].map((i) => place(2 * i + 2)),
      gutterKinds: [gutterKind(0), gutterKind(1)],
      gutterLabels: [0, 1].map((i) => (gutterKind(i) === "side" ? "Resize project panel" : "Resize editor")),
      timelineGutter: `2 / ${t0} / 3 / ${t1 + 1}`,
      timeline: `3 / ${t0} / 4 / ${t1 + 1}`,
    };
  });

  onMount(() => {
    if (!studio.dir) {
      goto("/");
      return;
    }
    studio.init().catch((e) => (bootError = String(e)));
    if (ui.exportOnOpen) {
      ui.exportOnOpen = false;
      if (studio.clips.length) exporting = true;
    }
    assistant.init();
    if (studio.dir) assistant.loadChats(studio.dir);
    voice.loadMeta();
  });

  function resize(e: PointerEvent, kind: "side" | "split" | "timeline") {
    const el = e.currentTarget as HTMLElement;
    el.setPointerCapture(e.pointerId);
    el.onpointermove = (ev) => {
      if (kind === "side") {
        const r = main.getBoundingClientRect();
        sideW = clamp(sideRight ? r.right - 8 - ev.clientX : ev.clientX - r.left - 8, 220, 520);
      }
      else if (kind === "timeline") timelineH = clamp(window.innerHeight - ev.clientY - 26, 140, window.innerHeight - 320);
      else {
        const a = editorEl.getBoundingClientRect();
        const b = previewEl.getBoundingClientRect();
        const l = Math.min(a.left, b.left);
        const w = Math.max(a.right, b.right) - l;
        const left = clamp((ev.clientX - l) / w, 0.25, 0.75);
        editorFrac = previewCenter ? 1 - left : left;
      }
    };
    el.onpointerup = () => (el.onpointermove = null);
  }

  function inTextField(e: KeyboardEvent) {
    const t = e.target as HTMLElement;
    return t.closest(".monaco-editor") || ["INPUT", "SELECT", "TEXTAREA"].includes(t.tagName);
  }

  async function deleteClip() {
    if (!studio.selectedClip) return;
    if (settings.value.confirmDelete && !(await ask("Delete this clip from the timeline?", { title: "Delete clip", kind: "warning" }))) return;
    studio.deleteSelected();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "F11") {
      e.preventDefault();
      const inCode = (e.target as HTMLElement).closest(".monaco-editor") || ui.mainTab === "assistant";
      fullscreen.toggle(fullscreen.target ?? (inCode && !studio.playing ? "code" : "viewer"));
      return;
    }
    if (e.key === "Escape" && fullscreen.target && !(e.target as HTMLElement).closest(".monaco-editor, dialog")) {
      fullscreen.exit();
      return;
    }
    // The code editor binds its own Ctrl+S / Ctrl+Enter.
    if ((e.target as HTMLElement).closest(".monaco-editor") && e.ctrlKey) return;
    if (e.ctrlKey && e.key === "s") {
      e.preventDefault();
      studio.save().then(() => {
        if (studio.autoRender) studio.renderCurrent();
      });
      return;
    }
    if (e.ctrlKey && e.key === "Enter") {
      e.preventDefault();
      studio.renderCurrent();
      return;
    }
    if (e.ctrlKey && e.key.toLowerCase() === "e") {
      e.preventDefault();
      if (studio.clips.length || studio.currentScene) exporting = true;
      return;
    }
    if (inTextField(e) || exporting) return;
    if (e.ctrlKey && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) {
      e.preventDefault();
      studio.redo();
      return;
    }
    if (e.ctrlKey && e.key.toLowerCase() === "z") {
      e.preventDefault();
      studio.undo();
      return;
    }
    if (e.key === " ") {
      e.preventDefault();
      viewer?.togglePlay();
    } else if (e.key === "s" || e.key === "S") {
      studio.splitAtPlayhead();
    } else if (e.key === "Delete" || e.key === "Backspace") {
      deleteClip();
    } else if (e.key === "Home") {
      studio.playhead = 0;
    } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      studio.playing = false;
      studio.viewerMode = "program";
      const step = (e.shiftKey ? 1 : 1 / 30) * (e.key === "ArrowLeft" ? -1 : 1);
      studio.playhead = clamp(studio.playhead + step, 0, studio.timelineDuration);
    }
  }
</script>

<svelte:window onkeydown={onKey} />

<div class="app" style:--side="{sideW}px" style:--tl="{timelineH}px">
  <TopBar onExport={() => (exporting = true)} />

  <main bind:this={main} style:grid-template-columns={layout.columns}>
    <!-- Panels are placed by grid position (never re-created), so the editor and a running chat keep their state. -->
    <div class="side" style:grid-area={layout.area.side}><Sidebar /></div>
    <div class="gutter v" style:grid-area={layout.gutters[0]} role="separator" aria-orientation="vertical" aria-label={layout.gutterLabels[0]} onpointerdown={(e) => resize(e, layout.gutterKinds[0])}></div>
    <div class="pane editor" bind:this={editorEl} style:grid-area={layout.area.editor}><MainPanel /></div>
    <div class="gutter v" style:grid-area={layout.gutters[1]} role="separator" aria-orientation="vertical" aria-label={layout.gutterLabels[1]} onpointerdown={(e) => resize(e, layout.gutterKinds[1])}></div>
    <div class="pane preview" bind:this={previewEl} style:grid-area={layout.area.preview}><Viewer bind:this={viewer} /></div>
    <div class="gutter h" style:grid-area={layout.timelineGutter} role="separator" aria-orientation="horizontal" aria-label="Resize timeline" onpointerdown={(e) => resize(e, "timeline")}></div>
    <div class="bottom" style:grid-area={layout.timeline}><Timeline /></div>
  </main>

  {#if settings.value.showStatusBar}<StatusBar />{/if}
</div>

{#if bootError}
  <div class="boot-error" role="alert">
    <strong>ManimPro could not open your project.</strong>
    <p>{bootError}</p>
  </div>
{/if}

{#if ui.voiceOpen}
  <VoiceDialog
    onClose={() => {
      ui.voiceOpen = false;
      ui.voiceEdit = null;
    }}
  />
{/if}

{#if ui.captionsOpen}
  <CaptionsDialog focus={ui.captionFocus} onClose={() => (ui.captionsOpen = false)} />
{/if}

{#if ui.latexOpen}
  <LatexDialog onClose={() => (ui.latexOpen = false)} />
{/if}

{#if exporting}
  <ExportDialog onClose={() => (exporting = false)} />
{/if}

<style>
  .app {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100vh;
  }
  main {
    display: grid;
    grid-template-rows: minmax(0, 1fr) 8px var(--tl);
    min-height: 0;
    min-width: 0;
    padding: 0 8px;
  }
  .side,
  .pane,
  .bottom {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    border-radius: var(--r-lg);
    border: 1px solid var(--line);
  }
  .gutter {
    position: relative;
  }
  .gutter.v {
    cursor: col-resize;
  }
  .gutter.h {
    cursor: row-resize;
  }
  .gutter::after {
    content: "";
    position: absolute;
    border-radius: 2px;
    background: var(--accent);
    opacity: 0;
    transition: opacity 0.12s;
  }
  .gutter.v::after {
    inset: 30% 2px;
  }
  .gutter.h::after {
    inset: 2px 45%;
  }
  .gutter:hover::after {
    opacity: 0.7;
  }
  .boot-error {
    position: fixed;
    inset: auto 24px 40px;
    padding: 14px 16px;
    border-radius: var(--r-lg);
    background: #2a1a1a;
    border: 1px solid #5a2b28;
    color: #f3c7c3;
  }
  .boot-error p {
    margin: 4px 0 0;
    font-family: var(--mono);
    font-size: 12px;
  }
</style>
