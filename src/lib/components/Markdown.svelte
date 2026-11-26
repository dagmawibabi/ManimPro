<script lang="ts">
  import "katex/dist/katex.min.css";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import { renderMarkdown } from "#lib/markdown.ts";

  let { text }: { text: string } = $props();
  const html = $derived(renderMarkdown(text));

  // Links open in the user's browser, never inside the app window.
  function onClick(e: MouseEvent) {
    const a = (e.target as HTMLElement).closest("a");
    if (!a) return;
    e.preventDefault();
    const href = a.getAttribute("href") ?? "";
    if (/^https?:\/\//i.test(href)) openUrl(href);
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="md" onclick={onClick}>{@html html}</div>

<style>
  .md {
    line-height: 1.6;
    word-break: break-word;
  }
  .md :global(p) {
    margin: 0 0 0.7em;
  }
  .md :global(p:last-child),
  .md :global(ul:last-child),
  .md :global(ol:last-child) {
    margin-bottom: 0;
  }
  .md :global(h1),
  .md :global(h2),
  .md :global(h3),
  .md :global(h4) {
    margin: 1em 0 0.45em;
    font-family: var(--font-display);
    font-weight: 600;
    line-height: 1.3;
  }
  .md :global(h1) {
    font-size: 1.35em;
  }
  .md :global(h2) {
    font-size: 1.2em;
  }
  .md :global(h3),
  .md :global(h4) {
    font-size: 1.05em;
  }
  .md :global(:first-child) {
    margin-top: 0;
  }
  .md :global(ul),
  .md :global(ol) {
    margin: 0 0 0.7em;
    padding-left: 1.4em;
  }
  .md :global(li) {
    margin: 0.2em 0;
  }
  .md :global(li::marker) {
    color: var(--faint);
  }
  .md :global(strong) {
    font-weight: 600;
    color: var(--text);
  }
  .md :global(a) {
    color: var(--accent);
    text-decoration: none;
  }
  .md :global(a:hover) {
    text-decoration: underline;
  }
  .md :global(code) {
    font-family: var(--mono);
    font-size: 0.88em;
    padding: 1px 6px;
    border-radius: 6px;
    background: var(--bg);
    border: 1px solid var(--line);
  }
  .md :global(pre) {
    margin: 0 0 0.8em;
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--bg);
    border: 1px solid var(--line);
    overflow: auto;
  }
  .md :global(pre code) {
    padding: 0;
    border: 0;
    background: none;
    font-size: 12px;
    line-height: 1.55;
  }
  .md :global(blockquote) {
    margin: 0 0 0.7em;
    padding: 2px 12px;
    border-left: 3px solid var(--line-strong);
    color: var(--muted);
  }
  .md :global(table) {
    border-collapse: collapse;
    margin: 0 0 0.8em;
    font-size: 0.95em;
  }
  .md :global(th),
  .md :global(td) {
    padding: 6px 10px;
    border: 1px solid var(--line);
    text-align: left;
  }
  .md :global(th) {
    background: var(--panel-2);
    font-weight: 600;
  }
  .md :global(hr) {
    border: 0;
    border-top: 1px solid var(--line);
    margin: 1em 0;
  }
  .md :global(.katex-display) {
    margin: 0.6em 0 0.9em;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .md :global(.katex) {
    font-size: 1.08em;
  }
</style>
