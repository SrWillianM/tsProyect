$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $projectRoot "dist"
$stagingDir = Join-Path $distDir "lan-package"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipPath = Join-Path $distDir ("tsProject-lan-" + $timestamp + ".zip")

Write-Host "== Empaquetando version LAN =="
Write-Host "Proyecto: $projectRoot"

if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
New-Item -ItemType Directory -Path $stagingDir | Out-Null

$excludeDirs = @(
    ".git",
    ".venv",
    "__pycache__",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode"
)

$excludeFiles = @(
    "db.sqlite3",
    "*.pyc",
    "*.pyo"
)

$allFiles = Get-ChildItem -Path $projectRoot -Recurse -File
$filteredFiles = $allFiles | Where-Object {
    $fullPath = $_.FullName

    foreach ($dirName in $excludeDirs) {
        if ($fullPath -match "[\\/]" + [regex]::Escape($dirName) + "([\\/]|$)") {
            return $false
        }
    }

    foreach ($pattern in $excludeFiles) {
        if ($_.Name -like $pattern) {
            return $false
        }
    }

    return $true
}

foreach ($file in $filteredFiles) {
    $relativePath = $file.FullName.Substring($projectRoot.Length).TrimStart('\\')
    $targetPath = Join-Path $stagingDir $relativePath
    $targetDir = Split-Path -Parent $targetPath

    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    Copy-Item -Path $file.FullName -Destination $targetPath -Force
}

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

$zipSizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)

Write-Host ""
Write-Host "ZIP generado:" -ForegroundColor Green
Write-Host $zipPath
Write-Host ("Tamano: " + $zipSizeMb + " MB")
Write-Host ""
Write-Host "Incluye instaladores LAN: instalar_lan.bat, iniciar_lan.bat, crear_admin.bat"
Write-Host "Excluye: .venv, __pycache__, .git, db.sqlite3"
