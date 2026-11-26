# Builds the private Python runtime that ships inside ManimPro.
# Output: src-tauri/runtime/python  (relocatable CPython 3.12 + manim + ffmpeg)
# Requires uv on the developer machine only. End users never run this.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root "src-tauri\runtime"
$python = Join-Path $runtime "python"

New-Item -ItemType Directory -Force $runtime | Out-Null
# Be patient with slow connections; scipy and ffmpeg wheels are large.
if (-not $env:UV_HTTP_TIMEOUT) { $env:UV_HTTP_TIMEOUT = "600" }
if (-not $env:UV_HTTP_RETRIES) { $env:UV_HTTP_RETRIES = "8" }
if (Test-Path $python) {
    $item = Get-Item $python -Force
    if ($item.LinkType) { $item.Delete() } else { Remove-Item -Recurse -Force $python }
}

# Install (or reuse) a standalone CPython in uv's own store; it is cached there for next time.
Write-Host "Locating standalone CPython 3.12 (downloads once if missing)..."
uv python install 3.12
if ($LASTEXITCODE -ne 0) { throw "uv python install failed" }

# uv keeps versioned folders plus junctions like cpython-3.12-windows-...; copy a real folder.
$store = (uv python dir).Trim()
$src = Get-ChildItem $store -Directory -Force |
    Where-Object { -not $_.LinkType -and $_.Name -match '^cpython-3\.12\.\d+-windows-x86_64-none$' } |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $src) { throw "No CPython 3.12 folder found in $store" }

Write-Host "Copying $($src.Name) into the app runtime..."
robocopy $src.FullName $python /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "copy failed (robocopy $LASTEXITCODE)" }

$exe = Join-Path $python "python.exe"
# uv-managed interpreters are marked externally managed; this copy is private to the app.
Get-ChildItem $python -Recurse -Filter "EXTERNALLY-MANAGED" -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "Installing manim and ffmpeg into the runtime..."
# jedi + pyflakes power the code editor's completions, hover docs and warnings.
uv pip install --python $exe --link-mode copy manim imageio-ffmpeg jedi pyflakes
if ($LASTEXITCODE -ne 0) { throw "uv pip install failed" }

Write-Host "Precompiling bytecode (faster first launch)..."
& $exe -m compileall -q -j 0 (Join-Path $python "Lib") | Out-Null

& $exe -c "import manim, imageio_ffmpeg; print('manim', manim.__version__); print('ffmpeg', imageio_ffmpeg.get_ffmpeg_exe())"
if ($LASTEXITCODE -ne 0) { throw "runtime self-test failed" }
Write-Host "Runtime ready at $python"
