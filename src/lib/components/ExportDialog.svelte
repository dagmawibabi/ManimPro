<script lang="ts">
  import { save, open as pickFolder } from "@tauri-apps/plugin-dialog";
  import { revealItemInDir } from "@tauri-apps/plugin-opener";
  import { studio, EXPORT_PRESETS, EXPORT_FORMATS, ASPECTS, sceneKey, type Aspect, type ExportFormat } from "#lib/studio.svelte.ts";
  import { basename, joinPath } from "#lib/api.ts";
  import { timecode } from "#lib/time.ts";
  import Icon from "./Icon.svelte";
  import { settings } from "#lib/settings.svelte.ts";

  let { onClose }: { onClose: () => void } = $props();

  let aspect = $state<Aspect>(studio.aspect);
  const size = $derived(studio.frameSize(EXPORT_PRESETS.find((p) => p.id === presetId)!.height, aspect));
  let presetId = $state(settings.value.exportPreset as (typeof EXPORT_PRESETS)[number]["id"]);
  const exportDir = settings.value.exportFolder || studio.dir;
  if (!studio.clips.length && studio.currentScene && studio.activeFile) {
    // Nothing on the timeline: default to exporting the open scene.
    queueMicrotask(() => (what = sceneKey(studio.activeFile!, studio.currentScene!.name)));
  }
  let format = $state<ExportFormat>("mp4");
  /** "" = the whole timeline, else one scene's key. */
  let what = $state<string>("");
  let captionMode = $state<"off" | "srt" | "burn">(studio.captions.length ? "srt" : "off");
  let transparent = $state(false);
  const scenes = $derived(
    studio.files.flatMap((f) => (studio.scenes[f] ?? []).map((s) => ({ key: sceneKey(f, s.name), name: s.name, file: basename(f) }))),
  );
  const fmt = $derived(EXPORT_FORMATS.find((f) => f.id === format)!);
  const baseName = $derived(what ? what.split("::")[1] : studio.dir ? basename(studio.dir) : "video");
  let output = $state("");
  let outputTouched = false;
  // The file name follows the format and what is exported until the user picks one.
  $effect(() => {
    const ext = fmt.ext;
    const name = ext ? `${baseName}.${ext}` : `${baseName} frames`;
    if (!outputTouched && exportDir) output = joinPath(exportDir, name);
    else if (output && ext) output = output.replace(/\.[^.\\/]+$/, "") + `.${ext}`;
  });
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
    if (format === "png") {
      const dir = await pickFolder({ directory: true, title: "Folder for the frames" });
      if (typeof dir === "string") {
        output = joinPath(dir, `${baseName} frames`);
        outputTouched = true;
      }
      return;
    }
    const path = await save({
      title: "Export video",
      defaultPath: output,
      filters: [{ name: fmt.label, extensions: [fmt.ext] }],
    });
    if (path) {
      output = path.toLowerCase().endsWith(`.${fmt.ext}`) ? path : `${path}.${fmt.ext}`;
      outputTouched = true;
    }
  }

  async function start() {
    failure = null;
    done = null;
    stage = "Preparing";
    try {
      const r = await studio.exportVideo(preset, output, (s) => (stage = s), {
        aspect,
        format,
        only: what || null,
        burnCaptions: captionMode === "burn",
        srt: captionMode !== "off",
        transparent: transparent && (format === "mov" || format === "webm"),
      });
      done = r.output;
      if (settings.value.revealAfterExport) revealItemInDir(r.output);
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
        <p>{fmt.label} · {preset.label} · {aspect} ({size.width}×{size.height}){what ? "" : ` · ${timecode(studio.timelineDuration)}`}</p>
      </div>
    </div>
    <footer>
      <button class="btn" onclick={() => revealItemInDir(done!)}><Icon name="reveal" size={14} /> Show in folder</button>
      <button class="btn primary" onclick={close}>Done</button>
    </footer>
  {:else}
    <div class="fields">
      <label>
        <span>Export</span>
        <select bind:value={what} disabled={running}>
          <option value="" disabled={!studio.clips.length}>The whole timeline{studio.clips.length ? "" : " (empty)"}</option>
          {#each scenes as s (s.key)}<option value={s.key}>Just {s.name} ({s.file})</option>{/each}
        </select>
      </label>
      <label>
        <span>Format</span>
        <select bind:value={format} disabled={running}>
          {#each EXPORT_FORMATS as f (f.id)}<option value={f.id}>{f.label}</option>{/each}
        </select>
      </label>
      <p class="note dims">{fmt.note}</p>
      {#if format === "mov" || format === "webm"}
        <label class="check">
          <input type="checkbox" bind:checked={transparent} disabled={running} />
          <span>Transparent background</span>
        </label>
        {#if transparent}
          <p class="note dims">
            Scenes render without a background ({format === "mov" ? "ProRes 4444" : "VP9"} with alpha), for laying over other
            footage. Gaps between clips are see-through too.
          </p>
        {/if}
      {/if}
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
      {#if !what && studio.captions.length && format !== "png"}
        <label>
          <span>Captions</span>
          <select bind:value={captionMode} disabled={running}>
            <option value="off">Off</option>
            <option value="srt">Subtitle file (.srt) next to the video</option>
            <option value="burn">Burned into the picture, plus .srt</option>
          </select>
        </label>
      {/if}
      <label>
        <span>{format === "png" ? "Save frames in" : "Save as"}</span>
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
  .check {
    display: flex !important;
    flex-direction: row !important;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }
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
