/** What ManimPro can do with a project file, by extension. */

const TEXT: Record<string, string> = {
  py: "python",
  json: "json",
  csv: "plaintext",
  tsv: "plaintext",
  txt: "plaintext",
  md: "markdown",
  yaml: "yaml",
  yml: "yaml",
  toml: "ini",
  ini: "ini",
  cfg: "ini",
  xml: "xml",
  svg: "xml",
  tex: "latex",
  html: "html",
  css: "css",
  js: "javascript",
  ts: "typescript",
  srt: "plaintext",
};
const IMAGE = new Set(["png", "jpg", "jpeg", "gif", "webp", "bmp"]);

export const extOf = (path: string) => (path.match(/\.([^.\\/]+)$/)?.[1] ?? "").toLowerCase();
export const isText = (path: string) => extOf(path) in TEXT;
export const isImage = (path: string) => IMAGE.has(extOf(path));
export const languageOf = (path: string | null) => (path ? (TEXT[extOf(path)] ?? "plaintext") : "python");

/** Icon name for a file in the tree. */
export function iconOf(path: string): string {
  const e = extOf(path);
  if (IMAGE.has(e) || e === "svg") return "image";
  if (["mp3", "wav", "m4a", "ogg", "flac", "aac", "opus"].includes(e)) return "music";
  if (["mp4", "mov", "webm", "mkv"].includes(e)) return "film";
  if (["csv", "tsv", "json", "yaml", "yml", "toml", "xml"].includes(e)) return "grid";
  return "file";
}
