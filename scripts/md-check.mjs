// Quick check of the chat Markdown + math pipeline (mirrors src/lib/markdown.ts without DOMPurify).
// Run: node scripts/md-check.mjs
import { Marked } from "marked";
import katex from "katex";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../src/lib/markdown.ts", import.meta.url), "utf8");
const body = source.slice(source.indexOf("const stash"), source.indexOf("return DOMPurify"));
const marked = new Marked({ gfm: true, breaks: true });
const math = (tex, display) => katex.renderToString(tex, { displayMode: display, throwOnError: false, output: "html" });
const render = new Function("src", "marked", "math", body.replace(/ as string/g, "").replace(": string[]", "").replace("(html: string)", "(html)") + "; return html;");

const sample = [
  "**Pointers:** blue **L** and `mid = (0 + 14) // 2`; it costs $4 / $20 per M tokens.",
  "",
  "Inline $e^{i\\pi} + 1 = 0$ and display:",
  "",
  "$$\\int_0^1 x^2\\,dx = \\tfrac{1}{3}$$",
  "",
  "- item with $a_1 * b_2$ and \\(x_n\\)",
].join("\n");
const html = render(sample, marked, math);
const count = (re) => (html.match(re) || []).length;
console.log({
  katex: count(/class="katex"/g),
  display: count(/katex-display/g),
  pricesKept: html.includes("$4 / $20"),
  codeKept: html.includes("<code>mid = (0 + 14) // 2</code>"),
  bold: html.includes("<strong>Pointers:</strong>"),
  list: html.includes("<li>"),
  leftovers: count(//g),
});
