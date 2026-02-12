# Convenience script for starting Docker containers for the AI Real Estate Assistant
# This is a wrapper around docker compose with the correct compose file

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$composeFile = "$projectRoot\deploy\compose\docker-compose.yml"

Write-Host "Starting AI Real Estate Assistant with Docker..." -ForegroundColor Green

# Check if Docker is available
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "Error: Docker is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://docker.com" -ForegroundColor Yellow
    exit 1
}

# Check if docker compose is available
Write-Host "Using compose file: $composeFile" -ForegroundColor Cyan
Write-Host ""

# Run docker compose with the correct compose file
& docker compose -f $composeFile up --build
