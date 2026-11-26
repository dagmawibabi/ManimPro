# ManimPro website

The landing page for ManimPro, built with SvelteKit and prerendered to static HTML.

```
pnpm install
pnpm dev        # http://localhost:5180
pnpm build      # static site in build/
```

Deploy `build/` to any static host (GitHub Pages, Netlify, Vercel, Cloudflare Pages).

- Copy lives in `src/lib/content.ts` (features, dependencies, resources, FAQ, links).
- `src/lib/templates.json` and `src/lib/licenses.json` are copies from the app; refresh them after
  running `scripts/build-templates.py` or `scripts/build-licenses.py` there.
- Template previews in `static/templates` come from the app's `static/templates`.
- Headlines use KaTeX's Computer Modern fonts (`static/fonts`, MIT/OFL); body text uses Geist.
