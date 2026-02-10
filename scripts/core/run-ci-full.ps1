param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

python (Join-Path $root "scripts\ci\ci_full.py") --mode local @Args
exit $LASTEXITCODE
