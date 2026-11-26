<script lang="ts" module>
  export type PickerItem = {
    value: string;
    label: string;
    /** Second line: details such as context size or price. */
    sub?: string;
    /** Small tags shown on the right (e.g. "reasoning", "free"). */
    tags?: string[];
    group?: string;
    disabled?: boolean;
    /** Audio URL: shows a play button that previews it without choosing the item. */
    preview?: string;
  };
</script>

<script lang="ts">
  import { tick } from "svelte";
  import Icon from "./Icon.svelte";

  let {
    items,
    value,
    onChange,
    label,
    placeholder = "Choose…",
    searchable = items.length > 12,
    variant = "ghost",
    width = 320,
    align = "left",
    prefix,
  }: {
    items: PickerItem[];
    value: string;
    onChange: (v: string) => void;
    label: string;
    placeholder?: string;
    searchable?: boolean;
    variant?: "ghost" | "field";
    width?: number;
    align?: "left" | "right";
    prefix?: string;
  } = $props();

  let open = $state(false);
  let query = $state("");
  let active = $state(0);
  let button: HTMLButtonElement;
  let pop: HTMLDivElement | undefined = $state();
  let searchEl: HTMLInputElement | undefined = $state();
  let pos = $state({ top: 0, left: 0, maxH: 360, up: false });
  let sample: HTMLAudioElement | null = null;
  let sampling = $state<string | null>(null);

  function playSample(e: MouseEvent, item: PickerItem) {
    e.stopPropagation();
    if (sampling === item.value) {
      sample?.pause();
      sampling = null;
      return;
    }
    sample?.pause();
    sample = new Audio(item.preview);
    sample.onended = () => (sampling = null);
    sampling = item.value;
    sample.play().catch(() => (sampling = null));
  }

  function stopSample() {
    sample?.pause();
    sampling = null;
  }

  const selected = $derived(items.find((i) => i.value === value));
  const shown = $derived.by(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((i) => `${i.label} ${i.sub ?? ""} ${i.value} ${(i.tags ?? []).join(" ")}`.toLowerCase().includes(q));
  });

  async function toggle() {
    if (open) return close();
    const r = button.getBoundingClientRect();
    const zoom = parseFloat(getComputedStyle(document.documentElement).zoom || "1") || 1;
    const vh = window.innerHeight / zoom;
    const vw = window.innerWidth / zoom;
    const top = r.bottom / zoom + 6;
    const below = vh - top - 12;
    const above = r.top / zoom - 18;
    const up = below < 240 && above > below;
    let left = align === "right" ? r.right / zoom - width : r.left / zoom;
    left = Math.max(8, Math.min(left, vw - width - 8));
    pos = { top: up ? r.top / zoom - 6 : top, left, maxH: Math.min(420, up ? above : below), up };
    query = "";
    active = Math.max(0, items.findIndex((i) => i.value === value));
    open = true;
    await tick();
    if (searchable) searchEl?.focus();
    else pop?.focus();
    pop?.querySelector(".item.current")?.scrollIntoView({ block: "nearest" });
  }

  function close() {
    stopSample();
    open = false;
    button?.focus();
  }

  function choose(i: PickerItem) {
    if (i.disabled) return;
    onChange(i.value);
    close();
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      close();
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const d = e.key === "ArrowDown" ? 1 : -1;
      active = (active + d + shown.length) % Math.max(1, shown.length);
      pop?.querySelectorAll(".item")[active]?.scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (shown[active]) choose(shown[active]);
    }
  }

  function outside(e: PointerEvent) {
    if (!open) return;
    const t = e.target as Node;
    if (!pop?.contains(t) && !button.contains(t)) {
      stopSample();
      open = false;
    }
  }
</script>

<svelte:window onpointerdown={outside} onresize={() => (open = false)} />

<button
  bind:this={button}
  class="trigger {variant}"
  class:open
  aria-haspopup="listbox"
  aria-expanded={open}
  aria-label={label}
  onclick={toggle}
