<script lang="ts">
  import { onMount, tick } from "svelte";
  import { studio } from "#lib/studio.svelte.ts";
  import { captionsFromVoiceovers } from "#lib/captions.ts";
  import { timecode } from "#lib/time.ts";
  import Icon from "./Icon.svelte";

  let { focus = null, onClose }: { focus?: string | null; onClose: () => void } = $props();

  let dialog: HTMLDialogElement;
  let note = $state<string | null>(null);
  let busy = $state(false);

  onMount(async () => {
    dialog.showModal();
    if (focus) {
      await tick();
      dialog.querySelector<HTMLTextAreaElement>(`[data-id="${focus}"] textarea`)?.focus();
    }
  });

  function close() {
    dialog.close();
    onClose();
  }

  async function generate() {
    busy = true;
    note = null;
    try {
      const n = await captionsFromVoiceovers();
      note = n
        ? `Made ${n} captions from the voiceovers. Timing follows the text, so nudge any that are early or late.`
        : "No generated voiceovers on the timeline yet. Generate narration first, or add captions by hand.";
    } catch (e) {
      note = String(e);
    } finally {
      busy = false;
    }
  }

  async function add() {
    const c = studio.addCaption(studio.playhead);
    await tick();
    dialog.querySelector<HTMLTextAreaElement>(`[data-id="${c.id}"] textarea`)?.select();
  }

  const num = (v: string) => Math.max(0, Math.round(parseFloat(v) * 10) / 10 || 0);
</script>

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <header>
    <h2><Icon name="captions" size={16} /> Captions</h2>
    <button class="icon-btn" aria-label="Close" onclick={close}><Icon name="close" /></button>
  </header>

  <div class="actions">
    <button class="btn" disabled={busy} onclick={generate}><Icon name="mic" size={13} /> {busy ? "Making…" : "From voiceovers"}</button>
    <button class="btn" onclick={add}><Icon name="plus" size={13} /> Add at playhead</button>
    <span class="spacer"></span>
    {#if studio.captions.length}
      <button class="btn ghost" onclick={() => studio.setCaptions([])}>Clear all</button>
    {/if}
  </div>
  {#if note}<p class="note">{note}</p>{/if}

  <div class="list">
    {#each studio.captions as c (c.id)}
      <div class="cap" data-id={c.id} class:now={studio.playhead >= c.start && studio.playhead < c.end}>
        <div class="times">
          <label>
            <span>From</span>
            <input type="number" step="0.1" min="0" value={c.start.toFixed(1)} onchange={(e) => studio.updateCaption(c.id, { start: num(e.currentTarget.value) })} />
          </label>
          <label>
            <span>To</span>
            <input type="number" step="0.1" min="0" value={c.end.toFixed(1)} onchange={(e) => studio.updateCaption(c.id, { end: num(e.currentTarget.value) })} />
          </label>
          <button class="icon-btn" title="Jump here" aria-label="Move the playhead to this caption" onclick={() => { studio.viewerMode = "program"; studio.playhead = c.start; }}>
            <Icon name="play" size={12} />
          </button>
        </div>
        <textarea rows="2" value={c.text} onchange={(e) => studio.updateCaption(c.id, { text: e.currentTarget.value })}></textarea>
        <button class="icon-btn del" title="Delete caption" aria-label="Delete caption" onclick={() => studio.removeCaption(c.id)}><Icon name="trash" size={13} /></button>
      </div>
    {:else}
      <p class="empty">
        No captions yet. Make them from your voiceovers, or add lines by hand. They show in the preview and can be exported
        as a subtitle file or burned into the video.
      </p>
    {/each}
  </div>
  <footer>
    <span class="hint">{studio.captions.length} {studio.captions.length === 1 ? "caption" : "captions"} · playhead {timecode(studio.playhead)}</span>
    <button class="btn primary" onclick={close}>Done</button>
  </footer>
</dialog>

<style>
  dialog {
    width: min(620px, calc(100vw - 40px));
    max-height: min(720px, calc(100vh - 60px));
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
    padding: 16px 18px 8px;
  }
  h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
  }
  .actions {
    display: flex;
    gap: 8px;
    padding: 6px 18px 10px;
  }
  .spacer {
    flex: 1;
  }
  .note {
    margin: 0 18px 10px;
    font-size: 12px;
    color: var(--muted);
  }
  .list {
    flex: 1;
    overflow: auto;
    padding: 0 18px 8px;
    display: grid;
    gap: 8px;
    align-content: start;
  }
  .cap {
    position: relative;
    display: grid;
    gap: 8px;
    padding: 10px 40px 10px 12px;
    border-radius: 12px;
    background: var(--panel-2);
    border: 1px solid var(--line);
  }
  .cap.now {
    border-color: var(--accent);
  }
  .times {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .times label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    color: var(--faint);
  }
  .times input {
    width: 74px;
    height: 28px;
    border-radius: 8px;
    user-select: text;
  }
  textarea {
    resize: vertical;
    min-height: 44px;
    border-radius: 9px;
    font: inherit;
    font-size: 13px;
    user-select: text;
  }
  .del {
    position: absolute;
    top: 8px;
    right: 8px;
  }
  .empty {
    margin: 12px 0;
    color: var(--faint);
    font-size: 12.5px;
    line-height: 1.5;
  }
  footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px 16px;
    border-top: 1px solid var(--line);
  }
  .hint {
    font-size: 12px;
    color: var(--faint);
  }
</style>
