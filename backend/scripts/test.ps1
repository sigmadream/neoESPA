#Requires -Version 5.1
<#
.SYNOPSIS
    Docker 기반 백엔드 테스트 실행기 (Windows PowerShell).

.EXAMPLE
    .\backend\scripts\test.ps1
    .\backend\scripts\test.ps1 tests/grading -k lint
    .\backend\scripts\test.ps1 -Service coverage
    .\backend\scripts\test.ps1 -Service format
#>
[CmdletBinding()]
param(
    [ValidateSet('tests', 'tests-live', 'coverage', 'format')]
    [string]$Service = 'tests',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $repoRoot 'docker-compose.test.yml'

$arguments = @('compose', '-f', $composeFile, 'run', '--rm', '--build', $Service)
if ($PytestArgs) { $arguments += $PytestArgs }

& docker @arguments
exit $LASTEXITCODE
