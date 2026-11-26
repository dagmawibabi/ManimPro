<script lang="ts">
  import { assistant, PROVIDERS } from "#lib/assistant.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import { studio } from "#lib/studio.svelte.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import PromptBox from "./PromptBox.svelte";
  import Markdown from "./Markdown.svelte";
  import ToolSteps from "./ToolSteps.svelte";
  import PlanCard from "./PlanCard.svelte";
  import type { Item } from "#lib/assistant.svelte.ts";
  import { mediaUrl } from "#lib/api.ts";
  import Icon from "./Icon.svelte";
  import { ask } from "@tauri-apps/plugin-dialog";

  let list: HTMLDivElement | undefined = $state();
  let box: PromptBox | undefined = $state();

  const info = $derived(PROVIDERS.find((p) => p.id === assistant.provider)!);
  const st = $derived(assistant.current);

  const suggestions = [
    "Make the title bigger and color it blue",
    "Add a new scene that explains what a derivative is",
    "Put every scene on the timeline in a sensible order",
    "Slow the animations down and add pauses between steps",
  ];

  /** Consecutive tool steps share one card; everything else stands alone. */
  type Block = { kind: "steps"; id: string; items: Item[] } | { kind: "item"; id: string; item: Item };
  const blocks = $derived.by(() => {
    const out: Block[] = [];
    for (const it of assistant.items) {
      const last = out.at(-1);
      if (it.kind === "tool") {
        if (last?.kind === "steps") last.items.push(it);
        else out.push({ kind: "steps", id: it.id, items: [it] });
      } else {
        out.push({ kind: "item", id: it.id, item: it });
      }
    }
    return out;
  });

  $effect(() => {
    assistant.items.length;
    assistant.items.at(-1)?.text;
    if (list) list.scrollTop = list.scrollHeight;
  });

  let reverting = $state<string | null>(null);
  async function revert(id: string) {
    const ok = await ask("Undo everything the assistant changed in this request? Files it edited go back to how they were, files it added are moved aside, and the timeline is restored.", {
      title: "Undo changes",
      kind: "warning",
    });
    if (!ok) return;
    reverting = id;
    try {
      await assistant.revert(id);
    } catch (e) {
      studio.error = { message: String(e) };
    } finally {
      reverting = null;
    }
  }
</script>

