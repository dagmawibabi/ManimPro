<script lang="ts">
  import "@fontsource-variable/geist";
  import "../app.css";
  import { onMount } from "svelte";
  import { api } from "#lib/api.ts";
  import { settings } from "#lib/settings.svelte.ts";
  import SettingsDialog from "#lib/components/SettingsDialog.svelte";
  let { children } = $props();

  onMount(() => {
    settings.apply();
    // Other apps' MCP clients find a running ManimPro through this (Settings > Assistant).
    if (settings.value.shareMcp) api.mcpShare(true).catch(() => {});
  });

  function onKey(e: KeyboardEvent) {
    if (e.ctrlKey && e.key === ",") {
      e.preventDefault();
      settings.show();
    }
  }
</script>

<svelte:window onkeydown={onKey} />

{@render children()}

{#if settings.open}
  <SettingsDialog />
{/if}
