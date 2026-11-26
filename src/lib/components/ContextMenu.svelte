<script lang="ts" module>
  export type MenuItem =
    | {
        label: string;
        icon?: string;
        shortcut?: string;
        disabled?: boolean;
        danger?: boolean;
        hint?: string;
        action: () => void;
      }
    | "separator";
</script>

<script lang="ts">
  import { onMount, tick } from "svelte";
  import Icon from "./Icon.svelte";

  let { x, y, items, onClose }: { x: number; y: number; items: MenuItem[]; onClose: () => void } = $props();

  let menu: HTMLDivElement;
  let pos = $state({ left: 0, top: 0 });

  onMount(async () => {
    // Keep the menu on screen (the root may be zoomed by the interface-size setting).
    const zoom = parseFloat(getComputedStyle(document.documentElement).zoom || "1") || 1;
    const vw = window.innerWidth / zoom;
    const vh = window.innerHeight / zoom;
    pos = { left: x / zoom, top: y / zoom };
    await tick();
    const r = menu.getBoundingClientRect();
    const w = r.width / zoom;
    const h = r.height / zoom;
    pos = {
      left: Math.min(pos.left, vw - w - 8),
      top: pos.top + h > vh - 8 ? Math.max(8, pos.top - h) : pos.top,
    };
    menu.querySelector<HTMLButtonElement>("button:not(:disabled)")?.focus();
  });

  function run(item: Exclude<MenuItem, "separator">) {
    if (item.disabled) return;
    onClose();
    item.action();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const buttons = [...menu.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")];
    const i = buttons.indexOf(document.activeElement as HTMLButtonElement);
    buttons[(i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
  }

  function outside(e: PointerEvent) {
    if (!menu.contains(e.target as Node)) onClose();
  }
</script>

<svelte:window onpointerdown={outside} onblur={onClose} onresize={onClose} />

<div
  bind:this={menu}
  class="menu"
  role="menu"
  tabindex="-1"
  style:left="{pos.left}px"
  style:top="{pos.top}px"
  onkeydown={onKey}
  oncontextmenu={(e) => e.preventDefault()}
>
  {#each items as item, i (i)}
    {#if item === "separator"}
      <div class="sep" role="separator"></div>
    {:else}
      <button role="menuitem" class:danger={item.danger} disabled={item.disabled} title={item.hint} onclick={() => run(item)}>
        <span class="icon">{#if item.icon}<Icon name={item.icon} size={14} />{/if}</span>
        <span class="label">{item.label}</span>
        {#if item.shortcut}<kbd>{item.shortcut}</kbd>{/if}
      </button>
    {/if}
  {/each}
</div>

<style>
  .menu {
    position: fixed;
    z-index: 200;
    min-width: 230px;
    padding: 6px;
    border-radius: 14px;
    background: #1b1b1e;
    border: 1px solid var(--line-strong);
    box-shadow: 0 18px 48px rgb(0 0 0 / 0.55);
    outline: none;
    animation: appear 0.1s ease-out;
  }
  @keyframes appear {
    from {
      opacity: 0;
      transform: scale(0.97);
    }
  }
  button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    height: 32px;
    padding: 0 10px;
    border-radius: 9px;
    text-align: left;
    color: var(--text);
    outline: none;
  }
  button:hover:not(:disabled),
  button:focus-visible {
    background: var(--raised);
  }
  button:disabled {
    color: var(--faint);
    cursor: default;
  }
  button.danger:not(:disabled) {
    color: #f6a19a;
  }
  button.danger:hover:not(:disabled) {
    background: #3a1c1c;
  }
  .icon {
    display: grid;
    place-items: center;
    width: 16px;
    color: var(--muted);
  }
  button.danger .icon {
    color: inherit;
  }
  .label {
    flex: 1;
  }
  kbd {
    font-size: 10.5px;
  }
  .sep {
    height: 1px;
    margin: 5px 6px;
    background: var(--line);
  }
</style>
