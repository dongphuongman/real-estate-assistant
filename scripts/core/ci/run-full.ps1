param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $root

. (Join-Path $PSScriptRoot "..\_shared\resolve_python.ps1")

$invocation = Get-PythonInvocation -ProjectRoot $root
& $invocation.Python @($invocation.Args) (Join-Path $root "scripts\ci\ci_parity.py") @Args
exit $LASTEXITCODE
