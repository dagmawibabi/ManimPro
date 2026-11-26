<script lang="ts">
  import { assistant } from "#lib/assistant.svelte.ts";
  import { ui } from "#lib/ui.svelte.ts";
  import ProjectPanel from "./ProjectPanel.svelte";
  import ChatList from "./ChatList.svelte";
  import Icon from "./Icon.svelte";
</script>

<div class="side">
  <div class="tabs" role="tablist" aria-label="Sidebar">
    <button role="tab" aria-selected={ui.sideTab === "project"} class:active={ui.sideTab === "project"} onclick={() => (ui.sideTab = "project")}>
      <Icon name="folder" size={14} /> Project
    </button>
    <button role="tab" aria-selected={ui.sideTab === "chats"} class:active={ui.sideTab === "chats"} onclick={() => (ui.sideTab = "chats")}>
      <Icon name="sparkle" size={13} /> Chats
      {#if assistant.busy}<span class="busy" title="Working"></span>{/if}
    </button>
  </div>
  <div class="body">
    {#if ui.sideTab === "project"}
      <ProjectPanel />
    {:else}
      <ChatList />
    {/if}
  </div>
</div>

<style>
  .side {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--panel);
  }
  .tabs {
    display: flex;
    gap: 2px;
    margin: 8px 8px 0;
    padding: 3px;
    border-radius: 11px;
    background: var(--bg);
  }
  .tabs button {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 28px;
    border-radius: var(--r-sm);
    color: var(--muted);
    font-weight: 500;
    font-size: 12.5px;
  }
  .tabs button:hover {
    color: var(--text);
  }
  .tabs button.active {
    background: var(--raised);
    color: var(--text);
  }
  .busy {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.3;
    }
  }
  .body {
    flex: 1;
    min-height: 0;
  }
</style>
