/** Model choices per assistant, described with data from models.dev. */
import { api, type Catalog, type CatalogModel, type Provider } from "./api";
import type { PickerItem } from "./components/Picker.svelte";

function tokens(n?: number) {
  if (!n) return "";
  if (n >= 1_000_000) return `${+(n / 1_000_000).toFixed(1)}M`;
  return `${Math.round(n / 1000)}K`;
}

function price(m: CatalogModel) {
  if (m.input_cost === undefined || m.output_cost === undefined) return "";
  if (m.input_cost === 0 && m.output_cost === 0) return "free";
  const f = (x: number) => `$${x < 1 ? x.toFixed(2).replace(/0$/, "") : +x.toFixed(2)}`;
  return `${f(m.input_cost)} / ${f(m.output_cost)} per M tokens`;
}

export function describe(m: CatalogModel | undefined): { sub: string; tags: string[] } {
  if (!m) return { sub: "", tags: [] };
  const parts = [m.context ? `${tokens(m.context)} context` : "", price(m)].filter(Boolean);
  const tags: string[] = [];
  if (m.reasoning) tags.push("reasoning");
  if (m.attachment) tags.push("vision");
  if (m.input_cost === 0 && m.output_cost === 0) tags.push("free");
  return { sub: parts.join(" · "), tags };
}

const byNewest = (a: [string, CatalogModel], b: [string, CatalogModel]) =>
  (b[1].release_date ?? "").localeCompare(a[1].release_date ?? "");

class Models {
  catalog = $state<Catalog | null>(null);
  loading = $state(false);
  error = $state<string | null>(null);

  async load(refresh = false) {
    if ((this.catalog && !refresh) || this.loading) return;
    this.loading = true;
    try {
      this.catalog = await api.modelsCatalog(refresh);
      this.error = null;
    } catch (e) {
      this.error = String(e);
    } finally {
      this.loading = false;
    }
  }

  lookup(provider: string, model: string): CatalogModel | undefined {
    return this.catalog?.[provider]?.models?.[model];
  }

  /** Newest Anthropic model of a family (for Claude Code's opus/sonnet/haiku aliases). */
  newestOf(family: string): CatalogModel | undefined {
    const ms = Object.entries(this.catalog?.anthropic?.models ?? {}).filter(([, m]) => m.family === family);
    return ms.sort(byNewest)[0]?.[1];
  }

  /** Picker rows for a provider. `cli` is the list a CLI reported itself (OpenCode). */
  items(provider: Provider, cli: string[] = []): PickerItem[] {
    const def: PickerItem = { value: "", label: "Default model", sub: "Let the assistant choose" };
    switch (provider) {
      case "claude":
        return [
          { ...def, sub: "Claude Code's default for your plan" },
          ...(["opus", "sonnet", "haiku"] as const).map((alias) => {
            const m = this.newestOf(`claude-${alias}`);
            const d = describe(m);
            return {
              value: alias,
              label: m?.name ?? alias[0].toUpperCase() + alias.slice(1),
              sub: d.sub || `Latest ${alias}`,
              tags: d.tags,
            };
          }),
        ];
      case "codex": {
        const ms = Object.entries(this.catalog?.openai?.models ?? {})
          .filter(([, m]) => m.tool_call && m.reasoning)
          .sort(byNewest)
          .slice(0, 14);
        return [
          { ...def, sub: "Codex's default for your ChatGPT plan" },
          ...ms.map(([id, m]) => ({ value: id, label: m.name ?? id, ...describe(m) })),
        ];
      }
      case "opencode":
        return [
          def,
          ...cli.map((full) => {
            const [prov, ...rest] = full.split("/");
            const m = this.lookup(prov, rest.join("/"));
            return { value: full, label: m?.name ?? full, group: this.catalog?.[prov]?.name ?? prov, ...describe(m) };
          }),
        ];
      case "openrouter":
      case "vercel": {
        const ms = Object.entries(this.catalog?.[provider]?.models ?? {})
          .filter(([, m]) => m.tool_call)
          .sort(byNewest);
        return ms.map(([id, m]) => ({ value: `${provider}/${id}`, label: m.name ?? id, ...describe(m) }));
      }
    }
  }
}

export const models = new Models();
