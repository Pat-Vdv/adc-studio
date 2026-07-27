param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"

Write-Host "Initialisation d'ADC Studio dans : $Root"

$folders = @(
    "assets\logos",
    "assets\icons",
    "assets\images",
    "brand",
    "components",
    "docs",
    "examples",
    "templates\word",
    "templates\pdf",
    "tools",
    "build",
    "exports"
)

foreach ($folder in $folders) {
    $path = Join-Path $Root $folder
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}

Write-Host "Structure vérifiée."
Write-Host "Pense à exécuter : git status"
