#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run tests with coverage reports

.DESCRIPTION
    Runs all CI tests with code coverage analysis.
    Generates coverage.xml and terminal coverage report.

    Use this before committing to ensure adequate test coverage.

    This is equivalent to: run_ci_tests_local.ps1 -Coverage

.EXAMPLE
    .\scripts\test-coverage.ps1
#>

Write-Host "Running tests with COVERAGE analysis..." -ForegroundColor Cyan
Write-Host "This will generate coverage.xml report." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\run_ci_tests_local.ps1" -Coverage
