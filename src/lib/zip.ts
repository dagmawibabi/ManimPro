/** Project .zip export and import, used by the home page, the project switcher and agents. */
import { open, save } from "@tauri-apps/plugin-dialog";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { api } from "./api";

const nameOf = (dir: string) => dir.split(/[\\/]/).pop() || "project";

/** Asks where to save, writes the .zip and shows it in its folder. Returns the path, or null if cancelled. */
export async function exportZip(dir: string, includeRenders = false) {
  const dest = await save({
    title: "Export project as .zip",
    defaultPath: `${nameOf(dir)}.zip`,
    filters: [{ name: "Zip archive", extensions: ["zip"] }],
  });
  if (!dest) return null;
  const path = dest.toLowerCase().endsWith(".zip") ? dest : `${dest}.zip`;
  const info = await api.exportProjectZip(dir, path, includeRenders);
  revealItemInDir(info.path);
  return info;
}

/** Asks for a project .zip and unpacks it into the projects folder. Returns the new folder, or null. */
export async function importZip() {
  const picked = await open({ title: "Open a project .zip", filters: [{ name: "Zip archive", extensions: ["zip"] }] });
  if (typeof picked !== "string") return null;
  return api.importProjectZip(picked);
}
