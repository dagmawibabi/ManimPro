<script lang="ts">
  import { assistant, providerName, type Chat } from "#lib/assistant.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import Icon from "./Icon.svelte";

  let query = $state("");

  function ago(ms: number) {
    const s = (Date.now() - ms) / 1000;
    if (s < 60) return "now";
    if (s < 3600) return `${Math.floor(s / 60)}m`;
    if (s < 86400) return `${Math.floor(s / 3600)}h`;
    if (s < 86400 * 7) return `${Math.floor(s / 86400)}d`;
    return new Date(ms).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function group(ms: number) {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const day = 86400000;
    if (ms >= start.getTime()) return "Today";
    if (ms >= start.getTime() - day) return "Yesterday";
    if (ms >= start.getTime() - 7 * day) return "Last 7 days";
    return "Older";
  }

  /** The last thing said in a chat, for the one-line preview. */
  function preview(chat: Chat) {
    for (let i = chat.items.length - 1; i >= 0; i--) {
      const it = chat.items[i];
      if ((it.kind === "assistant" || it.kind === "user") && it.text.trim()) {
        return (it.kind === "user" ? "You: " : "") + it.text.replace(/[#*`>_]/g, "").replace(/\s+/g, " ").trim();
      }
    }
    return "No messages yet";
  }

  const messages = (chat: Chat) => chat.items.filter((i) => i.kind === "user").length;

  const filtered = $derived(
    assistant.sortedChats.filter((c) => {
      const q = query.trim().toLowerCase();
      return !q || c.title.toLowerCase().includes(q) || preview(c).toLowerCase().includes(q);
    }),
  );
  const groups = $derived.by(() => {
    const out: { label: string; chats: Chat[] }[] = [];
    for (const c of filtered) {
      const label = group(c.updated);
      const g = out.at(-1);
      if (g?.label === label) g.chats.push(c);
      else out.push({ label, chats: [c] });
    }
    return out;
  });

  function open(id: string) {
    assistant.openChat(id);
    ui.mainTab = "assistant";
  }

  function startNew() {
    assistant.newChat();
    ui.mainTab = "assistant";
  }
</script>

<div class="chats">
  <div class="top">
    <label class="search">
      <Icon name="search" size={13} />
      <input placeholder="Search chats" aria-label="Search chats" bind:value={query} />
    </label>
    <button class="new" title="New chat" aria-label="New chat" disabled={assistant.busy} onclick={startNew}>
      <Icon name="plus" size={14} />
    </button>
  </div>

  {#if !assistant.sortedChats.length}
    <div class="empty">
      <span class="tile"><Icon name="sparkle" size={16} /></span>
      <strong>No chats yet</strong>
      <p>Conversations with your assistant are saved with the project, so you can pick one up later.</p>
      <button class="btn primary" onclick={startNew}>Start a chat</button>
    </div>
  {:else if !filtered.length}
    <p class="none">No chats match “{query}”.</p>
  {/if}

  {#each groups as g (g.label)}
    <div class="label">{g.label}</div>
    <ul>
      {#each g.chats as chat (chat.id)}
        {@const running = assistant.runChatId === chat.id}
        <li class:active={chat.id === assistant.activeId} class:running>
          <button class="item" onclick={() => open(chat.id)}>
            <span class="body">
              <span class="head">
                <span class="title">{chat.title}</span>
                {#if running}
                  <span class="working"><span class="spin"></span>Working</span>
                {:else}
                  <span class="time">{ago(chat.updated)}</span>
                {/if}
              </span>
              <span class="preview">{preview(chat)}</span>
              <span class="meta">{providerName(chat.provider)} · {messages(chat)} {messages(chat) === 1 ? "message" : "messages"}</span>
            </span>
          </button>
          {#if !running}
            <button class="icon-btn del" title="Delete chat" aria-label="Delete chat {chat.title}" onclick={() => assistant.deleteChat(chat.id)}>
              <Icon name="trash" size={13} />
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {/each}
</div>

<style>
  .chats {
    display: flex;
    flex-direction: column;
    gap: 4px;
    height: 100%;
    padding: 10px 8px 14px;
    overflow: auto;
  }
  .top {
    display: flex;
    gap: 6px;
    margin-bottom: 6px;
  }
  .search {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 8px;
    height: 34px;
    padding: 0 10px;
    border-radius: 11px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    color: var(--faint);
  }
  .search:focus-within {
    border-color: var(--line-strong);
  }
  .search input {
    flex: 1;
    min-width: 0;
    padding: 0;
    border: 0;
    background: none;
    outline: none;
    user-select: text;
  }
  .new {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 11px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .new:hover:not(:disabled) {
    background: color-mix(in srgb, var(--accent) 24%, transparent);
  }
  .new:disabled {
    opacity: 0.5;
  }
  .label {
    padding: 10px 10px 4px;
    font-size: 11px;
    font-weight: 600;
    color: var(--faint);
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 2px;
  }
  li {
    position: relative;
    border-radius: 14px;
    border: 1px solid transparent;
    transition: background 0.12s ease, border-color 0.12s ease;
  }
  li:hover {
    background: var(--panel-2);
  }
  li.active {
    background: var(--raised);
    border-color: var(--line);
  }
  .item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    text-align: left;
  }
  .body {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }
  .head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
  }
  .title {
    flex: 1;
    min-width: 0;
    font-weight: 600;
    font-size: 12.5px;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .time {
    flex: none;
    font-size: 11px;
    color: var(--faint);
    font-variant-numeric: tabular-nums;
  }
  li:hover .time {
    visibility: hidden;
  }
  .working {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--accent);
  }
  .preview {
    font-size: 12px;
    line-height: 1.45;
    color: var(--muted);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .meta {
    margin-top: 2px;
    font-size: 11px;
    color: var(--faint);
  }
  .del {
    position: absolute;
    right: 6px;
    top: 7px;
    width: 26px;
    height: 26px;
    opacity: 0;
  }
  li:hover .del,
  .del:focus-visible {
    opacity: 1;
  }
  .spin {
    flex: none;
    width: 11px;
    height: 11px;
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
  .empty {
    display: grid;
    justify-items: center;
    gap: 8px;
    padding: 32px 14px;
    text-align: center;
    color: var(--muted);
  }
  .tile {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .empty strong {
    color: var(--text);
  }
  .empty p {
    margin: 0 0 6px;
    font-size: 12.5px;
    line-height: 1.5;
  }
  .none {
    margin: 10px;
    color: var(--faint);
    font-size: 12px;
  }
</style>
