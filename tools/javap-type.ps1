[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$JavaHome,
    [Parameter(Mandatory = $true)] [string]$TypeName,
    [Parameter(Mandatory = $true)] [string[]]$Jar,
    [switch]$Bytecode
)
$ErrorActionPreference = 'Stop'
$javap = Join-Path ([IO.Path]::GetFullPath($JavaHome)) 'bin\javap.exe'
if (-not (Test-Path -LiteralPath $javap)) { throw "javap.exe not found: $javap" }
$cp = $Jar -join [IO.Path]::PathSeparator
$args = @('-classpath', $cp, '-p', '-s')
if ($Bytecode) { $args += '-c' }
$args += $TypeName
& $javap @args
exit $LASTEXITCODE
