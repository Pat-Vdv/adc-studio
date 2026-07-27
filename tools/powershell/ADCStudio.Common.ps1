function Convert-ToSafeName {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Text
    )

    $normalized = $Text.Normalize(
        [System.Text.NormalizationForm]::FormD
    )

    $builder = New-Object System.Text.StringBuilder

    foreach ($character in $normalized.ToCharArray()) {
        $category = [Globalization.CharUnicodeInfo]::GetUnicodeCategory(
            $character
        )

        if (
            $category -ne
            [Globalization.UnicodeCategory]::NonSpacingMark
        ) {
            [void]$builder.Append($character)
        }
    }

    $safeName = $builder.ToString().Normalize(
        [System.Text.NormalizationForm]::FormC
    )

    $safeName = $safeName -replace '[<>:"/\\|?*]', ''
    $safeName = $safeName -replace '[^\p{L}\p{Nd}\-]+', '_'
    $safeName = $safeName -replace '_+', '_'
    $safeName = $safeName.Trim('_', '-', ' ')

    return $safeName
}

function Read-RequiredValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Prompt
    )

    do {
        $value = Read-Host $Prompt

        if ([string]::IsNullOrWhiteSpace($value)) {
            Write-Host `
                "Cette information est obligatoire." `
                -ForegroundColor Yellow
        }
    }
    while ([string]::IsNullOrWhiteSpace($value))

    return $value.Trim()
}

function Write-ADCStudioHeader {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Title
    )

    Write-Host ""
    Write-Host "========================================" `
        -ForegroundColor Cyan
    Write-Host "  A.D.C. Studio - $Title" `
        -ForegroundColor Cyan
    Write-Host "========================================" `
        -ForegroundColor Cyan
    Write-Host ""
}