param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

python (Join-Path $root "scripts\dev\start.py") --mode docker --docker-mode cpu @Args

