#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick test run for rapid feedback during development

.DESCRIPTION
    Runs tests in fast mode:
    - Skips slow tests
    - Skips mypy type checking
    - Parallel execution enabled
    - No coverage reports

    Perfect for quick validation during active development.

    This is equivalent to: run_ci_tests_local.ps1 -Fast

.EXAMPLE
    .\scripts\test-fast.ps1
#>

Write-Host "Running tests in FAST mode..." -ForegroundColor Cyan
Write-Host "Skipping slow tests and type checking for quick feedback." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\run_ci_tests_local.ps1" -Fast
