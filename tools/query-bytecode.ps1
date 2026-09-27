[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [string]$TargetClass,
    [string]$TargetMethod,
    [string]$PatchClass,
    [switch]$FullGame,
    [switch]$IncludeInstructions
)

$ErrorActionPreference = 'Stop'
$packRoot = [IO.Path]::GetFullPath($PackRoot)
$targetFile = Join-Path $packRoot 'environment\patch_targets.jsonl'
if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) { throw "Patch target index not found: $targetFile" }
$targetMatches = New-Object System.Collections.Generic.List[object]
foreach ($line in Get-Content -LiteralPath $targetFile -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $item = $line | ConvertFrom-Json
    if ($TargetClass -and $item.target_class -notlike $TargetClass) { continue }
    if ($TargetMethod -and $item.target_method -notlike $TargetMethod) { continue }
    if ($PatchClass -and $item.patch_class -notlike $PatchClass) { continue }
    $targetMatches.Add($item)
}
if (-not $IncludeInstructions -and -not $FullGame) { @($targetMatches.ToArray()) | ConvertTo-Json -Depth 100; exit 0 }
$snapshotFile = Join-Path $packRoot 'bytecode\instruction_snapshots.jsonl'
$wanted = @{}
foreach ($item in $targetMatches) { foreach ($id in @($item.instruction_snapshot_ids)) { $wanted[[string]$id] = $true } }
$snapshots = New-Object System.Collections.Generic.List[object]
if (Test-Path -LiteralPath $snapshotFile -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $snapshotFile -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $item = $line | ConvertFrom-Json
        if ($wanted.ContainsKey([string]$item.snapshot_id)) { $snapshots.Add($item) }
    }
}
$fullSnapshots = New-Object System.Collections.Generic.List[object]
if ($FullGame) {
    $fullFile = Join-Path $packRoot 'bytecode\full_game_instruction_snapshots.jsonl'
    if (-not (Test-Path -LiteralPath $fullFile -PathType Leaf)) { throw "Full base-game bytecode index not found: $fullFile" }
    foreach ($line in Get-Content -LiteralPath $fullFile -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $item = $line | ConvertFrom-Json
        if ($TargetClass -and $item.target_class -notlike $TargetClass) { continue }
        if ($TargetMethod -and $item.target_method -notlike $TargetMethod) { continue }
        $fullSnapshots.Add($item)
    }
}
$result = [ordered]@{ patch_targets=@($targetMatches.ToArray()) }
if ($IncludeInstructions) { $result.instruction_snapshots = @($snapshots.ToArray()) }
if ($FullGame) { $result.full_game_instruction_snapshots = @($fullSnapshots.ToArray()) }
[pscustomobject]$result | ConvertTo-Json -Depth 100
