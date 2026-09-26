[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$StsRoot,
    [Parameter(Mandatory = $true)] [string]$JavaHome,
    [string]$ModTheSpireJar,
    [string]$BaseModJar,
    [string]$StSLibJar,
    [string]$OutputJar = (Join-Path $PSScriptRoot 'MinimalStsMod.jar')
)
$ErrorActionPreference = 'Stop'
$StsRoot = [IO.Path]::GetFullPath($StsRoot)
$JavaHome = [IO.Path]::GetFullPath($JavaHome)
$steamapps = Split-Path (Split-Path $StsRoot)
$workshopRoot = Join-Path $steamapps 'workshop\content\646570'
if (-not $ModTheSpireJar) { $ModTheSpireJar = (Get-ChildItem $workshopRoot -Filter ModTheSpire.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
if (-not $BaseModJar) { $BaseModJar = (Get-ChildItem $workshopRoot -Filter BaseMod.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
if (-not $StSLibJar) { $StSLibJar = (Get-ChildItem $workshopRoot -Filter StSLib.jar -Recurse | Select-Object -First 1 -ExpandProperty FullName) }
$javac = Join-Path $JavaHome 'bin\javac.exe'
$jar = Join-Path $JavaHome 'bin\jar.exe'
$required = @($javac, $jar, (Join-Path $StsRoot 'desktop-1.0.jar'), $ModTheSpireJar, $BaseModJar)
foreach ($file in $required) { if (-not $file -or -not (Test-Path -LiteralPath $file)) { throw "Missing build input: $file" } }
$classes = Join-Path $PSScriptRoot 'build\classes'
New-Item -ItemType Directory -Force -Path $classes | Out-Null
$cp = @((Join-Path $StsRoot 'desktop-1.0.jar'), $ModTheSpireJar, $BaseModJar, $StSLibJar) -join [IO.Path]::PathSeparator
$sources = Get-ChildItem (Join-Path $PSScriptRoot 'src\main\java') -Filter *.java -Recurse | Select-Object -ExpandProperty FullName
& $javac -encoding UTF-8 -source 8 -target 8 -cp $cp -d $classes $sources
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'ModTheSpire.json') -Destination $classes -Force
& $jar cf $OutputJar -C $classes .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Built $OutputJar"
