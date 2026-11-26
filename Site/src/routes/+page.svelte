<script lang="ts">
  import HeroScene from "#lib/HeroScene.svelte";
  import AppWindow from "#lib/AppWindow.svelte";
  import templates from "#lib/templates.json";
  import licenses from "#lib/licenses.json";
  import { STAGES, DETAILS, BUNDLED, BUILT_WITH, SERVICES, RESOURCES, FAQ, REPO, RELEASES, DOWNLOAD } from "#lib/content.ts";

  const gallery = templates.filter((t) => t.id !== "blank") as {
    id: string;
    title: string;
    description: string;
    category: string;
    duration: number | null;
    thumbnail: string | null;
    preview?: string | null;
    scenes: string[];
  }[];
  const totalComponents = licenses.groups.reduce((n, g) => n + g.items.length, 0);

  function play(e: PointerEvent | FocusEvent, on: boolean) {
    const v = (e.currentTarget as HTMLElement).querySelector("video");
    if (!v) return;
    if (on) v.play().catch(() => {});
    else {
      v.pause();
      v.currentTime = 0;
    }
  }

  const secs = (d: number | null) => (d ? `${Math.round(d)} s` : "");
</script>

<svelte:head>
  <title>ManimPro: make Manim videos on Windows</title>
  <meta
    name="description"
    content="A desktop studio for Manim. Write scenes or describe them to an AI assistant, preview them beside your code, and cut them into a video with narration, music and captions. Python, Manim, FFmpeg and LaTeX included."
  />
</svelte:head>

<a class="skip" href="#main">Skip to content</a>

<header class="nav">
  <a class="brand" href="/" aria-label="ManimPro home"><img src="/logo.svg" alt="" width="26" height="26" /> ManimPro</a>
  <nav aria-label="Sections">
    <a href="#features">Features</a>
    <a href="#templates">Templates</a>
    <a href="#built-with">Built with</a>
    <a href="#resources">Resources</a>
    <a href={REPO}>GitHub</a>
  </nav>
  <a class="button small" href={DOWNLOAD}>Download</a>
</header>

