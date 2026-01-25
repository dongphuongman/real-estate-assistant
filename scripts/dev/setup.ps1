param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

python (Join-Path $root "scripts\dev\bootstrap_uv.py") --dev @Args
