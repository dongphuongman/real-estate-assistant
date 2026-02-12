# Convenience script for running the AI Real Estate Assistant locally
# This is a wrapper around the launcher script with sensible defaults

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Write-Host "Starting AI Real Estate Assistant..." -ForegroundColor Green
Write-Host "Project root: $projectRoot" -ForegroundColor Cyan

# Check if Python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "Error: Python is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Run the launcher script with sensible defaults
& python "$projectRoot\scripts\launcher\start.py" @args
