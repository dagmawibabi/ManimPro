<script lang="ts">
  import { save } from "@tauri-apps/plugin-dialog";
  import { revealItemInDir } from "@tauri-apps/plugin-opener";
  import { studio, EXPORT_PRESETS, ASPECTS, type Aspect } from "#lib/studio.svelte.ts";
  import { basename, joinPath } from "#lib/api.ts";
  import { timecode } from "#lib/time.ts";
  import Icon from "./Icon.svelte";
  import { settings } from "#lib/settings.svelte.ts";

  let { onClose }: { onClose: () => void } = $props();

  let aspect = $state<Aspect>(studio.aspect);
  const size = $derived(studio.frameSize(EXPORT_PRESETS.find((p) => p.id === presetId)!.height, aspect));
  let presetId = $state(settings.value.exportPreset as (typeof EXPORT_PRESETS)[number]["id"]);
  const exportDir = settings.value.exportFolder || studio.dir;
  let output = $state(exportDir && studio.dir ? joinPath(exportDir, `${basename(studio.dir)}.mp4`) : "");
  let stage = $state<string | null>(null);
  let done = $state<string | null>(null);
  let failure = $state<string | null>(null);
  let dialog: HTMLDialogElement;

  const preset = $derived(EXPORT_PRESETS.find((p) => p.id === presetId)!);
  const running = $derived(stage !== null && !done && !failure);
  const fraction = $derived(studio.job?.kind === "export" ? (studio.job.fraction ?? 0) : null);

  $effect(() => {
    dialog.showModal();
  });

  async function chooseFile() {
    const path = await save({
      title: "Export video",
      defaultPath: output,
      filters: [{ name: "MP4 video", extensions: ["mp4"] }],
    });
    if (path) output = path.endsWith(".mp4") ? path : `${path}.mp4`;
  }

  async function start() {
    failure = null;
    done = null;
    stage = "Preparing";
    try {
      const r = await studio.exportVideo(preset, output, (s) => (stage = s), aspect);
      done = r.output;
    } catch (e) {
      failure = (e as { message?: string }).message ?? String(e);
    }
  }

  function close() {
    if (running) return;
    dialog.close();
    onClose();
  }
</script>

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <header>
    <h2>Export video</h2>
    <button class="icon-btn" aria-label="Close" disabled={running} onclick={close}><Icon name="close" /></button>
  </header>

  {#if done}
    <div class="result">
      <span class="ok-mark"><Icon name="check" size={18} /></span>
      <div>
        <strong>Exported {basename(done)}</strong>
        <p>{timecode(studio.timelineDuration)} · {preset.label} · {aspect} ({size.width}×{size.height})</p>
      </div>
    </div>
    <footer>
      <button class="btn" onclick={() => revealItemInDir(done!)}><Icon name="reveal" size={14} /> Show in folder</button>
      <button class="btn primary" onclick={close}>Done</button>
    </footer>
  {:else}
    <div class="fields">
      <label>
        <span>Resolution</span>
        <select bind:value={presetId} disabled={running}>
          {#each EXPORT_PRESETS as p (p.id)}<option value={p.id}>{p.label}</option>{/each}
        </select>
      </label>
      <label>
        <span>Frame</span>
        <select bind:value={aspect} disabled={running}>
          {#each ASPECTS as a (a.id)}<option value={a.id}>{a.id} · {a.label}{a.id === studio.aspect ? " (project)" : ""}</option>{/each}
        </select>
      </label>
      <p class="note dims">{size.width} × {size.height} px{aspect !== studio.aspect ? ". Scenes are laid out for " + studio.aspect + ", so check that nothing is cut off." : ""}</p>
      <label>
        <span>Save as</span>
        <div class="file">
          <input value={output} readonly title={output} />
          <button class="btn" disabled={running} onclick={chooseFile}>Change</button>
        </div>
      </label>
      <p class="note">
        Each scene is rendered again at full quality before the video is put together, so this can take a few minutes.
      </p>
    </div>

    {#if running}
      <div class="progress">
        <span>{stage}</span>
        <div class="bar" class:indeterminate={fraction === null}>
          <div style:width="{(fraction ?? 0.3) * 100}%"></div>
        </div>
      </div>
    {/if}
    {#if failure}
      <p class="failure">{failure}</p>
    {/if}

    <footer>
      <button class="btn" disabled={running} onclick={close}>Cancel</button>
      <button class="btn primary" disabled={running || !output} onclick={start}>
        <Icon name="export" size={14} /> {failure ? "Try again" : "Export"}
      </button>
    </footer>
  {/if}
</dialog>

<style>
  dialog {
    width: 440px;
    padding: 0;
    border: 1px solid var(--line-strong);
    border-radius: var(--r-lg);
    background: var(--panel);
    color: var(--text);
    box-shadow: 0 24px 60px rgb(0 0 0 / 0.5);
  }
  dialog::backdrop {
    background: rgb(8 9 11 / 0.6);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 12px 6px 18px;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 16px;
    font-weight: 600;
  }
  .fields {
    display: grid;
    gap: 14px;
    padding: 10px 18px;
  }
  label {
    display: grid;
    gap: 6px;
  }
  label > span {
    font-size: 12px;
    color: var(--muted);
  }
  .file {
    display: flex;
    gap: 6px;
  }
  .file input {
    flex: 1;
    min-width: 0;
    color: var(--muted);
  }
  .note {
    margin: 0;
    font-size: 12px;
    color: var(--faint);
    line-height: 1.5;
  }
  .progress {
    display: grid;
    gap: 8px;
    padding: 4px 18px 8px;
    font-size: 12px;
    color: var(--muted);
  }
  .bar {
    height: 4px;
    border-radius: 2px;
    background: var(--raised);
    overflow: hidden;
  }
  .bar div {
    height: 100%;
    background: var(--accent);
    transition: width 0.2s;
  }
  .bar.indeterminate div {
    animation: slide 1.2s ease-in-out infinite;
  }
  @keyframes slide {
    from {
      transform: translateX(-100%);
    }
    to {
      transform: translateX(340%);
    }
  }
  .failure {
    margin: 4px 18px;
    padding: 8px 10px;
    border-radius: var(--r-sm);
    background: #2a1a1a;
    color: #f3c7c3;
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
    max-height: 160px;
    overflow: auto;
    user-select: text;
  }
  .result {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 12px 18px;
  }
  .result p {
    margin: 2px 0 0;
    color: var(--muted);
    font-size: 12px;
  }
  .ok-mark {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: rgb(131 193 103 / 0.15);
    color: var(--ok);
  }
  footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 14px 18px 16px;
  }
</style>
