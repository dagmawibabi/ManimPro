<script lang="ts">
  import { studio, sceneKey } from "#lib/studio.svelte.ts";
  import { mediaUrl } from "#lib/api.ts";
  import { timecode, clamp } from "#lib/time.ts";
  import Icon from "./Icon.svelte";
  import { untrack } from "svelte";
  import { ui } from "#lib/ui.svelte.ts";
  import { fullscreen } from "#lib/fullscreen.svelte.ts";

  let video: HTMLVideoElement;
  let currentSrc = "";
  let sourceTime = $state(0);
  let sourcePlaying = $state(false);

  const source = $derived(studio.sourceKey ? studio.renders[studio.sourceKey] : null);
  const sourceName = $derived(studio.sourceKey?.split("::")[1] ?? "");
  const isProgram = $derived(studio.viewerMode === "program");
  const programClip = $derived(isProgram ? studio.clipAt(studio.playhead) : undefined);
  const showBlack = $derived(isProgram && !programClip);

  function setSrc(src: string) {
    if (currentSrc === src) return;
    currentSrc = src;
    video.src = src;
  }

  // ---- Source monitor: the native video element is the clock.
  $effect(() => {
    if (isProgram || !video) return;
    if (!source) {
      currentSrc = "";
      video.removeAttribute("src");
      video.load();
      return;
    }
    setSrc(mediaUrl(source.video, source.version));
    sourceTime = 0;
  });

  function toggleSource() {
    if (!source) return;
    if (video.paused) video.play();
    else video.pause();
  }

  // ---- Audio track: one <audio> element per clip, kept in step with the playhead.
  const players = new Map<string, HTMLAudioElement>();

  function syncAudio(t: number, playing: boolean) {
    const live = new Set(studio.audio.map((a) => a.id));
    for (const [id, el] of players) {
      if (!live.has(id)) {
        el.pause();
        players.delete(id);
      }
    }
    for (const a of studio.audio) {
      let el = players.get(a.id);
      if (!el) {
        el = new Audio(mediaUrl(a.path));
        el.preload = "auto";
        players.set(a.id, el);
      }
      const inside = t >= a.start && t < a.start + (a.out - a.in);
      if (!playing || !inside || studio.audioMuted) {
        if (!el.paused) el.pause();
        continue;
      }
      el.volume = Math.min(1, a.volume);
      const local = a.in + (t - a.start);
      if (Math.abs(el.currentTime - local) > 0.25) el.currentTime = local;
      if (el.paused) el.play().catch(() => {});
    }
  }

  function stopAudio() {
    for (const el of players.values()) el.pause();
  }

  $effect(() => () => stopAudio());

  // ---- Program monitor: a wall clock drives the playhead; the video follows it.
  function syncProgram(t: number, playing: boolean) {
    const clip = studio.clipAt(t);
    if (!clip) {
      if (!video.paused) video.pause();
      return;
    }
    const r = studio.renders[sceneKey(clip.file, clip.scene)];
    if (!r) return;
    setSrc(mediaUrl(r.video, r.version));
    const local = clip.in + (t - clip.start);
    const drift = Math.abs(video.currentTime - local);
    if (drift > (playing ? 0.2 : 0.005)) video.currentTime = local;
    if (playing && video.paused) video.play().catch(() => {});
    if (!playing && !video.paused) video.pause();
  }

  $effect(() => {
    if (!isProgram || !video) return;
    const t = studio.playhead;
    if (!studio.playing) syncProgram(t, false);
  });

  $effect(() => {
    if (!isProgram || !studio.playing || !video) return;
    const startT = untrack(() => (studio.playhead >= studio.timelineDuration ? 0 : studio.playhead));
    const startAt = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = startT + (now - startAt) / 1000;
      if (t >= studio.timelineDuration) {
        studio.playhead = studio.timelineDuration;
        studio.playing = false;
        video.pause();
        stopAudio();
        return;
      }
      studio.playhead = t;
      syncProgram(t, true);
      syncAudio(t, true);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      video.pause();
      stopAudio();
    };
  });

  export function togglePlay() {
    if (isProgram) {
      if (!studio.timelineDuration) return;
      studio.playing = !studio.playing;
    } else toggleSource();
  }

  function step(frames: number) {
    if (isProgram) {
      studio.playing = false;
      studio.playhead = clamp(studio.playhead + frames / 30, 0, studio.timelineDuration);
    } else if (source) {
      video.pause();
      video.currentTime = clamp(video.currentTime + frames / source.fps, 0, source.duration);
    }
  }

  function toStart() {
    if (isProgram) {
      studio.playing = false;
      studio.playhead = 0;
    } else if (source) video.currentTime = 0;
  }

  function scrub(e: PointerEvent) {
    const bar = e.currentTarget as HTMLElement;
    const move = (ev: PointerEvent) => {
      const rect = bar.getBoundingClientRect();
      const f = clamp((ev.clientX - rect.left) / rect.width, 0, 1);
      if (isProgram) {
        studio.playing = false;
        studio.playhead = f * studio.timelineDuration;
      } else if (source) {
        video.currentTime = f * source.duration;
      }
    };
    bar.setPointerCapture(e.pointerId);
    move(e);
    bar.onpointermove = move;
    bar.onpointerup = () => (bar.onpointermove = null);
  }

  const time = $derived(isProgram ? studio.playhead : sourceTime);
  const total = $derived(isProgram ? studio.timelineDuration : (source?.duration ?? 0));
  const playing = $derived(isProgram ? studio.playing : sourcePlaying);
  const job = $derived(studio.job);
