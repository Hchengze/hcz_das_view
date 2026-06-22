param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not $SkipInstall) {
    python -m pip install -e ".[gui,packaging]"
}

python -m PyInstaller "packaging\hcz_das_view.spec" --clean --noconfirm

Write-Host "Build finished. Local artifacts are under build/ and dist/."
Write-Host "Do not commit build/, dist/, wheels, archives, exe files, or real DAS data."
