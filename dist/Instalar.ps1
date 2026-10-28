<#
    Instalador portátil da tradução PT-BR do Ostriv.

    - Procura o ostriv.exe em instalações Steam, GOG, pastas personalizadas e
      na pasta atual (inclui o layout com Game\Ostriv).
    - Copia o ostriv_ptbr.exe para a pasta correta (cria as pastas necessárias).
    - Cria um launcher PT-BR quando encontra o loader da versão portátil.
    - Seleciona o idioma Português (Brasil) e cria um atalho na área de trabalho.
    - O ostriv.exe original nunca é substituído.

    Uso:
        powershell -ExecutionPolicy Bypass -File Instalar.ps1
        powershell -ExecutionPolicy Bypass -File Instalar.ps1 -GameRoot "D:\Jogos\Ostriv"
#>
param(
    [string]$GameRoot = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$patchFile = Join-Path $here "ostriv_0.5.9.58_ptbr.patch"
$applyScript = Join-Path $here "Apply-Patch.ps1"

function Write-Step($msg) { Write-Host "  $msg" }
function Fail($msg) { Write-Host ""; Write-Host "ERRO: $msg" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $patchFile)) {
    Fail "Arquivo de patch não encontrado ao lado do instalador ($patchFile)."
}
if (-not (Test-Path $applyScript)) {
    Fail "Apply-Patch.ps1 não encontrado ao lado do instalador."
}

