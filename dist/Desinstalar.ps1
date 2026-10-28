<#
    Desinstalador portátil da tradução PT-BR do Ostriv.
#>
param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-GameFolder([string]$folder) {
    if (-not $folder -or -not (Test-Path $folder)) { return $null }
    $folder = (Resolve-Path $folder).Path
    foreach ($exe in @(
        (Join-Path $folder "ostriv.exe"),
        (Join-Path $folder "Game\Ostriv\ostriv.exe"),
        (Join-Path $folder "Ostriv\ostriv.exe")
    )) {
        if (Test-Path $exe) {
            return [pscustomobject]@{
                Exe = (Resolve-Path $exe).Path
                ExeDir = (Split-Path -Parent $exe)
                Root = $folder
            }
        }
    }
    return $null
}

function Find-Game {
    if ($GameRoot) {
        $g = Resolve-GameFolder $GameRoot
        if ($g) { return $g }
    }
    $candidates = @(
        (Get-Location).Path,
        $here,
        "C:\Games\Ostriv",
        "D:\Games\Ostriv",
        "C:\Program Files (x86)\Steam\steamapps\common\Ostriv",
        "C:\Program Files\Steam\steamapps\common\Ostriv",
        "C:\GOG Games\Ostriv"
    )
    foreach ($p in $candidates) {
        $g = Resolve-GameFolder $p
        if ($g) { return $g }
    }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Selecione a pasta do Ostriv"
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return (Resolve-GameFolder $dialog.SelectedPath)
    }
    return $null
}

Write-Host ""
Write-Host "=== Desinstalador da tradução PT-BR do Ostriv ===" -ForegroundColor Cyan
$game = Find-Game
if (-not $game) { Write-Host "Não encontrei o Ostriv." -ForegroundColor Red; exit 1 }

$gameRoot = Split-Path -Parent (Split-Path -Parent $game.ExeDir)
$files = @(
    (Join-Path $game.ExeDir "ostriv_ptbr.exe"),
    (Join-Path $gameRoot "Play - Ostriv PT-BR.exe"),
    (Join-Path $gameRoot "Play - Ostriv PT-BR.ini"),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Ostriv PT-BR.lnk")
)
foreach ($f in $files) {
    if (Test-Path $f) {
        Remove-Item $f -Force
        Write-Host "removido: $f"
    }
}

# volta o idioma para inglês
$settings = Join-Path $env:USERPROFILE "Saved Games\Ostriv\settings.data"
if (Test-Path $settings) {
    $bytes = [IO.File]::ReadAllBytes($settings)
    $ascii = [Text.Encoding]::ASCII.GetString($bytes)
    $idx = $ascii.IndexOf("iLanguage")
    if ($idx -ge 0) {
        [BitConverter]::GetBytes([int]0).CopyTo($bytes, $idx + "iLanguage".Length)
        [IO.File]::WriteAllBytes($settings, $bytes)
        Write-Host "idioma restaurado para English"
    }
}

Write-Host ""
Write-Host "Tradução desinstalada. O jogo original continua funcionando." -ForegroundColor Green