<main id="main">
  <!-- Hero: a scene drawing itself, the thing Manim exists to do -->
  <section class="hero">
    <div class="hero-copy">
      <h1>From equation<br />to animation.</h1>
      <p class="lede">
        ManimPro is a desktop studio for Manim, the animation engine behind 3Blue1Brown-style videos. Write scenes or describe
        them to an AI assistant, see them render beside your code, and cut them into a finished video with narration, music and
        captions.
      </p>
      <div class="ctas">
        <a class="button" href={DOWNLOAD}>
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M1 2.6 6.6 1.8v5.4H1zM7.3 1.7 15 .6v6.6H7.3zM1 7.9h5.6v5.4L1 12.5zm6.3 0H15v6.6l-7.7-1.1z" fill="currentColor" /></svg>
          Download for Windows
        </a>
        <a class="button ghost" href={REPO}>View the source</a>
      </div>
      <p class="fine">Free and open source. Windows 10 and 11. Python, Manim, FFmpeg and LaTeX are included.</p>
    </div>
    <div class="hero-scene">
      <HeroScene />
    </div>
  </section>

  <!-- The product -->
  <section class="product" aria-labelledby="product-title">
    <h2 id="product-title" class="sr-only">The ManimPro editor</h2>
    <AppWindow />
    <p class="caption">Code, preview and timeline in one window. The preview is a real render from the “Area under a curve” template.</p>
  </section>

  <!-- What's in the box, typeset -->
  <section class="equation" aria-label="What the installer includes">
    <p class="eq">
      <span>ManimPro</span> <span class="op">=</span> <span>Python</span> <span class="op">+</span> <span>Manim</span>
      <span class="op">+</span> <span>FFmpeg</span> <span class="op">+</span> <span>LaTeX</span>
    </p>
    <p class="eq-note">
      One installer, about 1 GB, no administrator rights. Nothing to set up on PATH, no virtual environments, no TeX
      distribution to hunt down. Install it and render your first scene.
    </p>
  </section>

  <!-- Every feature, in the order you use them -->
  <section id="features" class="stages" aria-labelledby="features-title">
    <div class="section-head">
      <h2 id="features-title">From idea to export</h2>
      <p>Everything ManimPro does, in the order you'll use it.</p>
    </div>
    {#each STAGES as stage (stage.name)}
      <article class="stage">
        <div class="stage-name">
          <h3>{stage.name}</h3>
          <p>{stage.lead}</p>
        </div>
        <dl>
          {#each stage.features as f (f.title)}
            <div class="feature">
              <dt>{f.title}</dt>
              <dd>{f.body}</dd>
            </div>
          {/each}
        </dl>
      </article>
    {/each}
    <article class="stage">
      <div class="stage-name">
        <h3>And the rest</h3>
        <p>The small things that make it pleasant to spend an afternoon in.</p>
      </div>
      <ul class="details">
        {#each DETAILS as d (d)}<li>{d}</li>{/each}
      </ul>
    </article>
  </section>

  <!-- Templates -->
  <section id="templates" class="templates" aria-labelledby="templates-title">
    <div class="section-head">
      <h2 id="templates-title">Start from a finished video</h2>
      <p>{gallery.length} templates, each a complete video in several scenes. Open one, play it, and change anything.</p>
    </div>
    <ul class="grid">
      {#each gallery as t (t.id)}
        <li>
          <div
            class="tile"
            role="group"
            aria-label={t.title}
            onpointerenter={(e) => play(e, true)}
            onpointerleave={(e) => play(e, false)}
          >
            <div class="frame">
              {#if t.thumbnail}<img src={t.thumbnail} alt="" loading="lazy" />{/if}
              {#if t.preview}<video src={t.preview} muted loop playsinline preload="none" aria-hidden="true"></video>{/if}
              {#if t.duration}<span class="len">{secs(t.duration)}</span>{/if}
            </div>
            <h3>{t.title}</h3>
            <p>{t.description}</p>
          </div>
        </li>
      {/each}
    </ul>
  </section>

  <!-- Dependencies -->
  <section id="built-with" class="deps" aria-labelledby="deps-title">
    <div class="section-head">
      <h2 id="deps-title">Built on open source</h2>
      <p>
        ManimPro stands on a lot of good software. These are the main pieces; the
        <a href={`${REPO}/blob/main/THIRD-PARTY-NOTICES.md`}>full list of {totalComponents} components</a> and their licences is in the
        source code and in the app under Settings, About.
      </p>
    </div>
    <div class="dep-cols">
      {#each [{ title: "Inside the installer", items: BUNDLED }, { title: "The app is made with", items: BUILT_WITH }, { title: "Services you can connect", items: SERVICES }] as col (col.title)}
        <div class="dep-col">
          <h3>{col.title}</h3>
          <ul>
            {#each col.items as d (d.name)}
              <li>
                <a href={d.url}>{d.name}</a>
                <span class="role">{d.role}</span>
                <span class="lic">{d.license}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/each}
    </div>
  </section>

  <!-- Resources -->
  <section id="resources" class="resources" aria-labelledby="resources-title">
    <div class="section-head">
      <h2 id="resources-title">Learn more</h2>
      <p>Where to learn Manim, find ideas, and follow ManimPro.</p>
    </div>
    <div class="res-cols">
      {#each RESOURCES as g (g.group)}
        <div>
          <h3>{g.group}</h3>
          <ul>
            {#each g.links as l (l.url)}
              <li><a href={l.url}><span class="res-label">{l.label}</span><span class="res-note">{l.note}</span></a></li>
            {/each}
          </ul>
        </div>
      {/each}
    </div>
  </section>

  <!-- FAQ -->
  <section class="faq" aria-labelledby="faq-title">
    <div class="section-head">
      <h2 id="faq-title">Questions</h2>
    </div>
    <div class="qs">
      {#each FAQ as item (item.q)}
        <details>
          <summary>{item.q}</summary>
          <p>{item.a}</p>
        </details>
      {/each}
    </div>
  </section>

  <!-- Download -->
  <section class="final" aria-labelledby="final-title">
    <h2 id="final-title">Make something that moves.</h2>
    <div class="ctas">
      <a class="button" href={DOWNLOAD}>Download for Windows</a>
      <a class="button ghost" href={RELEASES}>All releases</a>
    </div>
    <p class="fine">Windows 10 or 11, 64-bit. About 1 GB of disk space. The installer fetches Microsoft WebView2 if your PC doesn't have it.</p>
  </section>
</main>

<footer>
  <div class="foot-brand"><img src="/logo.svg" alt="" width="22" height="22" /> ManimPro</div>
  <p>
    Built on <a href="https://www.manim.community/">Manim Community Edition</a>, created by Grant Sanderson and maintained by the
    Manim Community. ManimPro is independent and not affiliated with 3Blue1Brown or the Manim Community.
  </p>
  <nav aria-label="Footer">
    <a href={REPO}>Source code</a>
    <a href={RELEASES}>Releases</a>
    <a href={`${REPO}/issues`}>Issues</a>
    <a href={`${REPO}/blob/main/THIRD-PARTY-NOTICES.md`}>Licences</a>
  </nav>
</footer>

<style>
  /* ---- layout scale ---- */
  .nav,
  main > section,
  footer {
    width: min(1200px, 100% - 48px);
    margin-inline: auto;
  }
  main > section {
    padding-block: 120px 0;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .skip {
    position: absolute;
    left: 16px;
    top: -60px;
    padding: 8px 14px;
    background: var(--white);
    color: var(--black);
    border-radius: 8px;
    z-index: 10;
  }
  .skip:focus {
    top: 12px;
  }

  /* ---- type ---- */
  h1,
  h2,
  h3 {
    font-family: var(--tex);
    font-weight: 400;
    margin: 0;
    letter-spacing: -0.005em;
  }
  h1 {
    font-size: clamp(50px, 5.6vw, 84px);
    line-height: 1;
  }
  h2 {
    font-size: clamp(36px, 4.6vw, 56px);
    line-height: 1.05;
  }
  h3 {
    font-size: 26px;
    line-height: 1.2;
  }
  p {
    margin: 0;
  }
  .section-head {
    display: grid;
    gap: 14px;
    max-width: 62ch;
    margin-bottom: 56px;
  }
  .section-head p {
    color: var(--ink-2);
  }
  .section-head a {
    color: var(--white);
    text-underline-offset: 3px;
  }

  /* ---- buttons ---- */
  .button {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    height: 48px;
    padding: 0 22px;
    border-radius: 999px;
    background: var(--white);
    color: var(--black);
    border: 1px solid var(--white);
    font-weight: 600;
    font-size: 15px;
    text-decoration: none;
    transition: background 0.15s, color 0.15s;
  }
  .button:hover {
    background: #d9d9d9;
  }
  .button.ghost {
    background: transparent;
    color: var(--white);
    border-color: #3a3a3a;
  }
  .button.ghost:hover {
    border-color: var(--white);
    background: transparent;
  }
  .button.small {
    height: 38px;
    padding: 0 16px;
    font-size: 14px;
  }

  /* ---- nav ---- */
  .nav {
    display: flex;
    align-items: center;
    gap: 28px;
    height: 76px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-weight: 600;
    text-decoration: none;
    margin-right: auto;
  }
  .brand img {
    border-radius: 7px;
    border: 1px solid #2a2a2a;
  }
  nav {
    display: flex;
    gap: 26px;
  }
  .nav nav a {
    color: var(--ink-2);
    text-decoration: none;
    font-size: 15px;
  }
  .nav nav a:hover {
    color: var(--white);
  }

  /* ---- hero ---- */
  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: center;
    gap: 48px;
    min-height: min(760px, calc(100vh - 76px));
  }
  main > section.hero {
    padding-block: 40px 40px;
  }
  .hero-copy {
    display: grid;
    gap: 28px;
  }
  .lede {
    max-width: 52ch;
    color: var(--ink-2);
    font-size: 18px;
  }
  .ctas {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .fine {
    color: var(--ink-3);
    font-size: 14px;
  }

  /* ---- product ---- */
  main > section.product {
    padding-top: 40px;
  }
  .caption {
    margin-top: 16px;
    color: var(--ink-3);
    font-size: 14px;
  }

  /* ---- equation ---- */
  .eq {
    font-family: var(--tex);
    font-size: clamp(30px, 5vw, 68px);
    line-height: 1.15;
    display: flex;
    flex-wrap: wrap;
    gap: 0 0.32em;
  }
  .eq .op {
    color: var(--ink-3);
  }
  .eq-note {
    margin-top: 24px;
    max-width: 60ch;
    color: var(--ink-2);
  }

  /* ---- stages ---- */
  .stage {
    display: grid;
    grid-template-columns: minmax(0, 4fr) minmax(0, 8fr);
    gap: 48px;
    padding: 48px 0;
    border-top: 1px solid var(--line);
  }
  .stage-name {
    position: sticky;
    top: 24px;
    align-self: start;
    display: grid;
    gap: 12px;
  }
  .stage-name h3 {
    font-size: clamp(34px, 3.6vw, 48px);
  }
  .stage-name p {
    color: var(--ink-2);
    max-width: 34ch;
  }
  dl {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 36px 40px;
  }
  .feature dt {
    font-family: var(--tex);
    font-size: 22px;
    line-height: 1.25;
    margin-bottom: 8px;
  }
  .feature dd {
    margin: 0;
    color: var(--ink-2);
    font-size: 15.5px;
  }
  .details {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 40px;
  }
  .details li {
    padding: 12px 0;
    border-bottom: 1px solid var(--line);
    color: var(--ink-2);
    font-size: 15.5px;
  }

  /* ---- templates ---- */
  .grid {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 40px 24px;
  }
  .tile {
    display: grid;
    gap: 10px;
  }
  .frame {
    position: relative;
    aspect-ratio: 16 / 9;
    border-radius: 10px;
    overflow: hidden;
    background: #0a0a0a;
    border: 1px solid var(--line);
  }
  .frame img,
  .frame video {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: grayscale(1);
  }
  .frame video {
    opacity: 0;
    transition: opacity 0.25s;
  }
  .tile:hover video {
    opacity: 1;
  }
  .len {
    position: absolute;
    right: 8px;
    bottom: 8px;
    padding: 1px 7px;
    border-radius: 6px;
    background: rgb(0 0 0 / 0.75);
    font-size: 12px;
    color: var(--ink-2);
    font-variant-numeric: tabular-nums;
  }
  .tile h3 {
    font-size: 21px;
  }
  .tile p {
    color: var(--ink-3);
    font-size: 14.5px;
    line-height: 1.5;
  }

  /* ---- dependencies ---- */
  .dep-cols {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 40px;
  }
  .dep-col h3,
  .res-cols h3 {
    font-size: 24px;
    margin-bottom: 16px;
  }
  .dep-col ul,
  .res-cols ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .dep-col li {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 2px 12px;
    padding: 14px 0;
    border-top: 1px solid var(--line);
  }
  .dep-col li a {
    text-decoration: none;
    font-weight: 500;
  }
  .dep-col li a:hover {
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .role {
    grid-column: 1;
    color: var(--ink-3);
    font-size: 14px;
  }
  .lic {
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: center;
    color: var(--ink-3);
    font-size: 13px;
    text-align: right;
    max-width: 13ch;
  }

  /* ---- resources ---- */
  .res-cols {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 40px;
  }
  .res-cols a {
    display: grid;
    gap: 2px;
    padding: 14px 0;
    border-top: 1px solid var(--line);
    text-decoration: none;
  }
  .res-label {
    font-weight: 500;
  }
  .res-note {
    color: var(--ink-3);
    font-size: 14px;
  }
  .res-cols a:hover .res-label {
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  /* ---- faq ---- */
  .qs {
    max-width: 820px;
  }
  details {
    border-top: 1px solid var(--line);
  }
  details:last-child {
    border-bottom: 1px solid var(--line);
  }
  summary {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    padding: 20px 0;
    cursor: pointer;
    font-family: var(--tex);
    font-size: 22px;
    list-style: none;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  summary::after {
    content: "+";
    color: var(--ink-3);
    font-family: var(--sans);
    transition: transform 0.2s;
  }
  details[open] summary::after {
    transform: rotate(45deg);
  }
  details p {
    padding: 0 0 22px;
    color: var(--ink-2);
    max-width: 64ch;
  }

  /* ---- final ---- */
  main > section.final {
    padding-block: 160px 120px;
    display: grid;
    justify-items: start;
    gap: 28px;
  }
  .final h2 {
    font-size: clamp(44px, 6.6vw, 92px);
  }

  /* ---- footer ---- */
  footer {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: start;
    gap: 32px;
    padding: 40px 0 56px;
    border-top: 1px solid var(--line);
    color: var(--ink-3);
    font-size: 14px;
  }
  .foot-brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: var(--white);
    font-weight: 600;
  }
  .foot-brand img {
    border-radius: 6px;
    border: 1px solid #2a2a2a;
  }
  footer p {
    max-width: 64ch;
  }
  footer nav {
    display: flex;
    gap: 20px;
  }
  footer a {
    color: var(--ink-2);
  }
  footer a:hover {
    color: var(--white);
  }

  /* ---- small screens ---- */
  @media (max-width: 960px) {
    .hero {
      grid-template-columns: 1fr;
      min-height: 0;
    }
    .stage {
      grid-template-columns: 1fr;
      gap: 28px;
    }
    .stage-name {
      position: static;
    }
    .dep-cols,
    .res-cols {
      grid-template-columns: 1fr;
    }
    footer {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 720px) {
    .nav nav {
      display: none;
    }
    main > section {
      padding-top: 88px;
    }
    dl,
    .details {
      grid-template-columns: 1fr;
    }
  }
</style>