</script>

<section class="viewer" class:fs={fullscreen.target === "viewer"}>
  <header>
    <div class="modes" role="tablist" aria-label="Viewer">
      <button role="tab" aria-selected={!isProgram} class:active={!isProgram} onclick={() => studio.viewerMode = "source"}>
        Scene
      </button>
      <button role="tab" aria-selected={isProgram} class:active={isProgram} onclick={() => { studio.viewerMode = "program"; sourcePlaying = false; }}>
        Timeline
      </button>
    </div>
    <span class="label">
      {#if isProgram}
        {programClip ? programClip.scene : studio.playhead < studio.timelineDuration ? "Gap" : ""}
      {:else if source}
        {sourceName} <span class="meta">{source.height}p · {Math.round(source.fps)} fps</span>
      {/if}
    </span>
  </header>

  <div class="stage">
    <div class="frame" style:--ar="{studio.aspectInfo.w} / {studio.aspectInfo.h}" style:--arn={studio.aspectInfo.w / studio.aspectInfo.h}>
      <!-- svelte-ignore a11y_media_has_caption -->
      <video
        bind:this={video}
        class:hidden={showBlack || (!isProgram && !source)}
        playsinline
        preload="auto"
        ontimeupdate={() => { if (!isProgram) sourceTime = video.currentTime; }}
        onplay={() => { if (!isProgram) sourcePlaying = true; }}
        onpause={() => { if (!isProgram) sourcePlaying = false; }}
        onerror={() => { if (!isProgram && studio.sourceKey) studio.error = { message: "This preview file is missing. Render the scene again." }; }}
      ></video>

      {#if !isProgram && !source && !job}
        <div class="empty">
          {#if studio.currentScene}
            <p>Render <strong>{studio.currentScene.name}</strong> to see it here.</p>
            <button class="btn primary" onclick={() => studio.renderCurrent()}>
              <Icon name="bolt" /> Render scene
            </button>
          {:else}
            <p>Write a Scene class in the editor, then render it.</p>
          {/if}
        </div>
      {:else if isProgram && !studio.clips.length}
        <div class="empty">
          <p>Drag scenes from the project panel onto the timeline to build your video.</p>
        </div>
      {/if}

      {#if job?.kind === "render"}
        <div class="progress" aria-live="polite">
          <span class="spinner"></span>
          <span>Rendering {job.label}</span>
          {#if job.animations}<span class="meta">animation {job.animations}{job.time ? ` · ${job.time.toFixed(1)}s` : ""}</span>{/if}
          <button class="link" onclick={() => studio.cancel()}>Stop</button>
        </div>
      {/if}

      {#if studio.error}
        <div class="error" role="alert">
          <div class="error-head">
            <Icon name="alert" />
            <strong>Render failed</strong>
            <button class="icon-btn" aria-label="Dismiss" onclick={() => (studio.error = null)}><Icon name="close" size={14} /></button>
          </div>
          <p>{studio.error.message}</p>
          {#if /latex|dvisvgm/i.test(studio.error.message) && !studio.worker.latex}
            <button class="link" onclick={() => (ui.latexOpen = true)}>Install LaTeX</button>
          {/if}
          {#if studio.error.line && studio.error.file === studio.activeFile}
            <button class="link" onclick={() => studio.goToLine(studio.error!.line!)}>Go to line {studio.error.line}</button>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <footer>
    <div
      class="scrub"
      role="slider"
      tabindex="0"
      aria-label="Position"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={time}
      onpointerdown={scrub}
    >
      <div class="fill" style:width="{total ? (time / total) * 100 : 0}%"></div>
    </div>
    <div class="transport">
      <span class="tc">{timecode(time)}</span>
      <div class="buttons">
        <button class="icon-btn" aria-label="Go to start" onclick={toStart}><Icon name="toStart" /></button>
        <button class="icon-btn" aria-label="Previous frame" onclick={() => step(-1)}><Icon name="stepBack" /></button>
        <button class="play" aria-label={playing ? "Pause" : "Play"} onclick={togglePlay}>
          <Icon name={playing ? "pause" : "play"} size={18} />
        </button>
        <button class="icon-btn" aria-label="Next frame" onclick={() => step(1)}><Icon name="stepFwd" /></button>
      </div>
      <div class="right">
        <span class="tc dim">{timecode(total)}</span>
        <button
          class="icon-btn"
          title={fullscreen.target === "viewer" ? "Exit full screen (Esc)" : "Full screen (F11)"}
          aria-label={fullscreen.target === "viewer" ? "Exit full screen" : "Full screen preview"}
          onclick={() => fullscreen.toggle("viewer")}
        >
          <Icon name={fullscreen.target === "viewer" ? "shrink" : "expand"} size={15} />
        </button>
      </div>
    </div>
  </footer>
</section>

<style>
  .viewer.fs {
    position: fixed;
    inset: 0;
    z-index: 60;
  }
  .viewer.fs .stage {
    margin: 0;
    border-radius: 0;
  }
  .right {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
  }
  .viewer {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-width: 0;
    background: var(--panel);
  }
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 44px;
    padding: 0 8px;
  }
  .modes {
    display: flex;
    gap: 2px;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg);
  }
  .modes button {
    height: 28px;
    padding: 0 14px;
    border-radius: var(--r-sm);
    color: var(--muted);
    font-size: 12px;
    font-weight: 500;
  }
  .modes button.active {
    background: var(--raised);
    color: var(--text);
  }
  .label {
    font-weight: 500;
  }
  .meta {
    color: var(--faint);
    font-weight: 400;
    margin-left: 6px;
  }

  .stage {
    flex: 1;
    min-height: 0;
    display: grid;
    place-items: center;
    margin: 0 8px;
    padding: 14px;
    container-type: size;
    border-radius: var(--r-md);
    background: #0a0a0b;
  }
  .frame {
    position: relative;
    /* Largest box of the project's shape that fits the stage. */
    width: min(100cqw, 100cqh * var(--arn, 1.7778));
    aspect-ratio: var(--ar, 16 / 9);
    background: #000;
    box-shadow: 0 0 0 1px var(--line);
    container-type: size;
  }
  video {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
  }
  video.hidden {
    visibility: hidden;
  }
  .empty {
    position: absolute;
    inset: 0;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 14px;
    padding: 24px;
    color: var(--muted);
    text-align: center;
  }
  .empty p {
    margin: 0;
    max-width: 34ch;
  }
  .empty strong {
    color: var(--text);
    font-weight: 600;
  }

  .progress {
    position: absolute;
    left: 12px;
    bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: var(--r-md);
    background: rgb(20 21 25 / 0.88);
    backdrop-filter: blur(6px);
    border: 1px solid var(--line);
    font-size: 12px;
  }
  .spinner {
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
  .link {
    color: var(--accent);
    font-weight: 500;
  }
  .link:hover {
    text-decoration: underline;
  }

  .error {
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 12px;
    max-height: 60%;
    overflow: auto;
    padding: 10px 12px;
    border-radius: var(--r-md);
    background: #2a1a1a;
    border: 1px solid #5a2b28;
    user-select: text;
  }
  .error-head {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--danger);
  }
  .error-head .icon-btn {
    margin-left: auto;
  }
  .error p {
    margin: 6px 0;
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
    color: #f3c7c3;
  }

  footer {
    padding: 6px 14px 10px;
  }
  .scrub {
    position: relative;
    height: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
  }
  .scrub::before {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 2px;
    background: var(--raised);
  }
  .fill {
    position: relative;
    height: 3px;
    border-radius: 2px;
    background: var(--accent);
  }
  .fill::after {
    content: "";
    position: absolute;
    right: -5px;
    top: -4px;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: var(--text);
  }
  .transport {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
  }
  .buttons {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .play {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: var(--text);
    color: var(--bg);
    margin: 0 4px;
  }
  .play:hover {
    background: #fff;
  }
  .tc {
    font-family: var(--mono);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
  .tc.dim {
    color: var(--faint);
    justify-self: end;
  }
</style>