# ---------------------------------------------------------------- localizar jogo
function Resolve-GameFolder([string]$folder) {
    if (-not $folder -or -not (Test-Path $folder)) { return $null }
    $folder = (Resolve-Path $folder).Path

    # a própria pasta pode ser o executável
    if ($folder -like "*.exe") { $folder = Split-Path -Parent $folder }

    $candidates = @(
        (Join-Path $folder "ostriv.exe"),
        (Join-Path $folder "Game\Ostriv\ostriv.exe"),
        (Join-Path $folder "Ostriv\ostriv.exe"),
        (Join-Path $folder "bin\ostriv.exe")
    )
    foreach ($exe in $candidates) {
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

function Get-SearchPaths {
    $paths = New-Object System.Collections.Generic.List[string]
    $paths.Add((Get-Location).Path)
    $paths.Add($here)

    # Steam
    $steam = $null
    try { $steam = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction Stop).SteamPath } catch {}
    if (-not $steam) {
        try { $steam = (Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam" -ErrorAction Stop).InstallPath } catch {}
    }
    if ($steam -and (Test-Path $steam)) {
        $paths.Add((Join-Path $steam "steamapps\common\Ostriv"))
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            $content = Get-Content $vdf -Raw
            foreach ($m in [regex]::Matches($content, '"path"\s+"([^"]+)"')) {
                $lib = $m.Groups[1].Value -replace "\\\\", "\"
                $paths.Add((Join-Path $lib "steamapps\common\Ostriv"))
            }
        }
    }

    # Steam/GOG em caminhos comuns
    $paths.Add("C:\Program Files (x86)\Steam\steamapps\common\Ostriv")
    $paths.Add("C:\Program Files\Steam\steamapps\common\Ostriv")
    $paths.Add("C:\GOG Games\Ostriv")
    $paths.Add("C:\Program Files (x86)\GOG Galaxy\Games\Ostriv")
    $paths.Add("C:\Program Files\GOG Galaxy\Games\Ostriv")
    $paths.Add("C:\Games\Ostriv")
    $paths.Add("D:\Games\Ostriv")
    $paths.Add("E:\Games\Ostriv")

    # entradas de desinstalação (Steam/GOG/outros)
    $uninstallKeys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    foreach ($key in $uninstallKeys) {
        try {
            Get-ItemProperty $key -ErrorAction SilentlyContinue |
                Where-Object { $_.DisplayName -like "*Ostriv*" } |
                ForEach-Object {
                    if ($_.InstallLocation) { $paths.Add($_.InstallLocation) }
                }
        } catch {}
    }

    # GOG registry
    foreach ($key in @("HKLM:\SOFTWARE\WOW6432Node\GOG.com\Games\*", "HKLM:\SOFTWARE\GOG.com\Games\*", "HKCU:\SOFTWARE\GOG.com\Games\*")) {
        try {
            Get-ItemProperty $key -ErrorAction SilentlyContinue | ForEach-Object {
                if ($_.path) { $paths.Add($_.path) }
            }
        } catch {}
    }

    return $paths | Select-Object -Unique
}

function Find-Game {
    if ($GameRoot) {
        $g = Resolve-GameFolder $GameRoot
        if ($g) { return $g }
        Fail "Não encontrei ostriv.exe em '$GameRoot'."
    }

    $found = New-Object System.Collections.Generic.List[object]
    foreach ($p in Get-SearchPaths) {
        $g = Resolve-GameFolder $p
        if ($g) {
            if (-not ($found | Where-Object { $_.Exe -eq $g.Exe })) { $found.Add($g) }
        }
    }

    if ($found.Count -eq 1) { return $found[0] }
    if ($found.Count -gt 1) {
        Write-Host "Encontrei mais de uma instalação do Ostriv:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $found.Count; $i++) {
            Write-Host ("  [{0}] {1}" -f ($i + 1), $found[$i].Exe)
        }
        $answer = Read-Host "Escolha o número (Enter = 1)"
        $idx = 1
        if ($answer -match '^\d+$') { $idx = [int]$answer }
        if ($idx -lt 1 -or $idx -gt $found.Count) { $idx = 1 }
        return $found[$idx - 1]
    }

    # busca limitada nos discos
    Write-Host "Procurando ostriv.exe nos discos (pode demorar um pouco)..." -ForegroundColor Yellow
    foreach ($drive in (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\$' })) {
        try {
            $hit = Get-ChildItem -Path $drive.Root -Filter "ostriv.exe" -Recurse -Depth 4 -File -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($hit) {
                return [pscustomobject]@{
                    Exe = $hit.FullName
                    ExeDir = $hit.DirectoryName
                    Root = $hit.DirectoryName
                }
            }
        } catch {}
    }

    # último recurso: seletor de pasta
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Selecione a pasta do Ostriv (onde está o ostriv.exe)"
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $g = Resolve-GameFolder $dialog.SelectedPath
        if ($g) { return $g }
        Fail "A pasta selecionada não contém ostriv.exe."
    }
    Fail "Não foi possível localizar o Ostriv. Informe a pasta com -GameRoot."
}

# ---------------------------------------------------------------- versão
function Get-GameVersion($exe) {
    $vi = (Get-Item $exe).VersionInfo
    return ("{0}.{1}.{2}.{3}" -f $vi.FileMajorPart, $vi.FileMinorPart, $vi.FileBuildPart, $vi.FilePrivatePart)
}

# ---------------------------------------------------------------- idioma
function Set-Portuguese {
    $dir = Join-Path $env:USERPROFILE "Saved Games\Ostriv"
    $settings = Join-Path $dir "settings.data"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    if (-not (Test-Path $settings)) {
        Write-Step "settings.data ainda não existe; selecione 'Português (Brasil)' em Opções > Idioma no primeiro jogo."
        return
    }
    $bytes = [IO.File]::ReadAllBytes($settings)
    $ascii = [Text.Encoding]::ASCII.GetString($bytes)
    $idx = $ascii.IndexOf("iLanguage")
    if ($idx -ge 0) {
        [BitConverter]::GetBytes([int]1).CopyTo($bytes, $idx + "iLanguage".Length)
        [IO.File]::WriteAllBytes($settings, $bytes)
        Write-Step "idioma definido para Português (Brasil)"
    } else {
        Write-Step "não encontrei iLanguage em settings.data; selecione o idioma no jogo."
    }
}

# ---------------------------------------------------------------- instalação
Write-Host ""
Write-Host "=== Instalador da tradução PT-BR do Ostriv ===" -ForegroundColor Cyan
Write-Host ""

$game = Find-Game
Write-Host "Jogo encontrado:" -ForegroundColor Green
Write-Step $game.Exe

$version = Get-GameVersion $game.Exe
Write-Step "versão do executável: $version"

if ($version -ne "0.5.9.58") {
    Write-Host ""
    Write-Host "ATENÇÃO: esta tradução foi gerada para a versão 0.5.9.58." -ForegroundColor Yellow
    Write-Host "Executar o executável traduzido (0.5.9.58) com os dados de outra versão pode causar erros." -ForegroundColor Yellow
    $answer = Read-Host "Continuar mesmo assim? (s/N)"
    if ($answer -notmatch '^[sS]') {
        Write-Host "Instalação cancelada. O jogo não foi alterado."
        exit 0
    }
}

# backup do executável original (não é substituído, mas guardamos por segurança)
$backupDir = Join-Path $game.ExeDir "backup_ptbr"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$backupExe = Join-Path $backupDir "ostriv.exe"
if (-not (Test-Path $backupExe)) {
    Copy-Item $game.Exe $backupExe -Force
    Write-Step "backup do original: $backupExe"
}

# gera o executável traduzido aplicando o patch ao executável original
$target = Join-Path $game.ExeDir "ostriv_ptbr.exe"
try {
    & $applyScript -InputExe $game.Exe -OutputExe $target -PatchFile $patchFile
} catch {
    Write-Host ""
    Write-Host "O executável encontrado não é exatamente o build 0.5.9.58 esperado." -ForegroundColor Yellow
    Write-Host "A tradução pode não funcionar neste build." -ForegroundColor Yellow
    $answer = Read-Host "Tentar aplicar o patch mesmo assim? (s/N)"
    if ($answer -notmatch '^[sS]') {
        Fail "Instalação cancelada. O jogo não foi alterado."
    }
    & $applyScript -InputExe $game.Exe -OutputExe $target -PatchFile $patchFile -AllowDifferentBuild
}
Write-Step "tradução instalada: $target"

# launcher para a versão portátil (loader Play - Ostriv.exe)
$loader = $null
$loaderIni = $null
$gameRoot = Split-Path -Parent (Split-Path -Parent $game.ExeDir)
if ($game.ExeDir -like "*\Game\Ostriv" -and (Test-Path (Join-Path $gameRoot "Play - Ostriv.exe"))) {
    $loader = Join-Path $gameRoot "Play - Ostriv PT-BR.exe"
    $loaderIni = Join-Path $gameRoot "Play - Ostriv PT-BR.ini"
    Copy-Item (Join-Path $gameRoot "Play - Ostriv.exe") $loader -Force
    $origIni = Join-Path $gameRoot "Play - Ostriv.ini"
    (Get-Content $origIni -Raw) -replace '(?m)^Exe=.*$', 'Exe=.\Game\Ostriv\ostriv_ptbr.exe' |
        Set-Content $loaderIni -Encoding ASCII
    Write-Step "launcher PT-BR criado: $loader"
}

# idioma
Set-Portuguese

# atalho
try {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ostriv PT-BR.lnk"
    $sc = $ws.CreateShortcut($lnk)
    if ($loader) {
        $sc.TargetPath = $loader
        $sc.WorkingDirectory = $gameRoot
    } else {
        $sc.TargetPath = $target
        $sc.WorkingDirectory = $game.ExeDir
    }
    $sc.Save()
    Write-Step "atalho criado: $lnk"
} catch {
    Write-Step "(não foi possível criar o atalho: $_)"
}

Write-Host ""
Write-Host "Pronto!" -ForegroundColor Green
if ($loader) {
    Write-Host "Inicie pelo atalho 'Ostriv PT-BR' ou por: $loader"
} else {
    Write-Host "Inicie pelo atalho 'Ostriv PT-BR' ou por: $target"
}
Write-Host "O executável original ($($game.Exe)) não foi alterado."
Write-Host ""
