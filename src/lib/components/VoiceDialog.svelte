<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "#lib/api.ts";
  import { voice, VOICE_MODELS } from "#lib/voice.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import { basename } from "#lib/api.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import { timecode } from "#lib/time.ts";
  import Icon from "./Icon.svelte";
  import Picker from "./Picker.svelte";

  let { onClose }: { onClose: () => void } = $props();

  let dialog: HTMLDialogElement;
  let text = $state("");
  let name = $state("");
  let speed = $state(1);
  let stability = $state(0.5);
  let place = $state(true);
  let hasKey = $state<boolean | null>(null);
  let quota = $state<{ used: number; limit: number; tier: string } | null>(null);
  let failure = $state<string | null>(null);
  let done = $state<string | null>(null);
  let preview: HTMLAudioElement | null = null;
  let previewing = $state(false);

  const voiceItems = $derived(
    voice.voices.map((v) => ({
      value: v.id,
      label: v.name,
      sub: [v.category, ...v.labels].filter(Boolean).slice(0, 4).join(" · "),
      group: v.category === "premade" ? "Default voices" : "Your voices",
      preview: v.preview_url ?? undefined,
    })),
  );
  const left = $derived(quota ? quota.limit - quota.used : null);

  const editing = ui.voiceEdit;

  onMount(() => {
    dialog.showModal();
    if (editing) {
      place = false;
      voice.metaFor(editing.path).then((m) => {
        if (!m) return;
        text = m.text;
        speed = m.speed ?? 1;
        stability = m.stability ?? 0.5;
        voice.setVoice(m.voiceId);
        voice.setModel(m.modelId);
        name = basename(editing.path).replace(/\.[^.]+$/, "");
      });
    }
    api.apiKeyHint("elevenlabs").then((h) => {
      hasKey = !!h;
      if (h) {
        voice.load();
        api.voiceAccount().then((q) => (quota = q)).catch(() => {});
      }
    });
    return () => preview?.pause();
  });

  function togglePreview() {
    const url = voice.current?.preview_url;
    if (!url) return;
    if (previewing && preview) {
      preview.pause();
      previewing = false;
      return;
    }
    preview?.pause();
    preview = new Audio(url);
    preview.onended = () => (previewing = false);
    preview.play().then(() => (previewing = true)).catch(() => (previewing = false));
  }

  async function generate() {
    failure = null;
    done = null;
    try {
      const r = await voice.generate(text, { name: name || undefined, speed, stability, place: place && !editing?.clipId, at: studio.playhead });
      done = r.path.split(/[\\/]/).pop() ?? r.path;
      // Regenerating from a clip: the clip switches to the new take, same position.
      if (editing?.clipId) await studio.replaceAudioSource(editing.clipId, r.path);
      api.voiceAccount().then((q) => (quota = q)).catch(() => {});
    } catch (e) {
      failure = String((e as { message?: string }).message ?? e);
    }
  }

  function close() {
    if (voice.generating) return;
    dialog.close();
    onClose();
  }
