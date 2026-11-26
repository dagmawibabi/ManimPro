<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { api, mediaUrl, type MusicTrack } from "#lib/api.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import { shortTime } from "#lib/time.ts";
  import Icon from "./Icon.svelte";

  let { onClose }: { onClose: () => void } = $props();

  let dialog: HTMLDialogElement;
  let tracks = $state<MusicTrack[]>([]);
  let error = $state<string | null>(null);
  let playing = $state<string | null>(null);
  let busy = $state<string | null>(null);
  let added = $state<Record<string, string>>({});
  let player: HTMLAudioElement | null = null;

  onMount(async () => {
    dialog.showModal();
    try {
      tracks = (await api.musicLibrary()).tracks;
    } catch (e) {
      error = String(e);
    }
  });
  onDestroy(() => player?.pause());

  function toggle(t: MusicTrack) {
    if (playing === t.id) {
      player?.pause();
      playing = null;
      return;
    }
    player?.pause();
    player = new Audio(mediaUrl(t.path));
    player.onended = () => (playing = null);
    player.play();
    playing = t.id;
  }

  async function use(t: MusicTrack, place: boolean) {
    if (!studio.dir) return;
    busy = t.id;
    error = null;
    try {
      if (place) {
        await studio.addAudio(t.path, 0);
        added[t.id] = "Added to the timeline";
      } else {
        const path = await api.importMedia(studio.dir, t.path);
        if (!studio.audioFiles.includes(path)) studio.audioFiles = [...studio.audioFiles, path].sort();
        added[t.id] = "Added to Audio";
      }
    } catch (e) {
      error = String(e);
    } finally {
      busy = null;
    }
  }

  function close() {
    player?.pause();
    dialog.close();
    onClose();
  }
</script>

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <header>
    <h2><Icon name="music" size={16} /> Music library</h2>
    <button class="icon-btn" aria-label="Close" onclick={close}><Icon name="close" /></button>
  </header>
  <p class="intro">Original tracks made for ManimPro. They're free to use in any video, commercial ones included (CC0), with no credit needed.</p>
  {#if error}<p class="error">{error}</p>{/if}
  <div class="list">
    {#each tracks as t (t.id)}
      <div class="track" class:on={playing === t.id}>
        <button class="play" aria-label={playing === t.id ? `Pause ${t.title}` : `Play ${t.title}`} onclick={() => toggle(t)}>
          <Icon name={playing === t.id ? "pauseFill" : "play"} size={14} />
        </button>
        <span class="text">
          <strong>{t.title}</strong>
          <span>{t.mood}</span>
          <span class="facts">{shortTime(t.duration)} · {t.bpm} BPM</span>
        </span>
        {#if added[t.id]}
          <span class="done"><Icon name="check" size={12} /> {added[t.id]}</span>
        {:else}
          <div class="actions">
            <button class="btn ghost" disabled={busy === t.id} onclick={() => use(t, false)}>Add to Audio</button>
            <button class="btn" disabled={busy === t.id} onclick={() => use(t, true)}><Icon name="plus" size={12} /> Timeline</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>
</dialog>

<style>
  dialog {
    width: min(640px, calc(100vw - 40px));
    max-height: min(680px, calc(100vh - 60px));
    padding: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line-strong);
    border-radius: var(--r-lg);
    background: var(--panel);
    color: var(--text);
  }
  dialog:not([open]) {
    display: none;
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 0.55);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 18px 6px;
  }
  h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
  }
  .intro {
    margin: 0 18px 12px;
    color: var(--muted);
    font-size: 12.5px;
    line-height: 1.5;
  }
  .error {
    margin: 0 18px 10px;
    color: #f3c7c3;
    font-size: 12px;
  }
  .list {
    overflow: auto;
    padding: 0 12px 14px;
    display: grid;
    gap: 4px;
  }
  .track {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    border-radius: 12px;
  }
  .track:hover,
  .track.on {
    background: var(--panel-2);
  }
  .play {
    flex: none;
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }
  .text strong {
    font-size: 13px;
  }
  .text span {
    font-size: 12px;
    color: var(--muted);
  }
  .text .facts {
    font-size: 11px;
    color: var(--faint);
  }
  .actions {
    display: flex;
    gap: 6px;
  }
  .done {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--ok);
  }
</style>
