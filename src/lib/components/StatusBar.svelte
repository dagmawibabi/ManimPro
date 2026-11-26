<script lang="ts">
  import { studio } from "#lib/studio.svelte.ts";
  import Icon from "./Icon.svelte";
  import { ui } from "#lib/ui.svelte.ts";

  let showLog = $state(false);
  let logEl: HTMLPreElement | undefined = $state();

  const status = $derived.by(() => {
    if (studio.job?.kind === "export") return { tone: "busy", text: `Exporting ${Math.round((studio.job.fraction ?? 0) * 100)}%` };
    if (studio.job) return { tone: "busy", text: `Rendering ${studio.job.label}` };
    if (studio.worker.status === "ready") return { tone: "ok", text: `Manim ${studio.worker.manim ?? ""} ready` };
    if (studio.worker.status === "starting") return { tone: "busy", text: "Starting Manim…" };
    return { tone: "bad", text: "Manim is not running" };
  });

  $effect(() => {
    studio.logs.length;
    if (showLog && logEl) logEl.scrollTop = logEl.scrollHeight;
  });
</script>

{#if showLog}
  <div class="log">
    <div class="log-head">
      <span class="panel-title">Render log</span>
      <button class="icon-btn" aria-label="Close log" onclick={() => (showLog = false)}><Icon name="close" size={14} /></button>
    </div>
    <pre bind:this={logEl}>{studio.logs.join("\n") || "Nothing logged yet."}</pre>
  </div>
{/if}

<footer>
  <span class="status {status.tone}"><span class="led"></span>{status.text}</span>
  {#if studio.notice}
    <span class="notice" title={studio.notice}>{studio.notice}</span>
    <button class="dismiss" aria-label="Dismiss" onclick={() => (studio.notice = null)}>×</button>
  {:else if studio.definitionHint}
    <span class="notice" title="Defined in Manim's own code">Defined in {studio.definitionHint}</span>
    <button class="dismiss" aria-label="Dismiss" onclick={() => (studio.definitionHint = null)}>×</button>
  {/if}
  <span class="spacer"></span>
  {#if studio.worker.status === "ready" && !studio.worker.latex}
    <button class="log-btn" class:on={studio.worker.latex} onclick={() => (ui.latexOpen = true)} title="LaTeX lets MathTex and Tex render">
      <Icon name="sigma" size={13} /> {studio.worker.latex ? "LaTeX ready" : "Install LaTeX"}
    </button>
  {/if}
  <span class="count">{studio.clips.length} {studio.clips.length === 1 ? "clip" : "clips"}</span>
  <button class="log-btn" class:on={showLog} onclick={() => (showLog = !showLog)}>
    <Icon name="terminal" size={13} /> Log
  </button>
</footer>

<style>
  .notice {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #f1c26b;
  }
  .dismiss {
    color: var(--faint);
    font-size: 14px;
    line-height: 1;
  }
  footer {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 26px;
    padding: 0 12px;
    font-size: 12px;
    color: var(--muted);
    background: var(--bg);
  }
  .status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
  }
  .led {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--faint);
  }
  .ok .led {
    background: var(--ok);
  }
  .busy .led {
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }
  .bad .led {
    background: var(--danger);
  }
  @keyframes pulse {
    50% {
      opacity: 0.35;
    }
  }
  .spacer {
    flex: 1;
  }
  .log-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--muted);
  }
  .log-btn:hover,
  .log-btn.on {
    color: var(--text);
  }
  .log {
    position: fixed;
    right: 12px;
    bottom: 32px;
    width: min(640px, 60vw);
    height: 280px;
    display: flex;
    flex-direction: column;
    z-index: 20;
    background: var(--panel);
    border: 1px solid var(--line-strong);
    border-radius: var(--r-lg);
    box-shadow: 0 18px 40px rgb(0 0 0 / 0.45);
  }
  .log-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 6px 4px 12px;
    border-bottom: 1px solid var(--line);
  }
  pre {
    flex: 1;
    margin: 0;
    padding: 10px 12px;
    overflow: auto;
    font-family: var(--mono);
    font-size: 11.5px;
    line-height: 1.5;
    color: var(--muted);
    user-select: text;
    white-space: pre-wrap;
  }
</style>
