<script lang="ts">
  import { onMount } from "svelte";
  import { api, type LatexStatus } from "#lib/api.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import Icon from "./Icon.svelte";

  let { onClose }: { onClose: () => void } = $props();

  let dialog: HTMLDialogElement;
  let status = $state<LatexStatus | null>(null);
  let stage = $state<string | null>(null);
  let detail = $state("");
  let fraction = $state<number | null>(null);
  let failure = $state<string | null>(null);
  let done = $state(false);

  onMount(() => {
    dialog.showModal();
    api.latexStatus().then((s) => {
      status = s;
      if (s.installing) stage = "Installing";
    });
    const off = api.onLatexProgress((p) => {
      stage = p.stage;
      detail = p.detail;
      if (p.fraction !== null) fraction = p.fraction;
    });
    return () => {
      off.then((f) => f());
    };
  });

  async function install() {
    failure = null;
    stage = "Starting";
    fraction = null;
    try {
      await api.latexInstall();
      done = true;
      status = await api.latexStatus();
      studio.ping();
    } catch (e) {
      failure = String(e);
    } finally {
      stage = null;
    }
  }

  function close() {
    if (stage) return;
    dialog.close();
    onClose();
  }
</script>

<dialog bind:this={dialog} oncancel={(e) => { e.preventDefault(); close(); }}>
  <header>
    <h2>LaTeX for math</h2>
    <button class="icon-btn" aria-label="Close" disabled={!!stage} onclick={close}><Icon name="close" /></button>
  </header>

  <div class="content">
    {#if done || (status?.complete && !stage)}
      <div class="ok"><Icon name="check" size={18} /> LaTeX is installed. <code>MathTex</code> and <code>Tex</code> now render.</div>
    {:else}
      <p>
        Formulas made with <code>MathTex</code> and <code>Tex</code> need LaTeX. ManimPro can install TinyTeX for you: about
        75 MB to download, plus the packages Manim uses. It goes into ManimPro's own folder and doesn't change anything
        else on your PC.
      </p>
      {#if stage}
        <div class="progress">
          <span>{stage}{detail ? ` · ${detail}` : ""}</span>
          <div class="bar" class:indeterminate={fraction === null}>
            <div style:width="{(fraction ?? 0.3) * 100}%"></div>
          </div>
        </div>
      {/if}
      {#if failure}<pre class="failure">{failure}</pre>{/if}
    {/if}
  </div>

  <footer>
    {#if done || (status?.complete && !stage)}
      <button class="btn primary" onclick={close}>Done</button>
    {:else}
      <button class="btn" disabled={!!stage} onclick={close}>Not now</button>
      <button class="btn primary" disabled={!!stage || !status} onclick={install}>
        {failure ? "Try again" : "Install LaTeX"}
      </button>
    {/if}
  </footer>
</dialog>

<style>
  dialog {
    width: 460px;
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
    padding: 14px 12px 4px 18px;
  }
  h2 {
    margin: 0;
    font-family: var(--font-display);
    font-size: 16px;
    font-weight: 600;
  }
  .content {
    padding: 6px 18px;
    display: grid;
    gap: 12px;
  }
  p {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
  }
  code {
    font-family: var(--mono);
    color: var(--text);
  }
  .ok {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
  }
  .ok :global(svg) {
    color: var(--ok);
  }
  .progress {
    display: grid;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
  }
  .progress span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
    margin: 0;
    padding: 8px 10px;
    border-radius: var(--r-sm);
    background: #2a1a1a;
    color: #f3c7c3;
    font-family: var(--mono);
    font-size: 11.5px;
    white-space: pre-wrap;
    max-height: 160px;
    overflow: auto;
    user-select: text;
  }
  footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 14px 18px 16px;
  }
</style>
