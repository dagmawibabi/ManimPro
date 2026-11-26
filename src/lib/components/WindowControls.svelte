<script lang="ts">
  import { onMount } from "svelte";
  import { getCurrentWindow } from "@tauri-apps/api/window";

  const win = getCurrentWindow();
  let maximized = $state(false);

  onMount(() => {
    const sync = () => win.isMaximized().then((m) => (maximized = m)).catch(() => {});
    sync();
    const off = win.onResized(sync);
    return () => {
      off.then((f) => f());
    };
  });
</script>

<!-- Windows-style caption buttons, drawn by the app so they sit in its own top bar. -->
<div class="controls">
  <button aria-label="Minimize" title="Minimize" onclick={() => win.minimize()}>
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M0 5h10" stroke="currentColor" stroke-width="1" /></svg>
  </button>
  <button aria-label={maximized ? "Restore" : "Maximize"} title={maximized ? "Restore" : "Maximize"} onclick={() => win.toggleMaximize()}>
    {#if maximized}
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1">
        <rect x="0.5" y="2.5" width="7" height="7" rx="1" /><path d="M2.5 2.5V1.5a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-1" />
      </svg>
    {:else}
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1"><rect x="0.5" y="0.5" width="9" height="9" rx="1.2" /></svg>
    {/if}
  </button>
  <button class="close" aria-label="Close" title="Close" onclick={() => win.close()}>
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M0.5 0.5l9 9M9.5 0.5l-9 9" stroke="currentColor" stroke-width="1" /></svg>
  </button>
</div>

<style>
  .controls {
    display: flex;
    align-self: stretch;
    margin-left: 6px;
  }
  button {
    display: grid;
    place-items: center;
    width: 46px;
    height: 100%;
    min-height: 36px;
    color: var(--muted);
    transition: background 0.1s, color 0.1s;
  }
  button:hover {
    background: var(--raised);
    color: var(--text);
  }
  button.close:hover {
    background: #c42b1c;
    color: #fff;
  }
  button:focus-visible {
    outline: none;
    background: var(--raised);
  }
</style>