</script>

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <header>
    <h2><Icon name="mic" size={16} /> {editing ? "Edit voiceover" : "Generate voiceover"}</h2>
    <button class="icon-btn" aria-label="Close" disabled={voice.generating} onclick={close}><Icon name="close" /></button>
  </header>

  {#if hasKey === false}
    <div class="body">
      <p class="note">Voiceovers use ElevenLabs. Add your API key in Settings, under Accounts, to start.</p>
    </div>
    <footer>
      <button class="btn" onclick={close}>Not now</button>
      <button class="btn primary" onclick={() => { close(); settings.show("accounts"); }}>Open Accounts</button>
    </footer>
  {:else}
    <div class="body">
      <label class="field">
        <span>Script</span>
        <textarea rows="6" bind:value={text} placeholder="What should the narrator say?"></textarea>
        <span class="count">
          {text.length.toLocaleString()} characters{#if left !== null} · {left.toLocaleString()} left this period ({quota?.tier}){/if}
        </span>
      </label>

      <div class="grid">
        <div class="field">
          <span>Voice</span>
          <div class="voice-row">
            <div class="grow">
              <Picker
                label="Voice"
                variant="field"
                width={340}
                items={voiceItems}
                value={voice.current?.id ?? ""}
                placeholder={voice.loading ? "Loading voices…" : "Choose a voice"}
                searchable
                onChange={(id) => voice.setVoice(id)}
              />
            </div>
            <button class="icon-btn" title="Hear this voice" aria-label="Preview voice" disabled={!voice.current?.preview_url} onclick={togglePreview}>
              <Icon name={previewing ? "pauseFill" : "play"} size={13} />
            </button>
          </div>
          {#if voice.error}<span class="error">{voice.error}</span>{/if}
        </div>
        <div class="field">
          <span>Model</span>
          <Picker label="Model" variant="field" width={320} items={VOICE_MODELS} value={voice.modelId} onChange={(m) => voice.setModel(m)} />
        </div>
        <label class="field">
          <span>Speed · {speed.toFixed(2)}×</span>
          <input type="range" min="0.7" max="1.2" step="0.05" bind:value={speed} />
        </label>
        <label class="field">
          <span>Stability · {Math.round(stability * 100)}%</span>
          <input type="range" min="0" max="1" step="0.05" bind:value={stability} />
          <span class="hint">Lower is more expressive, higher is steadier.</span>
        </label>
        <label class="field">
          <span>File name</span>
          <input placeholder="Optional, e.g. intro-narration" bind:value={name} />
        </label>
        {#if editing?.clipId}
          <p class="hint replace">Regenerating replaces the clip on the timeline with the new take. The old file stays in assets/audio.</p>
        {:else}
          <label class="check">
            <input type="checkbox" bind:checked={place} />
            Put it on the audio track at {timecode(studio.playhead)}
          </label>
        {/if}
      </div>

      {#if failure}<p class="error">{failure}</p>{/if}
      {#if done}<p class="done"><Icon name="check" size={14} /> Saved {done} in assets/audio{place ? " and added it to the timeline" : ""}.</p>{/if}
    </div>
    <footer>
      <button class="btn" disabled={voice.generating} onclick={close}>{done ? "Close" : "Cancel"}</button>
      <button class="btn primary" disabled={!text.trim() || voice.generating || !voice.current} onclick={generate}>
        {#if voice.generating}<span class="spin"></span> Generating…{:else}<Icon name="mic" size={14} /> {editing ? "Regenerate" : "Generate"}{/if}
      </button>
    </footer>
  {/if}
</dialog>

<style>
  dialog {
    width: min(640px, 92vw);
    padding: 0;
    border: 1px solid var(--line-strong);
    border-radius: 22px;
    background: var(--panel);
    color: var(--text);
    box-shadow: 0 30px 80px rgb(0 0 0 / 0.6);
  }
  dialog::backdrop {
    background: rgb(5 5 6 / 0.6);
    backdrop-filter: blur(3px);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 14px 4px 22px;
  }
  h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
  }
  .body {
    display: grid;
    gap: 16px;
    padding: 10px 22px;
  }
  .field {
    display: grid;
    gap: 6px;
    min-width: 0;
  }
  .field > span:first-child {
    font-size: 12px;
    color: var(--muted);
  }
  textarea {
    width: 100%;
    resize: vertical;
    padding: 12px 14px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: var(--panel-2);
    color: var(--text);
    font: inherit;
    font-size: 14px;
    line-height: 1.55;
    user-select: text;
  }
  textarea:focus {
    outline: none;
    border-color: var(--line-strong);
  }
  .count,
  .hint {
    font-size: 11.5px;
    color: var(--faint);
  }
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px 16px;
  }
  .voice-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .grow {
    flex: 1;
    min-width: 0;
    display: flex;
  }
  input[type="range"] {
    padding: 0;
    border: 0;
    background: none;
    accent-color: var(--accent);
  }
  .field input:not([type]) {
    height: 34px;
    border-radius: 10px;
    user-select: text;
  }
  .replace {
    align-self: end;
    margin: 0;
  }
  .check {
    display: flex;
    align-items: center;
    gap: 8px;
    align-self: end;
    padding-bottom: 8px;
    color: var(--muted);
    font-size: 12.5px;
  }
  .check input {
    accent-color: var(--accent);
  }
  .note {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
  }
  .error {
    margin: 0;
    color: #f3c7c3;
    font-size: 12.5px;
  }
  .done {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    color: var(--ok);
    font-size: 12.5px;
  }
  footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 14px 22px 18px;
  }
  .spin {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid rgb(0 0 0 / 0.2);
    border-top-color: var(--accent-ink);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
