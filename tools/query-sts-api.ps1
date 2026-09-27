[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$PackRoot,
    [ValidateSet('base_game','modthespire','basemod','stslib','installed_mods','optional_mods','third_party')]
    [string]$Role = 'base_game',
    [Parameter(Mandatory = $true)] [string]$TypeName,
    [string]$Member,
    [switch]$IncludeBody
)

$ErrorActionPreference = 'Stop'
$files = @{
    base_game = 'base_game_api.types.jsonl'
    modthespire = 'modthespire_api.types.jsonl'
    basemod = 'basemod_api.types.jsonl'
    stslib = 'stslib_api.types.jsonl'
    installed_mods = 'installed_mods_api.types.jsonl'
    optional_mods = 'optional_mods_api.types.jsonl'
    third_party = 'third_party_api.types.jsonl'
}
$jsonl = Join-Path ([IO.Path]::GetFullPath($PackRoot)) ('api\' + $files[$Role])
if (-not (Test-Path -LiteralPath $jsonl -PathType Leaf)) { throw "API JSONL not found: $jsonl" }
$results = New-Object System.Collections.Generic.List[object]
foreach ($line in Get-Content -LiteralPath $jsonl -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $record = $line | ConvertFrom-Json
    if (($record.full_name -ne $TypeName) -and ($record.name -ne $TypeName) -and ($record.full_name -notlike $TypeName)) { continue }
    if ([string]::IsNullOrWhiteSpace($Member)) {
        if ($IncludeBody) { $results.Add($record); continue }
        $results.Add([pscustomobject][ordered]@{
            full_name = $record.full_name
            source_jar = $record.source_jar
            super_type = $record.super_type
            interfaces = @($record.interfaces)
            kind = $record.kind
            annotations = @($record.annotations)
            methods = @($record.methods | ForEach-Object {
                [pscustomobject][ordered]@{ name=$_.name; descriptor=$_.descriptor; return_type=$_.return_type; parameter_types=@($_.parameter_types); access=@($_.access); exceptions=@($_.exceptions); code=$_.code }
            })
            fields = @($record.fields | ForEach-Object {
                [pscustomobject][ordered]@{ name=$_.name; descriptor=$_.descriptor; field_type=$_.field_type; access=@($_.access); constant_value=$_.constant_value }
            })
        })
        continue
    }
    $methods = @($record.methods | Where-Object { $_.name -like $Member -or $_.full_name -like $Member })
    $fields = @($record.fields | Where-Object { $_.name -like $Member })
    if (($methods.Count + $fields.Count) -gt 0) {
        $results.Add([pscustomobject][ordered]@{ full_name=$record.full_name; source_jar=$record.source_jar; methods=$methods; fields=$fields })
    }
}
if ($results.Count -eq 0) { throw "No match. Role=$Role TypeName=$TypeName Member=$Member" }
$results | ConvertTo-Json -Depth 100
