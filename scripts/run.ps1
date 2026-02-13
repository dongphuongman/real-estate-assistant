param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

. (Join-Path $root "scripts\core\_shared\resolve_python.ps1")

$invocation = Get-PythonInvocation -ProjectRoot $root
& $invocation.Python @($invocation.Args) (Join-Path $root "scripts\launcher\start.py") @Args
exit $LASTEXITCODE
