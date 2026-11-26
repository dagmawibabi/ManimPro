<script lang="ts">
  import { toolKind, type Item } from "#lib/assistant.svelte.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";

  let { items }: { items: Item[] } = $props();

  let open = $state<Record<string, boolean>>({});

  const ICON: Record<string, string> = {
    write: "pencil",
    read: "file",
    search: "search",
    render: "film",
    plan: "list",
    voice: "mic",
    other: "sparkle",
  };

  /** The most useful input fields, plus any code the step wrote. */
  function inputSummary(input: Record<string, any> | undefined) {
    if (!input) return { fields: [] as [string, string][], code: "" };
    const code = String(input.content ?? input.new_string ?? "");
    const fields = Object.entries(input)
      .filter(([k, v]) => !["content", "new_string", "old_string"].includes(k) && v !== undefined && v !== null && v !== "")
      .map(([k, v]) => [k.replace(/_/g, " "), typeof v === "string" ? v : JSON.stringify(v)] as [string, string])
      .slice(0, 6);
    return { fields, code: code.split("\n").slice(0, 60).join("\n") + (code.split("\n").length > 60 ? "\n…" : "") };
  }

  function prettyResult(detail: string) {
    try {
      return JSON.stringify(JSON.parse(detail), null, 2);
    } catch {
      return detail;
    }
  }

  const done = $derived(items.filter((i) => i.status !== "running").length);
</script>

<div class="steps">
  {#if items.length > 2}
    <div class="summary">{done} of {items.length} steps{items.some((i) => i.status === "running") ? "" : " done"}</div>
  {/if}
  {#each items as item (item.id)}
    {@const expandable = !!(item.detail || item.input)}
    {@const isOpen = open[item.id] ?? (item.status === "error" && !!item.detail)}
    <div class="step {item.status}" class:open={isOpen}>
      <button class="row" disabled={!expandable} aria-expanded={expandable ? isOpen : undefined} onclick={() => (open[item.id] = !isOpen)}>
        <span class="kind"><Icon name={ICON[toolKind(item.tool)]} size={13} /></span>
        <span class="text">{item.text}</span>
        <span class="state">
          {#if item.status === "running"}<span class="spin"></span>
          {:else if item.status === "error"}<Icon name="alert" size={13} />
          {:else if item.status === "skipped"}<span class="skip">skipped</span>
          {:else}<Icon name="check" size={13} />{/if}
        </span>
        {#if expandable}<span class="chev"><Icon name="chevron" size={11} /></span>{/if}
      </button>
      {#if isOpen}
        {@const s = inputSummary(item.input)}
        <div class="details">
          {#if s.fields.length}
            <dl>
              {#each s.fields as [k, v] (k)}<dt>{k}</dt><dd>{v}</dd>{/each}
            </dl>
          {/if}
          {#if s.code.trim()}
            <div class="label">Code</div>
            <pre class="code">{s.code}</pre>
          {/if}
          {#if item.detail && (settings.value.showToolDetails || item.status !== "ok")}
            <div class="label">Result</div>
            <pre>{prettyResult(item.detail)}</pre>
          {/if}
        </div>
      {/if}
      {#if item.action === "latex"}
        <button class="fix" onclick={() => (ui.latexOpen = true)}><Icon name="sigma" size={13} /> Install LaTeX</button>
      {/if}
    </div>
  {/each}
</div>

<style>
  .steps {
    display: grid;
    gap: 1px;
    padding: 4px;
    border-radius: 14px;
    background: var(--panel-2);
    border: 1px solid var(--line);
  }
  .summary {
    padding: 6px 10px 4px;
    font-size: 11px;
    color: var(--faint);
  }
  .step {
    border-radius: 10px;
  }
  .step.open {
    background: var(--panel);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    min-height: 34px;
    padding: 4px 10px 4px 6px;
    border-radius: 10px;
    text-align: left;
    color: var(--muted);
  }
  .row:not(:disabled):hover {
    background: var(--raised);
    color: var(--text);
  }
  .row:disabled {
    cursor: default;
  }
  .kind {
    flex: none;
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: var(--bg);
    color: var(--muted);
  }
  .running .kind {
    color: var(--accent);
    background: var(--accent-soft);
  }
  .error .kind {
    color: #f3a59e;
    background: #2a1a1a;
  }
  .text {
    flex: 1;
    min-width: 0;
    font-size: 12.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .running .text {
    color: var(--text);
    background: linear-gradient(90deg, var(--text) 0%, var(--muted) 50%, var(--text) 100%);
    background-size: 200% 100%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 1.8s linear infinite;
  }
  @keyframes shimmer {
    to {
      background-position: -200% 0;
    }
  }
  .state {
    flex: none;
    display: grid;
    place-items: center;
  }
  .ok .state {
    color: var(--ok);
  }
  .error .state {
    color: #f3a59e;
  }
  .skip {
    font-size: 11px;
    color: var(--faint);
  }
  .chev {
    flex: none;
    display: grid;
    color: var(--faint);
    transition: transform 0.15s;
  }
  .open .chev {
    transform: rotate(90deg);
  }
  .details {
    display: grid;
    gap: 6px;
    padding: 2px 12px 12px 40px;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 12px;
    margin: 0;
    font-size: 12px;
  }
  dt {
    color: var(--faint);
  }
  dd {
    margin: 0;
    color: var(--muted);
    font-family: var(--mono);
    font-size: 11.5px;
    word-break: break-all;
  }
  .label {
    font-size: 11px;
    font-weight: 600;
    color: var(--faint);
  }
  pre {
    margin: 0;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--bg);
    border: 1px solid var(--line);
    color: var(--muted);
    font-family: var(--mono);
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 260px;
    overflow: auto;
    user-select: text;
  }
  pre.code {
    color: var(--text);
  }
  .spin {
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
  .fix {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    margin: 0 0 8px 40px;
    padding: 0 12px;
    border-radius: 9px;
    background: var(--raised);
    color: var(--text);
    font-size: 12.5px;
  }
</style>
