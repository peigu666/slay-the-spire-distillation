[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$SteamCmd,
    [string]$DownloadRoot = (Join-Path ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))) 'work\optional-mods')
)

$ErrorActionPreference = 'Stop'
$steamCmdPath = [IO.Path]::GetFullPath($SteamCmd)
$downloadRoot = [IO.Path]::GetFullPath($DownloadRoot)
$manifestPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\environment\optional_mod_manifest.json'))
if (-not (Test-Path -LiteralPath $steamCmdPath -PathType Leaf)) { throw "SteamCMD not found: $steamCmdPath" }
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Optional Mod manifest not found: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $manifest.app_id) { throw "Optional Mod manifest has no Steam app_id." }
New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null

foreach ($mod in @($manifest.mods)) {
    $workshopId = [string]$mod.workshop_id
    if ([string]::IsNullOrWhiteSpace($workshopId)) { throw "Optional Mod entry has no Workshop ID: $($mod.name)" }
    $steamArgs = @(
        '+force_install_dir', $downloadRoot,
        '+login', 'anonymous',
        '+workshop_download_item', [string]$manifest.app_id, $workshopId,
        'validate', '+quit'
    )
    Write-Host "Downloading Workshop $workshopId ($($mod.name))..." -ForegroundColor Cyan
    & $steamCmdPath @steamArgs
    if ($LASTEXITCODE -ne 0) { throw "SteamCMD failed for Workshop $workshopId with exit code $LASTEXITCODE" }

    $fileName = [IO.Path]::GetFileName([string]$mod.file_name)
    $actual = Join-Path $downloadRoot ("steamapps\workshop\content\{0}\{1}\{2}" -f $manifest.app_id, $workshopId, $fileName)
    if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { throw "Downloaded file not found: $actual" }
    $item = Get-Item -LiteralPath $actual
    $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($item.Length -ne [int64]$mod.size -or $hash -ne ([string]$mod.sha256).ToUpperInvariant()) {
        throw "Optional Mod verification failed for $($mod.name): sizeOk=$($item.Length -eq [int64]$mod.size) hashOk=$($hash -eq ([string]$mod.sha256).ToUpperInvariant())"
    }
    Write-Host "OK   $($mod.name) $hash" -ForegroundColor Green
}
Write-Host 'Optional Mod download and verification passed.' -ForegroundColor Green