>
  {#if prefix}<span class="prefix">{prefix}</span>{/if}
  <span class="value">{selected?.label ?? placeholder}</span>
  <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5 5 6.5 8 3.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg>
</button>

{#if open}
  <div
    bind:this={pop}
    class="pop"
    class:up={pos.up}
    role="listbox"
    tabindex="-1"
    aria-label={label}
    style:top="{pos.top}px"
    style:left="{pos.left}px"
    style:width="{width}px"
    style:max-height="{pos.maxH}px"
    onkeydown={onKey}
  >
    {#if searchable}
      <label class="search">
        <Icon name="search" size={13} />
        <input bind:this={searchEl} bind:value={query} placeholder="Search…" aria-label="Search {label}" oninput={() => (active = 0)} />
      </label>
    {/if}
    <div class="list">
      {#each shown as item, i (item.value)}
        {#if item.group && item.group !== shown[i - 1]?.group}
          <div class="group">{item.group}</div>
        {/if}
        <button
          class="item"
          class:current={item.value === value}
          class:active={i === active}
          role="option"
          aria-selected={item.value === value}
          disabled={item.disabled}
          onpointerenter={() => (active = i)}
          onclick={() => choose(item)}
        >
          <span class="text">
            <span class="label">{item.label}</span>
            {#if item.sub}<span class="sub">{item.sub}</span>{/if}
          </span>
          {#if item.tags?.length}
            <span class="tags">{#each item.tags as t (t)}<span class="tag">{t}</span>{/each}</span>
          {/if}
          {#if item.preview}
            <span
              class="sample"
              class:on={sampling === item.value}
              role="button"
              tabindex="-1"
              title={sampling === item.value ? "Stop" : "Hear this voice"}
              aria-label="Preview {item.label}"
              onclick={(e) => playSample(e, item)}
              onkeydown={() => {}}
            >
              {#if sampling === item.value}
                <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect x="1.5" y="1.5" width="7" height="7" rx="1.2" fill="currentColor" /></svg>
              {:else}
                <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2.5 1.5v7l6-3.5z" fill="currentColor" /></svg>
              {/if}
            </span>
          {/if}
          {#if item.value === value}<span class="check"><Icon name="check" size={13} /></span>{/if}
        </button>
      {:else}
        <div class="none">No matches</div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
    max-width: 100%;
    height: 30px;
    padding: 0 10px;
    border-radius: 10px;
    color: var(--muted);
    font-size: 12.5px;
    outline: none;
    transition: background 0.12s, color 0.12s;
  }
  .trigger:hover,
  .trigger.open,
  .trigger:focus-visible {
    background: var(--raised);
    color: var(--text);
  }
  .trigger.field {
    height: 34px;
    width: 100%;
    justify-content: space-between;
    padding: 0 12px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    color: var(--text);
    font-size: 13px;
  }
  .trigger.field:hover,
  .trigger.field.open {
    border-color: var(--line-strong);
    background: var(--panel-2);
  }
  .prefix {
    color: var(--faint);
  }
  .value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .trigger svg {
    flex: none;
    opacity: 0.7;
  }

  .pop {
    position: fixed;
    z-index: 100;
    display: flex;
    flex-direction: column;
    padding: 6px;
    border-radius: 16px;
    background: #1b1b1e;
    border: 1px solid var(--line-strong);
    box-shadow: 0 18px 48px rgb(0 0 0 / 0.55);
    outline: none;
    animation: pop 0.12s ease-out;
  }
  .pop.up {
    transform: translateY(-100%);
    animation-name: pop-up;
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
  }
  @keyframes pop-up {
    from {
      opacity: 0;
      transform: translateY(calc(-100% + 4px));
    }
  }
  .search {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 2px 2px 6px;
    padding: 0 10px;
    height: 34px;
    border-radius: 10px;
    background: var(--panel);
    color: var(--faint);
  }
  .search input {
    flex: 1;
    border: 0;
    padding: 0;
    background: none;
    outline: none;
  }
  .list {
    overflow: auto;
    min-height: 0;
  }
  .group {
    padding: 8px 10px 4px;
    font-size: 11px;
    font-weight: 600;
    color: var(--faint);
  }
  .item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 10px;
    border-radius: 10px;
    text-align: left;
    outline: none;
  }
  .item.active {
    background: var(--raised);
  }
  .item:disabled {
    opacity: 0.4;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 1px;
  }
  .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sub {
    font-size: 11.5px;
    color: var(--faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tags {
    display: flex;
    gap: 4px;
    flex: none;
  }
  .tag {
    padding: 1px 6px;
    border-radius: 6px;
    background: var(--panel);
    color: var(--muted);
    font-size: 10.5px;
  }
  .sample {
    flex: none;
    display: grid;
    place-items: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--panel);
    color: var(--muted);
    cursor: pointer;
  }
  .sample:hover,
  .sample.on {
    background: var(--accent);
    color: var(--accent-ink);
  }
  .check {
    flex: none;
    color: var(--accent);
    display: grid;
  }
  .none {
    padding: 14px;
    color: var(--faint);
    text-align: center;
  }
</style>
