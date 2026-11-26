/** Assistant replies: Markdown with LaTeX math, sanitized before it reaches the DOM. */
import { Marked } from "marked";
import katex from "katex";
import DOMPurify from "dompurify";

const marked = new Marked({ gfm: true, breaks: true });

function math(tex: string, display: boolean): string {
  try {
    return katex.renderToString(tex, { displayMode: display, throwOnError: false, output: "html", strict: "ignore" });
  } catch {
    return `<code>${escapeHtml(tex)}</code>`;
  }
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
}

/**
 * Math is cut out before Markdown runs (so `_` and `*` inside formulas survive),
 * replaced with placeholders, then rendered with KaTeX and put back.
 * Code spans and fences are protected first so `$` in code stays literal.
 */
export function renderMarkdown(src: string): string {
  const stash: string[] = [];
  const keep = (html: string) => `${stash.push(html) - 1}`;

  let text = src
    // fenced and inline code: leave untouched
    .replace(/```[\s\S]*?(```|$)|`[^`\n]*`/g, (m) => keep(m))
    // display math
    .replace(/\$\$([\s\S]+?)\$\$/g, (_, t) => keep(math(t.trim(), true)))
    .replace(/\\\[([\s\S]+?)\\\]/g, (_, t) => keep(math(t.trim(), true)))
    // inline math (avoid prices like "$4 / $20")
    .replace(/\\\(([\s\S]+?)\\\)/g, (_, t) => keep(math(t.trim(), false)))
    .replace(/(^|[^\\$\w])\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/g, (_, pre, t) => pre + keep(math(t, false)));

  // Code was stashed only to shield it from math; give it back to Markdown as-is.
  text = text.replace(/(\d+)/g, (m, i) => (stash[+i].startsWith("`") ? stash[+i] : m));
  let html = marked.parse(text, { async: false }) as string;
  html = html.replace(/(\d+)/g, (_, i) => stash[+i]);

  return DOMPurify.sanitize(html, {
    ADD_ATTR: ["target", "aria-hidden"],
    FORBID_TAGS: ["style", "form", "input", "button", "iframe"],
  });
}
