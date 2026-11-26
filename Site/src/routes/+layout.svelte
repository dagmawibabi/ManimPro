<script lang="ts">
  import "@fontsource-variable/geist";
  let { children } = $props();
</script>

<svelte:head>
  <link rel="preload" href="/fonts/KaTeX_Main-Regular.woff2" as="font" type="font/woff2" crossorigin="anonymous" />
</svelte:head>

{@render children()}

<style>
  @font-face {
    font-family: "KaTeX_Main";
    src: url("/fonts/KaTeX_Main-Regular.woff2") format("woff2");
    font-weight: 400;
    font-style: normal;
    font-display: swap;
  }
  @font-face {
    font-family: "KaTeX_Main";
    src: url("/fonts/KaTeX_Main-Italic.woff2") format("woff2");
    font-weight: 400;
    font-style: italic;
    font-display: swap;
  }
  @font-face {
    font-family: "KaTeX_Main";
    src: url("/fonts/KaTeX_Main-Bold.woff2") format("woff2");
    font-weight: 700;
    font-style: normal;
    font-display: swap;
  }
  @font-face {
    font-family: "KaTeX_Math";
    src: url("/fonts/KaTeX_Math-Italic.woff2") format("woff2");
    font-weight: 400;
    font-style: italic;
    font-display: swap;
  }

  :global(:root) {
    --black: #000000;
    --white: #ffffff;
    --ink-2: #b4b4b4; /* secondary text */
    --ink-3: #7a7a7a; /* quiet text */
    --line: #232323;
    --raise: #0e0e0e;
    --tex: "KaTeX_Main", "Latin Modern Roman", "Times New Roman", serif;
    --sans: "Geist Variable", system-ui, sans-serif;
    color-scheme: dark;
  }
  :global(*),
  :global(*::before),
  :global(*::after) {
    box-sizing: border-box;
  }
  :global(html) {
    background: var(--black);
    scroll-behavior: smooth;
    -webkit-text-size-adjust: 100%;
  }
  @media (prefers-reduced-motion: reduce) {
    :global(html) {
      scroll-behavior: auto;
    }
  }
  :global(body) {
    margin: 0;
    color: var(--white);
    font-family: var(--sans);
    font-size: 17px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  :global(a) {
    color: inherit;
  }
  :global(:focus-visible) {
    outline: 2px solid var(--white);
    outline-offset: 3px;
    border-radius: 6px;
  }
  :global(::selection) {
    background: var(--white);
    color: var(--black);
  }
</style>
