param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
& (Join-Path $root "scripts\core\local\run.ps1") @Args
exit $LASTEXITCODE
