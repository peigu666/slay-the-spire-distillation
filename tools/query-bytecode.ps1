[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [string]$TargetClass,
    [string]$TargetMethod,
    [string]$PatchClass,
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
if (-not $IncludeInstructions) { @($targetMatches.ToArray()) | ConvertTo-Json -Depth 100; exit 0 }
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
[pscustomobject][ordered]@{ patch_targets=@($targetMatches.ToArray()); instruction_snapshots=@($snapshots.ToArray()) } | ConvertTo-Json -Depth 100
