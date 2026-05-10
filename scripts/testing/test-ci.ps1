#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run full CI test suite (exactly as CI does)

.DESCRIPTION
    Runs the complete CI test suite with all checks:
    - Linting (ruff)
    - RuleEngine test
    - Security scans
    - OpenAPI diff
    - Alembic migrations
    - Unit tests (parallel)
    - Integration tests (parallel)
    - Type checking (mypy)

    Use this before pushing to ensure CI will pass.

    This is the default mode: run_ci_tests_local.ps1

.EXAMPLE
    .\scripts\test-ci.ps1
#>

Write-Host "Running FULL CI test suite..." -ForegroundColor Cyan
Write-Host "This replicates exactly what GitHub Actions will run." -ForegroundColor Cyan
Write-Host ""

& "$PSScriptRoot\run_ci_tests_local.ps1"
