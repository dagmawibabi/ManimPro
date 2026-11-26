/** Assistant replies: Markdown with LaTeX math, sanitized before it reaches the DOM. */
import { Marked } from "marked";
import katex from "katex";
import DOMPurify from "dompurify";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import json from "highlight.js/lib/languages/json";
import bash from "highlight.js/lib/languages/bash";
import powershell from "highlight.js/lib/languages/powershell";
import yaml from "highlight.js/lib/languages/yaml";
import xml from "highlight.js/lib/languages/xml";
import css from "highlight.js/lib/languages/css";
import latex from "highlight.js/lib/languages/latex";
import ini from "highlight.js/lib/languages/ini";
import plaintext from "highlight.js/lib/languages/plaintext";

for (const [name, lang] of Object.entries({ python, javascript, typescript, json, bash, powershell, yaml, xml, css, latex, ini, plaintext })) {
  hljs.registerLanguage(name, lang);
}
hljs.registerAliases(["py", "python3"], { languageName: "python" });
hljs.registerAliases(["js"], { languageName: "javascript" });
hljs.registerAliases(["ts"], { languageName: "typescript" });
hljs.registerAliases(["sh", "shell", "console"], { languageName: "bash" });
hljs.registerAliases(["ps", "ps1", "pwsh"], { languageName: "powershell" });
hljs.registerAliases(["yml"], { languageName: "yaml" });
hljs.registerAliases(["html", "svg"], { languageName: "xml" });
hljs.registerAliases(["tex"], { languageName: "latex" });
hljs.registerAliases(["toml", "cfg"], { languageName: "ini" });
hljs.registerAliases(["text", "txt"], { languageName: "plaintext" });

/** Highlights a code block; unlabelled blocks are guessed among the languages above (Manim code is Python). */
function highlight(code: string, lang?: string): { html: string; lang: string } {
  const want = (lang ?? "").trim().split(/\s+/)[0].toLowerCase();
  if (want && hljs.getLanguage(want)) {
    const r = hljs.highlight(code, { language: want, ignoreIllegals: true });
    return { html: r.value, lang: hljs.getLanguage(want)?.name ?? want };
  }
  const r = hljs.highlightAuto(code, ["python", "bash", "json", "latex", "powershell", "yaml"]);
  return { html: r.value, lang: r.language ? (hljs.getLanguage(r.language)?.name ?? r.language) : "" };
}

const marked = new Marked({
  gfm: true,
  breaks: true,
  renderer: {
    code({ text, lang }) {
      const { html, lang: name } = highlight(text, lang);
      return `<pre data-lang="${escapeHtml(name)}"><code class="hljs">${html}</code></pre>\n`;
    },
  },
});

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
    ADD_ATTR: ["target", "aria-hidden", "data-lang"],
    FORBID_TAGS: ["style", "form", "input", "button", "iframe"],
  });
}
