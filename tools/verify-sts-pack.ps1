[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$GameRoot,
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [switch]$VerifyPackFiles
)

$ErrorActionPreference = 'Stop'
$gameRoot = [IO.Path]::GetFullPath($GameRoot)
$packRoot = [IO.Path]::GetFullPath($PackRoot)
$manifest = Get-Content -LiteralPath (Join-Path $packRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = New-Object System.Collections.Generic.List[string]
$steamapps = Split-Path (Split-Path $gameRoot)
$workshopRoot = Join-Path $steamapps 'workshop\content\646570'
foreach ($jar in @($manifest.jars)) {
    $portable = [string]$jar.portable_path
    if ($portable -like 'workshop/*') {
        $relative = $portable.Substring(9) -replace '/', [IO.Path]::DirectorySeparatorChar
        $actual = Join-Path $workshopRoot $relative
    }
    elseif ($portable -like 'game/*') {
        $relative = $portable.Substring(5) -replace '/', [IO.Path]::DirectorySeparatorChar
        $actual = Join-Path $gameRoot $relative
    }
    else { $actual = Join-Path $gameRoot (($portable) -replace '/', [IO.Path]::DirectorySeparatorChar) }
    if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { $failures.Add("missing $($jar.name) [$portable]: $actual"); continue }
    $item = Get-Item -LiteralPath $actual
    $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
    if (($item.Length -ne [int64]$jar.size) -or ($hash -ne ([string]$jar.sha256).ToUpperInvariant())) { $failures.Add("mismatch $($jar.name) [$portable]: sizeOk=$($item.Length -eq [int64]$jar.size) hashOk=$($hash -eq ([string]$jar.sha256).ToUpperInvariant())") }
    else { Write-Host "OK   $($jar.name) $hash" -ForegroundColor Green }
}
if ($VerifyPackFiles) {
    $index = Join-Path $packRoot 'ai_file_index.jsonl'
    foreach ($line in Get-Content -LiteralPath $index -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $entry = $line | ConvertFrom-Json
        $file = Join-Path $packRoot (($entry.path) -replace '/', [IO.Path]::DirectorySeparatorChar)
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("missing pack file: $($entry.path)"); continue }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToUpperInvariant()
        $size = (Get-Item -LiteralPath $file).Length
        if ($size -ne [int64]$entry.size -or $hash -ne ([string]$entry.sha256).ToUpperInvariant()) { $failures.Add("pack file mismatch: $($entry.path)") }
    }
}
if ($failures.Count) { $failures | ForEach-Object { Write-Host "FAIL $_" -ForegroundColor Red }; exit 1 }
Write-Host 'Verification passed.' -ForegroundColor Green
