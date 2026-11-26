<script lang="ts">
  import { settings } from "#lib/settings.svelte.ts";

  /** Plays `src` over its parent (a card thumbnail) after the pointer rests on the card. */
  let { src, delay = 650 }: { src: string | null | undefined; delay?: number } = $props();

  let anchor: HTMLSpanElement;
  let active = $state(false);
  let ready = $state(false);

  $effect(() => {
    // Listen on the whole card (the thumbnail's parent button), not just the image.
    const card = anchor?.parentElement?.closest("button") ?? anchor?.parentElement;
    if (!card || !src) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const enter = () => {
      if (!settings.value.hoverPreviews) return;
      timer = setTimeout(() => (active = true), delay);
    };
    const leave = () => {
      clearTimeout(timer);
      active = false;
      ready = false;
    };
    card.addEventListener("pointerenter", enter);
    card.addEventListener("pointerleave", leave);
    return () => {
      clearTimeout(timer);
      card.removeEventListener("pointerenter", enter);
      card.removeEventListener("pointerleave", leave);
    };
  });
</script>

<span bind:this={anchor} class="anchor" aria-hidden="true"></span>
{#if active && src}
  <video class:ready {src} autoplay muted loop playsinline preload="auto" oncanplay={() => (ready = true)}></video>
{/if}

<style>
  .anchor {
    display: none;
  }
  video {
    position: absolute;
    inset: 0;
    z-index: 1;
    width: 100%;
    height: 100%;
    object-fit: contain;
    background: #000;
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
  }
  video.ready {
    opacity: 1;
  }
</style>
