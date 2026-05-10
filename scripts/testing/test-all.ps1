#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run ALL tests and see complete picture of failures

.DESCRIPTION
    Runs all CI tests without stopping on first failure.
    Perfect for preparing fixes - you'll see all issues at once.

    This is equivalent to: run_ci_tests_local.ps1 -ContinueOnError

.EXAMPLE
    .\scripts\test-all.ps1
#>

Write-Host "Running ALL tests (will not stop on failures)..." -ForegroundColor Cyan
Write-Host "This will show you the complete picture of all issues." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\run_ci_tests_local.ps1" -ContinueOnError
