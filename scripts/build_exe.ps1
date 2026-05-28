# Empacota GEO Extractor como executável Windows (pasta dist/GEO-Extractor/)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "Instalando PyInstaller..."
& $Python -m pip install pyinstaller -q

Write-Host "Limpando build anterior..."
if (Test-Path (Join-Path $Root "build")) { Remove-Item (Join-Path $Root "build") -Recurse -Force }
if (Test-Path (Join-Path $Root "dist")) { Remove-Item (Join-Path $Root "dist") -Recurse -Force }

Write-Host "Gerando executável (pode demorar 5-15 min)..."
& $Python -m PyInstaller geo_extractor.spec --noconfirm --log-level WARN

$Dist = Join-Path $Root "dist\GEO-Extractor"
$EnvExample = Join-Path $Root ".env.example"
$DistEnv = Join-Path $Dist ".env.example"

if (Test-Path $EnvExample) {
    Copy-Item $EnvExample $DistEnv -Force
}

@(
    (Join-Path $Dist "data"),
    (Join-Path $Dist "output")
) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
    }
}

Write-Host ""
Write-Host "Concluído: $Dist\GEO-Extractor.exe"
Write-Host "Copie .env.example para .env na mesma pasta antes de executar."
