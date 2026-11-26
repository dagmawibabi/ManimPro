# Bundles LaTeX (TinyTeX + the packages Manim uses) into the app runtime, so
# MathTex / Tex work right after installing ManimPro. Developer machine only.
# Output: src-tauri/runtime/TinyTeX   (shipped with the installer via runtime/)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root "src-tauri\runtime"
$tex = Join-Path $runtime "TinyTeX"
$bundle = Join-Path $runtime "TinyTeX-1-windows.exe"
$url = "https://github.com/rstudio/tinytex-releases/releases/download/daily/TinyTeX-1-windows.exe"

New-Item -ItemType Directory -Force $runtime | Out-Null

if (-not (Test-Path (Join-Path $tex "bin\windows\latex.exe"))) {
    if (-not (Test-Path $bundle)) {
        Write-Host "Downloading TinyTeX (about 74 MB)..."
        curl.exe -L --fail --retry 8 --retry-delay 5 -C - -o $bundle $url
        if ($LASTEXITCODE -ne 0) { throw "download failed" }
    }
    Write-Host "Unpacking TinyTeX..."
    # The release is a 7-Zip self-extractor: -y answers yes, -o sets the folder.
    & $bundle -y "-o$runtime" | Out-Null
    if (-not (Test-Path (Join-Path $tex "bin\windows\latex.exe"))) { throw "TinyTeX did not unpack where expected" }
    Remove-Item $bundle -Force
}

$bin = Join-Path $tex "bin\windows"
$env:PATH = "$bin;$env:PATH"
$packages = @(
    "amsmath", "babel-english", "cbfonts-fd", "cm-super", "count1to", "doublestroke", "dvisvgm", "everysel",
    "fontspec", "frcursive", "fundus-calligra", "gnu-freefont", "jknapltx", "latex-bin", "mathastext",
    "microtype", "multitoc", "physics", "preview", "prelim2e", "ragged2e", "relsize", "rsfs", "setspace",
    "standalone", "tipa", "wasy", "wasysym", "xcolor", "xetex", "xkeyval"
)
Write-Host "Installing the LaTeX packages Manim uses..."
& (Join-Path $bin "tlmgr.bat") install @packages
if ($LASTEXITCODE -ne 0) { throw "tlmgr install failed" }

# Keep the bundle lean: drop documentation and source trees.
foreach ($d in @("texmf-dist\doc", "texmf-dist\source")) {
    $p = Join-Path $tex $d
    if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

foreach ($exe in @("latex.exe", "dvisvgm.exe")) {
    if (-not (Test-Path (Join-Path $bin $exe))) { throw "$exe is missing" }
}
$size = (Get-ChildItem $tex -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("LaTeX ready at {0} ({1:N0} MB)" -f $tex, $size)