<div class="panel">
  {#if st && (!st.installed || !st.signed_in)}
    <div class="notice">
      {#if !st.installed}
        <strong>{info.name} isn't installed</strong>
        <span>{st.install_hint}</span>
        <div class="actions"><button class="btn" onclick={() => assistant.refresh()}><Icon name="refresh" size={13} /> Check again</button></div>
      {:else}
        <strong>Sign in to {info.name}</strong>
        <span>{info.plan}. You sign in through {info.name}'s own window; ManimPro never sees your password.</span>
        <div class="actions">
          <button class="btn primary" onclick={() => assistant.login()}>Sign in</button>
          <button class="btn ghost" onclick={() => assistant.refresh()}>Check again</button>
        </div>
      {/if}
    </div>
  {/if}

  <div class="log" bind:this={list} aria-live="polite">
    <div class="inner">
      {#if !assistant.items.length}
        <div class="empty">
          <span class="mark"><Icon name="sparkle" size={16} /></span>
          <h3>What should change?</h3>
          <p>The assistant edits your scenes, renders them to check its work, and fixes what breaks.</p>
          <div class="chips">
            {#each suggestions as s (s)}
              <button class="chip" onclick={() => box?.fill(s)}>{s}</button>
            {/each}
          </div>
        </div>
      {/if}
      {#each blocks as block (block.id)}
        {#if block.kind === "steps"}
          <ToolSteps items={block.items} />
        {:else}
        {@const item = block.item}
        {#if item.kind === "user"}
          <div class="msg user">
            {#if item.files?.length}
              <span class="files">
                {#each item.files as f (f)}
                  {#if /\.(png|jpe?g|gif|webp)$/i.test(f)}<img src={mediaUrl(f)} alt="" />{:else}<span class="file-chip"><Icon name="file" size={12} /> {f.split(/[\\/]/).pop()}</span>{/if}
                {/each}
              </span>
            {/if}
            {item.text}
          </div>
        {:else if item.kind === "assistant"}
          <div class="msg bot"><Markdown text={item.text} /></div>
        {:else if item.kind === "changes" && item.changes}
          {@const files = item.changes.filter((c) => c.path !== "project.json")}
          {@const timeline = item.changes.some((c) => c.path === "project.json")}
          <div class="changes" class:reverted={item.reverted}>
            <div class="changes-head">
              <Icon name="pencil" size={13} />
              <span>
                {item.reverted ? "Undone: " : ""}{files.length} {files.length === 1 ? "file" : "files"} changed{timeline ? " and the timeline" : ""}
              </span>
              {#if !item.reverted}
                <button
                  class="fix"
                  disabled={assistant.busy || reverting === item.id}
                  title="Put the files and timeline back the way they were before this request"
                  onclick={() => revert(item.id)}
                >
                  <Icon name="undo" size={12} /> {reverting === item.id ? "Undoing…" : "Undo these changes"}
                </button>
              {/if}
            </div>
            {#if files.length}
              <ul>
                {#each files.slice(0, 8) as c (c.path)}
                  <li><span class="st {c.status}">{c.status === "added" ? "new" : c.status === "deleted" ? "deleted" : "edited"}</span>{c.path}</li>
                {/each}
                {#if files.length > 8}<li class="more">and {files.length - 8} more</li>{/if}
              </ul>
            {/if}
          </div>
        {:else if item.kind === "plan" && item.plan}
          <PlanCard plan={item.plan} />
        {:else if item.kind === "error"}
          <div class="msg error">
            <span>{item.text}</span>
            {#if item.action === "login"}
              <button class="fix" onclick={() => assistant.login()}>Sign in again</button>
            {:else if item.action === "latex"}
              <button class="fix" onclick={() => (ui.latexOpen = true)}>Install LaTeX</button>
            {/if}
          </div>
        {:else}
          <div class="note">{item.text}</div>
        {/if}
        {/if}
      {/each}
      {#if assistant.busy && assistant.runChatId === assistant.activeId && !assistant.items.some((i) => i.kind === "tool" && i.status === "running")}
        <div class="working"><span class="spin"></span><span>{assistant.items.at(-1)?.kind === "user" ? "Thinking…" : "Working…"}</span></div>
      {/if}
    </div>
  </div>

  <div class="composer">
    <PromptBox bind:this={box} onSubmit={(t, files) => assistant.send(t, files)} disabled={!st?.signed_in} placeholder="Ask for a change…" />
  </div>
</div>

<style>
  .changes {
    display: grid;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    font-size: 12.5px;
  }
  .changes.reverted {
    opacity: 0.65;
  }
  .changes-head {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted);
  }
  .changes-head span {
    flex: 1;
  }
  .changes ul {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 3px;
  }
  .changes li {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text);
    font-family: var(--mono, Consolas, monospace);
    font-size: 11.5px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .changes li.more {
    color: var(--faint);
    font-family: inherit;
  }
  .st {
    flex: none;
    width: 52px;
    padding: 1px 0;
    border-radius: 6px;
    text-align: center;
    font-family: inherit;
    font-size: 10.5px;
    background: var(--raised);
    color: var(--muted);
  }
  .st.added {
    color: #9fd88a;
  }
  .st.deleted {
    color: #f3a39b;
  }
  .panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--panel);
  }
  .notice {
    display: grid;
    gap: 6px;
    margin: 12px 12px 0;
    padding: 12px 14px;
    border-radius: var(--r-md);
    background: var(--panel-2);
    border: 1px solid var(--line);
    font-size: 12.5px;
    color: var(--muted);
    line-height: 1.5;
  }
  .notice strong {
    color: var(--text);
    font-size: 13px;
  }
  .actions {
    display: flex;
    gap: 6px;
    margin-top: 4px;
  }
  .log {
    flex: 1;
    min-height: 0;
    overflow: auto;
    user-select: text;
  }
  .inner {
    max-width: 760px;
    margin: 0 auto;
    padding: 18px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .empty {
    display: grid;
    justify-items: center;
    text-align: center;
    gap: 8px;
    padding: 40px 8px 10px;
    color: var(--muted);
  }
  .mark {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 12px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .empty h3 {
    margin: 6px 0 0;
    font-family: var(--font-display);
    font-size: 17px;
    font-weight: 600;
    color: var(--text);
  }
  .empty p {
    margin: 0 0 8px;
    line-height: 1.5;
    max-width: 44ch;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 6px;
  }
  .chip {
    padding: 7px 12px;
    border-radius: 999px;
    border: 1px solid var(--line-strong);
    color: var(--muted);
    font-size: 12.5px;
  }
  .chip:hover {
    color: var(--text);
    background: var(--panel-2);
  }
  .msg {
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
  }
  .user {
    align-self: flex-end;
    max-width: 85%;
    padding: 9px 14px;
    border-radius: 18px 18px 6px 18px;
    background: var(--raised);
  }
  .files {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
  }
  .files img {
    max-width: 160px;
    max-height: 110px;
    border-radius: 10px;
    object-fit: cover;
  }
  .file-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 8px;
    background: var(--panel);
    font-size: 12px;
  }
  .bot {
    padding: 0 2px;
    white-space: normal;
  }
  .error {
    display: grid;
    gap: 8px;
    justify-items: start;
    padding: 10px 14px;
    border-radius: var(--r-md);
    background: #24171a;
    border: 1px solid #47262a;
    color: #f3c7c3;
    font-size: 12.5px;
  }
  .fix {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 12px;
    border-radius: 9px;
    background: var(--raised);
    color: var(--text);
    font-size: 12.5px;
    font-weight: 500;
    justify-self: start;
    align-self: flex-start;
  }
  .fix:hover {
    background: var(--line-strong);
  }
  .note {
    color: var(--faint);
    font-size: 12px;
  }
  .working {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 10px;
    color: var(--muted);
    font-size: 12.5px;
    animation: breathe 1.6s ease-in-out infinite;
  }
  @keyframes breathe {
    50% {
      opacity: 0.55;
    }
  }
  .spin {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    border: 2px solid var(--accent-soft);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
    flex: none;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .composer {
    width: 100%;
    max-width: 792px;
    margin: 0 auto;
    padding: 4px 16px 16px;
  }
</style>
