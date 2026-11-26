<script lang="ts">
  import "katex/dist/katex.min.css";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import { renderMarkdown } from "#lib/markdown.ts";

  let { text }: { text: string } = $props();
  const html = $derived(renderMarkdown(text));
  let root: HTMLDivElement;

  // Each code block gets its language and a Copy button (added after sanitizing, so they stay ours).
  $effect(() => {
    html;
    if (!root) return;
    for (const pre of root.querySelectorAll<HTMLPreElement>("pre")) {
      if (pre.parentElement?.classList.contains("code-block")) continue;
      const wrap = document.createElement("div");
      wrap.className = "code-block";
      const bar = document.createElement("div");
      bar.className = "code-bar";
      const label = document.createElement("span");
      label.textContent = pre.dataset.lang || "code";
      const copy = document.createElement("button");
      copy.type = "button";
      copy.textContent = "Copy";
      copy.onclick = async () => {
        await navigator.clipboard.writeText(pre.querySelector("code")?.textContent ?? "");
        copy.textContent = "Copied";
        setTimeout(() => (copy.textContent = "Copy"), 1400);
      };
      bar.append(label, copy);
      pre.replaceWith(wrap);
      wrap.append(bar, pre);
    }
  });

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
<div class="md" bind:this={root} onclick={onClick}>{@html html}</div>

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
  .md :global(.code-block) {
    margin: 0 0 0.8em;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--bg);
    overflow: hidden;
  }
  .md :global(.code-block pre) {
    margin: 0;
    border: 0;
    border-radius: 0;
  }
  .md :global(.code-bar) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 8px 5px 14px;
    border-bottom: 1px solid var(--line);
    font-size: 11px;
    color: var(--faint);
  }
  .md :global(.code-bar button) {
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    color: var(--muted);
  }
  .md :global(.code-bar button:hover) {
    background: var(--raised);
    color: var(--text);
  }
  /* Highlighting, matched to the code editor's colors. */
  .md :global(.hljs-comment),
  .md :global(.hljs-quote) {
    color: #5f636d;
    font-style: italic;
  }
  .md :global(.hljs-keyword),
  .md :global(.hljs-built_in),
  .md :global(.hljs-literal),
  .md :global(.hljs-meta .hljs-keyword) {
    color: #c792ea;
  }
  .md :global(.hljs-string),
  .md :global(.hljs-regexp),
  .md :global(.hljs-addition) {
    color: #a5d6a7;
  }
  .md :global(.hljs-number),
  .md :global(.hljs-symbol) {
    color: #f8c37a;
  }
  .md :global(.hljs-title),
  .md :global(.hljs-title.class_),
  .md :global(.hljs-type),
  .md :global(.hljs-section) {
    color: var(--accent);
  }
  .md :global(.hljs-title.function_),
  .md :global(.hljs-attr),
  .md :global(.hljs-attribute),
  .md :global(.hljs-property) {
    color: #82aaff;
  }
  .md :global(.hljs-params),
  .md :global(.hljs-variable) {
    color: #e6e6e6;
  }
  .md :global(.hljs-meta),
  .md :global(.hljs-tag),
  .md :global(.hljs-name),
  .md :global(.hljs-selector-tag) {
    color: #89ddff;
  }
  .md :global(.hljs-deletion) {
    color: #f3a39b;
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
