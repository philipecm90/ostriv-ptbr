<#
    Aplica o patch binário da tradução PT-BR ao ostriv.exe original.

    Uso:
        powershell -ExecutionPolicy Bypass -File Apply-Patch.ps1 `
            -InputExe "C:\...\ostriv.exe" `
            -OutputExe "C:\...\ostriv_ptbr.exe" `
            -PatchFile ".\ostriv_0.5.9.58_ptbr.patch"

    O patch verifica o SHA1 do executável original. Use -AllowDifferentBuild para
    tentar aplicar em um build diferente da mesma versão (por sua conta e risco).
#>
param(
    [Parameter(Mandatory = $true)][string]$InputExe,
    [Parameter(Mandatory = $true)][string]$OutputExe,
    [Parameter(Mandatory = $true)][string]$PatchFile,
    [switch]$AllowDifferentBuild
)

$ErrorActionPreference = "Stop"

function Get-Sha1([byte[]]$data) {
    $sha = [System.Security.Cryptography.SHA1]::Create()
    try { return $sha.ComputeHash($data) } finally { $sha.Dispose() }
}

function Bytes-Equal([byte[]]$a, [byte[]]$b) {
    if ($a.Length -ne $b.Length) { return $false }
    for ($i = 0; $i -lt $a.Length; $i++) { if ($a[$i] -ne $b[$i]) { return $false } }
    return $true
}

if (-not (Test-Path $InputExe)) { throw "Executável não encontrado: $InputExe" }
if (-not (Test-Path $PatchFile)) { throw "Patch não encontrado: $PatchFile" }

$patch = [IO.File]::ReadAllBytes($PatchFile)
$orig = [IO.File]::ReadAllBytes($InputExe)

$p = 0
$magic = [Text.Encoding]::ASCII.GetString($patch, 0, 8)
if ($magic -ne "OPTBR1`0`0") { throw "Arquivo de patch inválido (magic)." }
$p = 8
$version = [BitConverter]::ToUInt32($patch, $p); $p += 4
if ($version -ne 1) { throw "Versão de patch não suportada: $version" }
$origSize = [BitConverter]::ToUInt64($patch, $p); $p += 8
$patchSize = [BitConverter]::ToUInt64($patch, $p); $p += 8
$origSha = New-Object byte[] 20
[Array]::Copy($patch, $p, $origSha, 0, 20); $p += 20
$patchSha = New-Object byte[] 20
[Array]::Copy($patch, $p, $patchSha, 0, 20); $p += 20
$editCount = [BitConverter]::ToUInt32($patch, $p); $p += 4

if ($orig.Length -ne $origSize) {
    if (-not $AllowDifferentBuild) { throw "Tamanho do executável diferente do esperado ($($orig.Length) != $origSize)." }
    Write-Host "AVISO: tamanho diferente do esperado; continuando por sua conta e risco." -ForegroundColor Yellow
} elseif (-not (Bytes-Equal (Get-Sha1 $orig) $origSha)) {
    if (-not $AllowDifferentBuild) {
        throw "Este executável não é o build 0.5.9.58 esperado (SHA1 diferente). Use -AllowDifferentBuild para tentar mesmo assim."
    }
    Write-Host "AVISO: SHA1 diferente do build esperado; continuando por sua conta e risco." -ForegroundColor Yellow
}

$out = New-Object byte[] $patchSize
[Array]::Copy($orig, 0, $out, 0, [Math]::Min($orig.Length, $out.Length))

for ($i = 0; $i -lt $editCount; $i++) {
    $offset = [BitConverter]::ToUInt64($patch, $p); $p += 8
    $length = [BitConverter]::ToUInt32($patch, $p); $p += 4
    if (($offset + $length) -gt $out.Length) { throw "Edição fora dos limites do executável." }
    [Array]::Copy($patch, $p, $out, [int]$offset, [int]$length)
    $p += $length
}

$tailLen = [BitConverter]::ToUInt32($patch, $p); $p += 4
$tailStart = $origSize
if (($tailStart + $tailLen) -gt $out.Length) { throw "Tail fora dos limites." }
[Array]::Copy($patch, $p, $out, [int]$tailStart, [int]$tailLen)

if (-not (Bytes-Equal (Get-Sha1 $out) $patchSha)) {
    throw "O executável gerado não confere com o patch (SHA1). O build pode ser incompatível."
}

[IO.File]::WriteAllBytes($OutputExe, $out)
Write-Host "OK: $OutputExe" -ForegroundColor Green
