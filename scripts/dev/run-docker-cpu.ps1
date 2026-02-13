param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
& (Join-Path $root "scripts\core\docker\cpu.ps1") @Args
exit $LASTEXITCODE
