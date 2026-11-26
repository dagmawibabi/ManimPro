<script lang="ts">
  let { size = 16 }: { size?: number } = $props();
</script>

<!-- The two-snake Python mark, for .py files. -->
<svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
  <path
    fill="#4b8bbe"
    d="M7.9 1.2c-3.1 0-2.9 1.35-2.9 1.35v1.4h2.95v.42H3.85S1.9 4.15 1.9 7.2s1.7 2.95 1.7 2.95h1V8.72s-.05-1.7 1.67-1.7h2.85s1.6.03 1.6-1.56V2.85S11 1.2 7.9 1.2zM6.3 2.1a.53.53 0 1 1 0 1.06.53.53 0 0 1 0-1.06z"
  />
  <path
    fill="#ffd43b"
    d="M8.1 14.8c3.1 0 2.9-1.35 2.9-1.35v-1.4H8.05v-.42h4.1s1.95.22 1.95-2.83-1.7-2.95-1.7-2.95h-1v1.43s.05 1.7-1.67 1.7H6.88s-1.6-.03-1.6 1.56v2.61S5 14.8 8.1 14.8zm1.6-.9a.53.53 0 1 1 0-1.06.53.53 0 0 1 0 1.06z"
  />
</svg>
