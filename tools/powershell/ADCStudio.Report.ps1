function New-ADCClientReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$StudioRoot
    )

    Write-ADCStudioHeader -Title "Nouveau rapport client"

    $client = Read-RequiredValue "Nom du client"
    $titre = Read-RequiredValue "Titre ou objet du rapport"

    $dateParDefaut = Get-Date -Format "yyyy-MM-dd"
    $dateSaisie = Read-Host "Date du rapport [$dateParDefaut]"

    if ([string]::IsNullOrWhiteSpace($dateSaisie)) {
        $dateRapport = Get-Date
    }
    else {
        try {
            $dateRapport = [datetime]::ParseExact(
                $dateSaisie.Trim(),
                "yyyy-MM-dd",
                [Globalization.CultureInfo]::InvariantCulture
            )
        }
        catch {
            throw "Date invalide. Utilise le format AAAA-MM-JJ."
        }
    }

    $auteurParDefaut = "A.D.C. srl"
    $auteur = Read-Host "Auteur [$auteurParDefaut]"

    if ([string]::IsNullOrWhiteSpace($auteur)) {
        $auteur = $auteurParDefaut
    }

    $classification = Read-Host "Classification [Confidentiel]"

    if ([string]::IsNullOrWhiteSpace($classification)) {
        $classification = "Confidentiel"
    }

    $clientSafe = Convert-ToSafeName $client
    $titreSafe = Convert-ToSafeName $titre

    $annee = $dateRapport.ToString("yyyy")
    $dateISO = $dateRapport.ToString("yyyy-MM-dd")
    $nomMission = "${dateISO}_${titreSafe}"

    $racineRapports = Join-Path $StudioRoot "rapports-clients"

    $dossierMission = Join-Path `
        $racineRapports `
        (Join-Path $clientSafe (Join-Path $annee $nomMission))

    if (Test-Path $dossierMission) {
        throw "Le dossier existe déjà : $dossierMission"
    }

    $repertoires = @(
        "rapport",
        "rapport\versions",
        "captures",
        "annexes",
        "annexes\logs",
        "annexes\scripts",
        "annexes\exports",
        "annexes\documents",
        "travail"
    )

    foreach ($repertoire in $repertoires) {
        $chemin = Join-Path $dossierMission $repertoire

        New-Item `
            -ItemType Directory `
            -Path $chemin `
            -Force |
            Out-Null
    }

    $notesPath = Join-Path `
        $dossierMission `
        "travail\notes.md"

    $todoPath = Join-Path `
        $dossierMission `
        "travail\todo.md"

    $brouillonPath = Join-Path `
        $dossierMission `
        "travail\brouillon.md"

    @"
# Notes — $titre

## Client

$client

## Contexte

À compléter.

## Informations collectées

-

## Actions réalisées

-

## Résultats

-
"@ | Set-Content -Path $notesPath -Encoding UTF8

    @"
# À faire — $titre

- [ ] Rassembler les informations
- [ ] Importer les captures d'écran
- [ ] Ajouter les logs et scripts utiles
- [ ] Rédiger le rapport
- [ ] Effectuer la relecture
- [ ] Générer le PDF
- [ ] Valider la version finale
"@ | Set-Content -Path $todoPath -Encoding UTF8

    @"
# Brouillon — $titre

## 1. Contexte

## 2. Environnement

## 3. Symptômes ou demande initiale

## 4. Analyse

## 5. Actions réalisées

## 6. Résultats

## 7. Recommandations

## 8. Conclusion

## Annexes
"@ | Set-Content -Path $brouillonPath -Encoding UTF8

    $metadataPath = Join-Path $dossierMission "metadata.yml"

    @"
client: "$client"
titre: "$titre"
date: "$dateISO"
annee: "$annee"
auteur: "$auteur"
version: "0.1"
etat: "Brouillon"
classification: "$classification"

reference: ""
framework_version: "1.0"

livrables:
  word: ""
  pdf: ""

repertoires:
  rapport: "rapport"
  captures: "captures"
  annexes: "annexes"
  travail: "travail"
"@ | Set-Content -Path $metadataPath -Encoding UTF8

    Write-Host ""
    Write-Host "Rapport créé avec succès." `
        -ForegroundColor Green
    Write-Host ""
    Write-Host "Client  : $client"
    Write-Host "Rapport : $titre"
    Write-Host "Dossier : $dossierMission"
    Write-Host ""

    $ouvrir = Read-Host "Ouvrir le dossier maintenant ? [O/n]"

    if (
        [string]::IsNullOrWhiteSpace($ouvrir) -or
        $ouvrir -match '^[OoYy]'
    ) {
        Start-Process explorer.exe $dossierMission
    }

    return $dossierMission
}