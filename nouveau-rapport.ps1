#requires -Version 5.1

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$racineScript = Split-Path -Parent $MyInvocation.MyCommand.Path
$racineModules = Join-Path $racineScript "tools\powershell"

$modules = @(
    "ADCStudio.Common.ps1",
    "ADCStudio.Report.ps1"
)

try {
    foreach ($module in $modules) {
        $modulePath = Join-Path $racineModules $module

        if (-not (Test-Path -LiteralPath $modulePath)) {
            throw "Module ADC Studio introuvable : $modulePath"
        }

        . $modulePath
    }

    New-ADCClientReport -StudioRoot $racineScript | Out-Null
}
catch {
    Write-Host ""
    Write-Host "Erreur : $($_.Exception.Message)" `
        -ForegroundColor Red

    exit 1
}

exit 0