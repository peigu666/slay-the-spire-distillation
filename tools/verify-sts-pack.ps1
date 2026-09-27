[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$GameRoot,
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [string[]]$OptionalModsRoot,
    [switch]$VerifyOptionalMods,
    [switch]$VerifyPackFiles,
    [switch]$VerifyWorkshopExternalFiles,
    [switch]$VerifyTemplate
)

$ErrorActionPreference = 'Stop'
$gameRoot = [IO.Path]::GetFullPath($GameRoot)
$packRoot = [IO.Path]::GetFullPath($PackRoot)
$manifest = Get-Content -LiteralPath (Join-Path $packRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = New-Object System.Collections.Generic.List[string]
$ignoredRoots = @('.git', '.hg', '.svn', '__pycache__')
$packPrefix = $packRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar

function Normalize-RelativePath([string]$Path) {
    return $Path.Replace('\', '/')
}

function Test-IgnoredPackPath([string]$RelativePath) {
    $normalized = Normalize-RelativePath $RelativePath
    $parts = $normalized.Split('/')
    return ($parts[0] -in $ignoredRoots) -or $normalized -like 'templates/build/*' -or $normalized -like '*.pyc'
}

function Resolve-PackPath([string]$RelativePath) {
    $normalized = Normalize-RelativePath $RelativePath
    if ([IO.Path]::IsPathRooted($normalized) -or $normalized -eq '..' -or $normalized -like '../*') {
        throw "path is absolute or escapes pack root: $RelativePath"
    }
    $resolved = [IO.Path]::GetFullPath((Join-Path $packRoot ($normalized -replace '/', [IO.Path]::DirectorySeparatorChar)))
    if (-not $resolved.StartsWith($packPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "path escapes pack root: $RelativePath"
    }
    return $resolved
}

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
if ($VerifyOptionalMods) {
    if (-not @($manifest.optional_mods.jars).Count) { Write-Host 'No optional Mod JARs recorded.' -ForegroundColor Yellow }
    elseif (-not $OptionalModsRoot) { $failures.Add('VerifyOptionalMods requires -OptionalModsRoot pointing to the downloaded optional Workshop roots') }
    else {
        foreach ($jar in @($manifest.optional_mods.jars)) {
            $parts = ([string]$jar.portable_path).Split('/')
            if ($parts.Count -lt 3 -or $parts[0] -ne 'optional' -or $parts[1] -notmatch '^\d+$') { $failures.Add("invalid optional Mod path: $($jar.portable_path)"); continue }
            $rootIndex = [int]$parts[1]
            if ($rootIndex -ge @($OptionalModsRoot).Count) { $failures.Add("missing optional Mod root index $rootIndex for $($jar.name)"); continue }
            $relative = ($parts[2..($parts.Count - 1)] -join [IO.Path]::DirectorySeparatorChar)
            $actual = Join-Path ([IO.Path]::GetFullPath($OptionalModsRoot[$rootIndex])) $relative
            if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { $failures.Add("missing optional Mod $($jar.name) [$($jar.portable_path)]: $actual"); continue }
            $item = Get-Item -LiteralPath $actual
            $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
            if (($item.Length -ne [int64]$jar.size) -or ($hash -ne ([string]$jar.sha256).ToUpperInvariant())) { $failures.Add("optional Mod mismatch $($jar.name): sizeOk=$($item.Length -eq [int64]$jar.size) hashOk=$($hash -eq ([string]$jar.sha256).ToUpperInvariant())") }
            else { Write-Host "OK   optional $($jar.name) $hash" -ForegroundColor Green }
        }
    }
}
if ($VerifyWorkshopExternalFiles) {
    $externalIndex = Join-Path $packRoot 'environment\workshop_external_files.jsonl'
    if (-not (Test-Path -LiteralPath $externalIndex -PathType Leaf)) { $failures.Add("missing external Workshop index: $externalIndex") }
    else {
        foreach ($line in Get-Content -LiteralPath $externalIndex -Encoding UTF8) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try { $entry = $line | ConvertFrom-Json } catch { $failures.Add("invalid external Workshop JSON: $($_.Exception.Message)"); continue }
            $portable = [string]$entry.portable_path
            if ($portable -notlike 'workshop/*') { $failures.Add("invalid external Workshop path: $portable"); continue }
            $relative = $portable.Substring(9) -replace '/', [IO.Path]::DirectorySeparatorChar
            $actual = Join-Path $workshopRoot $relative
            if (-not (Test-Path -LiteralPath $actual -PathType Leaf)) { $failures.Add("missing external Workshop file [$portable]: $actual"); continue }
            $item = Get-Item -LiteralPath $actual
            $hash = (Get-FileHash -LiteralPath $actual -Algorithm SHA256).Hash.ToUpperInvariant()
            if ($item.Length -ne [int64]$entry.size -or $hash -ne ([string]$entry.sha256).ToUpperInvariant()) { $failures.Add("external Workshop mismatch: $portable") }
        }
    }
}
if ($VerifyPackFiles) {
    $index = Join-Path $packRoot 'ai_file_index.jsonl'
    if (-not (Test-Path -LiteralPath $index -PathType Leaf)) {
        $failures.Add("missing pack file index: $index")
    }
    $seen = @{}
    $checked = 0
    if (Test-Path -LiteralPath $index -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $index -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $entry = $line | ConvertFrom-Json } catch { $failures.Add("invalid pack index JSON: $($_.Exception.Message)"); continue }
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative)) { $failures.Add('pack index entry has no path'); continue }
        $normalized = Normalize-RelativePath $relative
        if (Test-IgnoredPackPath $normalized) { $failures.Add("pack index contains excluded path: $normalized"); continue }
        if ($seen.ContainsKey($normalized)) { $failures.Add("duplicate pack index path: $normalized"); continue }
        $seen[$normalized] = $true
        try { $file = Resolve-PackPath $normalized } catch { $failures.Add($_.Exception.Message); continue }
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("missing pack file: $normalized"); continue }
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToUpperInvariant()
        $size = (Get-Item -LiteralPath $file).Length
        if ($size -ne [int64]$entry.size -or $hash -ne ([string]$entry.sha256).ToUpperInvariant()) { $failures.Add("pack file mismatch: $normalized") }
        else { $checked++ }
    }
    foreach ($file in Get-ChildItem -LiteralPath $packRoot -File -Recurse -Force) {
        $relative = Normalize-RelativePath ($file.FullName.Substring($packRoot.Length + 1))
        if ($relative -eq 'ai_file_index.jsonl' -or (Test-IgnoredPackPath $relative)) { continue }
        if (-not $seen.ContainsKey($relative)) { $failures.Add("unindexed pack file: $relative") }
    }
    Write-Host "Pack file verification checked $checked file(s)."
    }
}
if ($VerifyTemplate) {
    $templateFiles = @(
        'templates/build.ps1',
        'templates/ModTheSpire.json',
        'templates/README.md',
        'templates/src/main/java/example/MinimalMod.java'
    )
    foreach ($relative in $templateFiles) {
        try { $file = Resolve-PackPath $relative } catch { $failures.Add($_.Exception.Message); continue }
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { $failures.Add("missing template file: $relative") }
    }
    $metadataPath = Join-Path $packRoot 'templates\ModTheSpire.json'
    if (Test-Path -LiteralPath $metadataPath -PathType Leaf) {
        try {
            $metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($key in @('modid', 'name', 'author_list', 'description', 'version')) {
                if ($null -eq $metadata.PSObject.Properties[$key]) { $failures.Add("template metadata missing key: $key") }
            }
        } catch { $failures.Add("invalid template ModTheSpire.json: $($_.Exception.Message)") }
    }
}
$aiManifestPath = Join-Path $packRoot 'ai_manifest.json'
if (-not (Test-Path -LiteralPath $aiManifestPath -PathType Leaf)) {
    $failures.Add("missing AI manifest: $aiManifestPath")
} else {
    try {
        $aiManifest = Get-Content -LiteralPath $aiManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($key in @('pack_id', 'pack_version', 'generated_at_utc', 'ingestion_order', 'default_files', 'on_demand_files')) {
            if ($null -eq $aiManifest.PSObject.Properties[$key]) { $failures.Add("AI manifest missing key: $key") }
        }
    } catch { $failures.Add("invalid AI manifest: $($_.Exception.Message)") }
}
if ($failures.Count) { $failures | ForEach-Object { Write-Host "FAIL $_" -ForegroundColor Red }; exit 1 }
Write-Host 'Verification passed.' -ForegroundColor Green
