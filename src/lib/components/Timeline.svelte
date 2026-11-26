<script lang="ts">
  import { open } from "@tauri-apps/plugin-dialog";
  import { studio, sceneKey, type Clip, type AudioClip, type Track } from "#lib/studio.svelte.ts";
  import { timecode, shortTime, clamp } from "#lib/time.ts";
  import { mediaUrl } from "#lib/api.ts";
  import Icon from "./Icon.svelte";
  import { settings } from "#lib/settings.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import ContextMenu, { type MenuItem } from "./ContextMenu.svelte";
  import { voice } from "#lib/voice.svelte.ts";

  let menu = $state<{ x: number; y: number; items: MenuItem[] } | null>(null);

  const deleteViaShortcut = () => window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));

  /** Double-click a scene clip: open its code at the scene. */
  async function openScript(clip: Clip) {
    await studio.openFile(clip.file);
    ui.mainTab = "code";
    const s = studio.scenes[clip.file]?.find((x) => x.name === clip.scene);
    if (s) studio.goToLine(s.line);
  }

  /** Double-click a generated voiceover: reopen the generator with its settings. */
  async function editVoice(clip: AudioClip) {
    if (!(await voice.metaFor(clip.path))) return;
    ui.voiceEdit = { path: clip.path, clipId: clip.id };
    ui.voiceOpen = true;
  }

  /** Right-click on a clip: trims and edits that act at the playhead. */
  function clipMenu(e: MouseEvent, clip: Clip | AudioClip, kind: Track) {
    e.preventDefault();
    e.stopPropagation();
    studio.selectedClip = clip.id;
    const inside = studio.playheadInside(clip.id);
    const why = inside ? undefined : "Move the playhead inside this clip first";
    const items: MenuItem[] = [
      { label: "Split at playhead", icon: "scissors", shortcut: "S", disabled: !inside, hint: why, action: () => studio.splitAtPlayhead() },
      { label: "Trim start to playhead", icon: "trimStart", disabled: !inside, hint: why, action: () => studio.trimToPlayhead(clip.id, "start") },
      { label: "Trim end to playhead", icon: "trimEnd", disabled: !inside, hint: why, action: () => studio.trimToPlayhead(clip.id, "end") },
      "separator",
    ];
    if (kind === "video" && "scene" in clip) {
      const key = sceneKey(clip.file, clip.scene);
      items.push(
        { label: "Show in viewer", icon: "play", disabled: !studio.renders[key], action: () => studio.showSource(key) },
        {
          label: "Open code",
          icon: "file",
          action: async () => {
            await studio.openFile(clip.file);
            ui.mainTab = "code";
            const s = studio.scenes[clip.file]?.find((x) => x.name === clip.scene);
            if (s) studio.goToLine(s.line);
          },
        },
      );
    } else if ("path" in clip) {
      const muted = clip.volume === 0;
      items.push({ label: muted ? "Unmute clip" : "Mute clip", icon: muted ? "volume" : "mute", action: () => studio.setVolume(clip.id, muted ? 1 : 0) });
      if (voice.meta[clip.path.slice((studio.dir?.length ?? 0) + 1).replaceAll("\\", "/")]) {
        items.push({ label: "Edit voiceover…", icon: "mic", action: () => editVoice(clip) });
      }
    }
    items.push(
      { label: "Duplicate", icon: "copy", action: () => studio.duplicateClip(clip.id) },
      "separator",
      { label: "Delete", icon: "trash", shortcut: "Del", danger: true, action: deleteViaShortcut },
    );
    menu = { x: e.clientX, y: e.clientY, items };
  }

  /** Right-click on the empty audio lane: add audio where you clicked. */
  function audioLaneMenu(e: MouseEvent) {
    e.preventDefault();
    const at = toTime(e.clientX);
    menu = {
      x: e.clientX,
      y: e.clientY,
      items: [{ label: "Add music or voiceover here", icon: "music", action: () => addAudioAt(at) }],
    };
  }

  const HEADER_W = 76;
  const SNAP_PX = 8;

  let scroller: HTMLDivElement;
  let viewportW = $state(800);
  let dropX = $state<number | null>(null);

  const contentSeconds = $derived(Math.max(studio.timelineDuration + 20, (viewportW - HEADER_W) / studio.zoom));
  const contentW = $derived(contentSeconds * studio.zoom);

  // Ruler steps: pick the smallest major interval that leaves ≥ 80px between labels.
  const major = $derived([0.5, 1, 2, 5, 10, 15, 30, 60, 120].find((s) => s * studio.zoom >= 80) ?? 300);
  const minor = $derived(major / (major >= 5 ? 5 : 4));
  const ticks = $derived.by(() => {
    const out: { x: number; t: number; major: boolean }[] = [];
    const n = Math.ceil(contentSeconds / minor);
    for (let i = 0; i <= n; i++) {
      const t = i * minor;
      out.push({ x: t * studio.zoom, t, major: Math.abs(t / major - Math.round(t / major)) < 1e-6 });
    }
    return out;
  });

  const toTime = (clientX: number) => {
    const rect = scroller.getBoundingClientRect();
    return Math.max(0, (clientX - rect.left - HEADER_W + scroller.scrollLeft) / studio.zoom);
  };

  /** Snap a time to clip edges, the playhead and zero when within SNAP_PX. */
  function snap(t: number, ignore?: string) {
    if (!settings.value.snapping) return t;
    const targets = [0, studio.playhead];
    for (const c of [...studio.clips, ...studio.audio]) if (c.id !== ignore) targets.push(c.start, c.start + c.out - c.in);
    let best = t;
    let bestD = SNAP_PX / studio.zoom;
    for (const s of targets) {
      const d = Math.abs(s - t);
      if (d < bestD) {
        best = s;
        bestD = d;
      }
    }
    return best;
  }

  function drag(e: PointerEvent, onMove: (dt: number, ev: PointerEvent) => void, onEnd?: () => void) {
    e.stopPropagation();
    const el = e.currentTarget as HTMLElement;
    const x0 = e.clientX;
    el.setPointerCapture(e.pointerId);
    el.onpointermove = (ev) => onMove((ev.clientX - x0) / studio.zoom, ev);
    el.onpointerup = () => {
      el.onpointermove = null;
      el.onpointerup = null;
      onEnd?.();
    };
  }

  function seek(e: PointerEvent) {
    if (e.button !== 0) return; // right-click opens a menu; it must not move the playhead
    studio.playing = false;
    studio.viewerMode = "program";
    studio.playhead = toTime(e.clientX);
    drag(e, (_dt, ev) => (studio.playhead = snap(toTime(ev.clientX))));
  }

  function moveClip(e: PointerEvent, clip: Clip | AudioClip, kind: Track = "video") {
    if (e.button !== 0) return;
    studio.selectedClip = clip.id;
    studio.viewerMode = "program";
    const start0 = clip.start;
    const len = clip.out - clip.in;
    drag(
      e,
      (dt) => {
        let s = start0 + dt;
        const head = snap(s, clip.id);
        const tail = snap(s + len, clip.id) - len;
        s = Math.abs(head - s) <= Math.abs(tail - s) ? head : tail;
        studio.moveClip(clip.id, s);
      },
      () => studio.resolveOverlaps(kind, clip.id),
    );
  }

  function trim(e: PointerEvent, clip: Clip | AudioClip, edge: "in" | "out", kind: Track = "video") {
    if (e.button !== 0) return;
    studio.selectedClip = clip.id;
    const in0 = clip.in;
    const out0 = clip.out;
    const start0 = clip.start;
    drag(
      e,
      (dt) => {
        if (edge === "in") {
          const t = snap(start0 + dt, clip.id);
          studio.trimClip(clip.id, "in", in0 + (t - start0));
        } else {
          const end = snap(start0 + (out0 - in0) + dt, clip.id);
          studio.trimClip(clip.id, "out", in0 + (end - start0));
        }
      },
      () => studio.resolveOverlaps(kind, clip.id),
    );
  }

  function onDragOver(e: DragEvent) {
    if (!e.dataTransfer?.types.includes("application/x-manim-scene")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    dropX = snap(toTime(e.clientX)) * studio.zoom;
  }

  function onDrop(e: DragEvent) {
    const key = e.dataTransfer?.getData("application/x-manim-scene");
    const at = dropX !== null ? dropX / studio.zoom : undefined;
    dropX = null;
    if (!key) return;
    e.preventDefault();
    const [file, scene] = key.split("::");
    studio.addToTimeline(file, scene, at);
  }

  function zoomBy(f: number) {
    studio.zoom = clamp(studio.zoom * f, 6, 400);
  }

  function onWheel(e: WheelEvent) {
    if (e.ctrlKey) {
      e.preventDefault();
      const t = toTime(e.clientX);
      const before = t * studio.zoom - scroller.scrollLeft;
      zoomBy(e.deltaY < 0 ? 1.15 : 1 / 1.15);
      requestAnimationFrame(() => (scroller.scrollLeft = t * studio.zoom - before));
    }
  }

  // Keep the playhead in view while playing.
  $effect(() => {
    if (!studio.playing || !scroller) return;
    const x = studio.playhead * studio.zoom;
    const visible = scroller.clientWidth - HEADER_W;
    if (x > scroller.scrollLeft + visible - 40) scroller.scrollLeft = x - 40;
  });

  const selectedInfo = $derived(studio.find(studio.selectedClip));
  const selected = $derived(selectedInfo?.clip);
  const selectedAudio = $derived(selectedInfo?.kind === "audio" ? (selectedInfo.clip as AudioClip) : null);
  const canSplit = $derived(
    !![...studio.clips, ...studio.audio].find(
      (c) => studio.playhead > c.start + 0.1 && studio.playhead < c.start + c.out - c.in - 0.1,
    ),
  );

  async function addAudio() {
    return addAudioAt(studio.playhead);
  }

  async function addAudioAt(at: number) {
    const file = await open({
      title: "Add music or voiceover",
      filters: [{ name: "Audio", extensions: ["mp3", "wav", "m4a", "aac", "ogg", "flac", "opus"] }],
    });
    if (typeof file === "string") {
      try {
        await studio.addAudio(file, at);
      } catch (e) {
        studio.error = { message: `Could not add that audio file: ${String((e as { message?: string }).message ?? e)}` };
      }
    }
  }

  /** Waveform outline for the visible (trimmed) part of an audio clip. */
  function wavePath(clip: AudioClip, peaks: number[] | undefined): string {
    if (!peaks?.length || !clip.duration) return "";
    const a = Math.floor((clip.in / clip.duration) * peaks.length);
    const b = Math.max(a + 1, Math.ceil((clip.out / clip.duration) * peaks.length));
    const slice = peaks.slice(a, b);
    const n = Math.min(slice.length, 400);
    const step = slice.length / n;
    let top = "M0 50";
    let bottom = "";
    for (let i = 0; i < n; i++) {
      let m = 0;
      for (let j = Math.floor(i * step); j < Math.floor((i + 1) * step); j++) m = Math.max(m, slice[j] ?? 0);
      const x = ((i + 0.5) / n) * 100;
      const h = Math.max(1.5, m * 46);
      top += ` L${x.toFixed(2)} ${(50 - h).toFixed(1)}`;
      bottom = ` L${x.toFixed(2)} ${(50 + h).toFixed(1)}` + bottom;
    }
    return `${top} L100 50${bottom} Z`;
  }
</script>

{#if menu}
  <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => (menu = null)} />
{/if}

<section class="timeline">
  <header>
    <span class="tc">{timecode(studio.playhead)}</span>
    <div class="tools">
      <button class="icon-btn" title="Split at playhead (S)" aria-label="Split at playhead" disabled={!canSplit} onclick={() => studio.splitAtPlayhead()}>
        <Icon name="scissors" />
      </button>
      <button class="icon-btn" title="Delete clip (Del)" aria-label="Delete clip" disabled={!selected} onclick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }))}>
        <Icon name="trash" />
      </button>
      <button class="icon-btn" title="Add music or voiceover" aria-label="Add audio" disabled={!studio.dir} onclick={addAudio}>
        <Icon name="music" />
      </button>
    </div>
    {#if selectedAudio}
      <label class="volume" title="Clip volume">
        <Icon name="volume" size={14} />
        <input
          type="range"
          min="0"
          max="2"
          step="0.05"
          aria-label="Clip volume"
          value={selectedAudio.volume}
          oninput={(e) => studio.setVolume(selectedAudio.id, +e.currentTarget.value)}
        />
        <span>{Math.round(selectedAudio.volume * 100)}%</span>
      </label>
    {/if}
    <div class="zoom">
      <button class="icon-btn" aria-label="Zoom out" onclick={() => zoomBy(1 / 1.4)}><Icon name="zoomOut" /></button>
      <input
        type="range"
        min="6"
        max="400"
        step="1"
        aria-label="Timeline zoom"
        value={studio.zoom}
        oninput={(e) => (studio.zoom = +e.currentTarget.value)}
      />
      <button class="icon-btn" aria-label="Zoom in" onclick={() => zoomBy(1.4)}><Icon name="zoomIn" /></button>
    </div>
  </header>

  <div class="body" bind:this={scroller} bind:clientWidth={viewportW} onwheel={onWheel}>
    <div class="canvas" style:width="{contentW + HEADER_W}px">
      <!-- Ruler -->
      <div class="row ruler-row">
        <div class="head corner"></div>
        <div class="ruler" role="presentation" onpointerdown={seek}>
          {#each ticks as tick (tick.t)}
            <div class="tick" class:major={tick.major} style:left="{tick.x}px">
              {#if tick.major}<span>{shortTime(tick.t)}</span>{/if}
            </div>
          {/each}
        </div>
      </div>

      <!-- Video track -->
      <div class="row track-row">
        <div class="head">
          <span class="track-name">V1</span>
          <span class="track-kind">Video</span>
        </div>
        <div
          class="lane"
          role="list"
          aria-label="Video track"
          onpointerdown={(e) => {
            if (e.button !== 0) return;
            studio.selectedClip = null;
            seek(e);
          }}
          ondragover={onDragOver}
          ondragleave={() => (dropX = null)}
          ondrop={onDrop}
        >
          {#each studio.clips as clip (clip.id)}
            {@const r = studio.renders[sceneKey(clip.file, clip.scene)]}
            <div
              class="clip"
              role="listitem"
              class:selected={clip.id === studio.selectedClip}
              class:stale={!r}
              style:left="{clip.start * studio.zoom}px"
              style:width="{(clip.out - clip.in) * studio.zoom}px"
              onpointerdown={(e) => moveClip(e, clip)}
              oncontextmenu={(e) => clipMenu(e, clip, "video")}
              ondblclick={() => openScript(clip)}
              title="{clip.scene} · {shortTime(clip.out - clip.in)}"
            >
              <div class="handle left" role="presentation" onpointerdown={(e) => trim(e, clip, "in")}></div>
              <div class="clip-body">
                <span class="clip-name">{clip.scene}</span>
                <span class="clip-len">{shortTime(clip.out - clip.in)}</span>
              </div>
              {#if r?.strip && r.stripFrames}
                {@const width = (clip.out - clip.in) * studio.zoom}
                {@const tileW = 56}
                {@const n = Math.max(1, Math.ceil(width / tileW))}
                <div class="strip frames" aria-hidden="true">
                  {#each Array(n) as _, i (i)}
                    {@const t = clip.in + ((i + 0.5) * tileW / width) * (clip.out - clip.in)}
                    {@const f = Math.min(r.stripFrames - 1, Math.max(0, Math.floor((t / r.duration) * r.stripFrames)))}
                    <span
                      class="frame"
                      style:background-image="url('{mediaUrl(r.strip, r.version)}')"
                      style:background-size="{r.stripFrames * tileW}px 100%"
                      style:background-position="{-f * tileW}px 0"
                    ></span>
                  {/each}
                </div>
              {:else}
                <div class="strip"></div>
              {/if}
              <div class="handle right" role="presentation" onpointerdown={(e) => trim(e, clip, "out")}></div>
            </div>
          {/each}
          {#if dropX !== null}<div class="drop" style:left="{dropX}px"></div>{/if}
          {#if !studio.clips.length && dropX === null}
            <div class="lane-empty">Drop scenes here</div>
          {/if}
        </div>
      </div>

      <!-- Audio track -->
      <div class="row track-row audio-row">
        <div class="head">
          <span class="track-name">A1</span>
          <span class="track-kind">Audio</span>
          <button
            class="icon-btn mute"
            class:on={studio.audioMuted}
            title={studio.audioMuted ? "Unmute track" : "Mute track"}
            aria-label={studio.audioMuted ? "Unmute audio track" : "Mute audio track"}
            onclick={() => (studio.audioMuted = !studio.audioMuted)}
          >
            <Icon name={studio.audioMuted ? "mute" : "volume"} size={13} />
          </button>
        </div>
        <div
          class="lane"
          role="list"
          aria-label="Audio track"
          oncontextmenu={audioLaneMenu}
          ondragover={(e) => {
            if (e.dataTransfer?.types.includes("application/x-mp-audio")) {
              e.preventDefault();
              e.dataTransfer.dropEffect = "copy";
            }
          }}
          ondrop={(e) => {
            const path = e.dataTransfer?.getData("application/x-mp-audio");
            if (!path) return;
            e.preventDefault();
            studio.placeAudio(path, snap(toTime(e.clientX)));
          }}
          onpointerdown={(e) => {
            if (e.button !== 0) return;
            studio.selectedClip = null;
            seek(e);
          }}
        >
          {#each studio.audio as clip (clip.id)}
            <div
              class="clip audio"
              role="listitem"
              class:selected={clip.id === studio.selectedClip}
              class:muted={studio.audioMuted}
              style:left="{clip.start * studio.zoom}px"
              style:width="{(clip.out - clip.in) * studio.zoom}px"
              onpointerdown={(e) => moveClip(e, clip, "audio")}
              oncontextmenu={(e) => clipMenu(e, clip, "audio")}
              ondblclick={() => editVoice(clip)}
              title="{clip.name} · {shortTime(clip.out - clip.in)}"
            >
              <div class="handle left" role="presentation" onpointerdown={(e) => trim(e, clip, "in", "audio")}></div>
              <svg class="wave" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <path d={wavePath(clip, studio.waveforms[clip.path])} />
              </svg>
              <span class="audio-name">{clip.name}</span>
              <div class="handle right" role="presentation" onpointerdown={(e) => trim(e, clip, "out", "audio")}></div>
            </div>
          {/each}
          {#if !studio.audio.length}
            <button class="lane-empty add" onpointerdown={(e) => e.stopPropagation()} onclick={addAudio}>
              <Icon name="music" size={13} /> Add music or voiceover
            </button>
          {/if}
        </div>
      </div>

      <div class="playhead" style:left="{HEADER_W + studio.playhead * studio.zoom}px">
        <div class="cap"></div>
      </div>
    </div>
  </div>
</section>

<style>
  .timeline {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--panel);
  }
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 44px;
    padding: 0 12px;
    border-bottom: 1px solid var(--line);
  }
  .tc {
    font-family: var(--mono);
    font-size: 13px;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
    min-width: 92px;
  }
  .tools {
    display: flex;
    gap: 2px;
    padding-left: 12px;
    border-left: 1px solid var(--line);
  }
  .zoom {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .zoom input {
    width: 120px;
    padding: 0;
    accent-color: var(--muted);
    background: none;
    border: 0;
  }

  .body {
    position: relative;
    flex: 1;
    overflow: auto;
  }
  .canvas {
    position: relative;
    min-height: 100%;
  }
  .row {
    display: flex;
  }
  .head {
    position: sticky;
    left: 0;
    z-index: 3;
    flex: 0 0 76px;
    background: var(--panel);
    border-right: 1px solid var(--line);
  }
  .ruler-row {
    position: sticky;
    top: 0;
    z-index: 4;
    height: 26px;
    background: var(--panel);
    border-bottom: 1px solid var(--line);
  }
  .corner {
    background: var(--panel);
  }
  .ruler {
    position: relative;
    flex: 1;
    cursor: text;
  }
  .tick {
    position: absolute;
    bottom: 0;
    width: 1px;
    height: 5px;
    background: var(--line-strong);
  }
  .tick.major {
    height: 10px;
    background: var(--faint);
  }
  .tick span {
    position: absolute;
    left: 4px;
    bottom: 9px;
    font-size: 10.5px;
    font-family: var(--mono);
    color: var(--faint);
    white-space: nowrap;
  }

  .track-row {
    height: 72px;
    border-bottom: 1px solid var(--line);
  }
  .track-row .head {
    z-index: 6; /* above the playhead line */
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 10px;
    gap: 1px;
  }
  .track-name {
    font-weight: 600;
  }
  .track-kind {
    font-size: 11px;
    color: var(--faint);
  }
  .lane {
    position: relative;
    flex: 1;
  }
  .lane-empty {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    padding: 14px 24px;
    border: 1px dashed var(--line-strong);
    border-radius: var(--r-md);
    color: var(--faint);
    pointer-events: none;
  }

  .clip {
    position: absolute;
    top: 6px;
    bottom: 6px;
    min-width: 4px;
    border-radius: 9px;
    background: var(--clip);
    border: 1px solid var(--clip-edge);
    overflow: hidden;
    cursor: grab;
  }
  .clip:active {
    cursor: grabbing;
  }
  .clip.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
  }
  .clip.stale {
    background: var(--raised);
    border-style: dashed;
  }
  .clip-body {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 6px 10px 0;
    white-space: nowrap;
    overflow: hidden;
  }
  .clip-name {
    font-weight: 600;
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .clip-len {
    font-size: 11px;
    color: rgb(255 255 255 / 0.5);
    font-family: var(--mono);
  }
  /* A filmstrip texture: reads as "video" without needing thumbnails. */
  .strip {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 26px;
    background:
      repeating-linear-gradient(90deg, rgb(0 0 0 / 0.22) 0 1px, transparent 1px 46px),
      linear-gradient(180deg, color-mix(in srgb, var(--accent) 10%, transparent), color-mix(in srgb, var(--accent) 4%, transparent));
    border-top: 1px solid rgb(255 255 255 / 0.05);
  }
  /* Real frames from the render, matched to the clip's trimmed range. */
  .strip.frames {
    height: 34px;
    display: flex;
    overflow: hidden;
    background: #0a0a0b;
  }
  .frame {
    flex: none;
    width: 56px;
    height: 100%;
    background-repeat: no-repeat;
    border-right: 1px solid rgb(0 0 0 / 0.5);
    opacity: 0.92;
  }
  .handle {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 7px;
    z-index: 2;
    cursor: ew-resize;
  }
  /* Handles follow the clip's rounded corners and the accent color. */
  .handle.left {
    left: 0;
    border-radius: 8px 0 0 8px;
  }
  .handle.right {
    right: 0;
    border-radius: 0 8px 8px 0;
  }
  .clip.selected .handle,
  .handle:hover {
    background: color-mix(in srgb, var(--accent) 60%, transparent);
  }

  .audio-row {
    height: 58px;
  }
  .audio-row .head {
    position: sticky;
  }
  .mute {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 22px;
    height: 22px;
  }
  .mute.on {
    color: var(--danger);
  }
  .clip.audio {
    background: #2c3b2a;
    border-color: #4c6b45;
  }
  .clip.audio.selected {
    border-color: var(--accent);
  }
  .clip.audio.muted {
    opacity: 0.45;
  }
  .wave {
    position: absolute;
    top: 4px;
    left: 0;
    width: 100%;
    height: calc(100% - 8px);
  }
  .wave path {
    fill: #83c167;
    opacity: 0.75;
  }
  .audio-name {
    position: absolute;
    left: 8px;
    top: 3px;
    font-size: 11px;
    font-weight: 600;
    color: rgb(255 255 255 / 0.8);
    white-space: nowrap;
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.6);
    pointer-events: none;
  }
  .lane-empty.add {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    pointer-events: auto;
    padding: 8px 14px;
    color: var(--muted);
  }
  .lane-empty.add:hover {
    color: var(--text);
    border-color: var(--line-strong);
  }
  .volume {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--muted);
    font-size: 12px;
  }
  .volume input {
    width: 90px;
    padding: 0;
    border: 0;
    background: none;
    accent-color: var(--accent);
  }
  .volume span {
    min-width: 34px;
    font-family: var(--mono);
    font-size: 11px;
  }
  .drop {
    position: absolute;
    top: 4px;
    bottom: 4px;
    width: 2px;
    background: var(--accent);
    pointer-events: none;
  }

  .playhead {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--accent);
    z-index: 5;
    pointer-events: none;
  }
  .cap {
    position: absolute;
    top: 0;
    left: -6px;
    width: 13px;
    height: 14px;
    background: var(--accent);
    clip-path: polygon(0 0, 100% 0, 100% 60%, 50% 100%, 0 60%);
  }
</style>
