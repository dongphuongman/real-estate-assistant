# ┌──────────────────────────────────────────────────────────────────┐
# │ AI-generated changes below this line are forbidden without      │
# │ human review. This is the unified Docker start script.          │
# │ Edit env.ps1 for project-specific configuration.                │
# └──────────────────────────────────────────────────────────────────┘
#Requires -Version 7.0
[CmdletBinding()]
param(
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$RuntimeDir = Join-Path $ProjectDir ".runtime"

# ─── Check Docker availability ─────────────────────────────────────
function Test-DockerAvailable {
    try {
        $null = docker info 2>&1
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-DockerAvailable)) {
    Write-Host ""
    Write-Host "❌ Docker is not running or not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    if ($IsWindows -or $env:OS -match "Windows") {
        Write-Host "  Windows: Start Docker Desktop from Start Menu" -ForegroundColor DarkGray
        Write-Host "  Or run:  Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'" -ForegroundColor DarkGray
    } else {
        Write-Host "  Linux: sudo systemctl start docker" -ForegroundColor DarkGray
        Write-Host "  Or:    sudo systemctl start docker.service" -ForegroundColor DarkGray
    }
    Write-Host ""
    exit 1
}

# ─── Source project config ────────────────────────────────────────
$EnvScript = Join-Path $ScriptDir "env.ps1"
if (-not (Test-Path $EnvScript)) {
    Write-Error "❌ Missing env.ps1 — copy from scripts/templates/env.ps1 and customize"
    exit 1
}
. $EnvScript

# ─── Resolve nestdev ──────────────────────────────────────────────
function Find-RepoRoot {
    $dir = $ProjectDir
    while ($dir -and $dir -ne [System.IO.Path]::GetPathRoot($dir)) {
        $nestdevPath = Join-Path $dir "scripts/nestdev/nestdev.mjs"
        if (Test-Path $nestdevPath) { return $dir }
        $dir = Split-Path -Parent $dir
    }
    return $null
}

$RepoRoot = Find-RepoRoot
$NestdevPath = Join-Path $RepoRoot "scripts/nestdev/nestdev.mjs"

if (-not $RepoRoot -or -not (Test-Path $NestdevPath)) {
    Write-Error "❌ Cannot find nestdev — ensure this project is inside the NestSolo meta-repo"
    exit 1
}

# ─── Create .runtime directory ───────────────────────────────────
if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
}

# ─── Cleanup function ────────────────────────────────────────────
function Invoke-DockerCleanup {
    Write-Host ""
    Write-Host "🧹 Cleaning up Docker containers and .runtime/..." -ForegroundColor Yellow

    # Stop docker compose
    $composeFiles = @("docker-compose.yml", "docker-compose.dev.yml")
    foreach ($cf in $composeFiles) {
        $cfPath = Join-Path $ProjectDir $cf
        if (Test-Path $cfPath) {
            docker compose -f $cfPath down --remove-orphans 2>$null
            break
        }
    }

    # Remove runtime files
    @("port.txt", "pid.txt", "ports.json") | ForEach-Object {
        $f = Join-Path $RuntimeDir $_
        if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
    }
    if ((Test-Path $RuntimeDir) -and (Get-ChildItem $RuntimeDir -ErrorAction SilentlyContinue).Count -eq 0) {
        Remove-Item $RuntimeDir -Force -ErrorAction SilentlyContinue
    }

    Write-Host "✅ Cleanup complete" -ForegroundColor Green
}

$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Invoke-DockerCleanup } -ErrorAction SilentlyContinue

# ─── Rebuild if requested ─────────────────────────────────────────
if ($Rebuild) {
    Write-Host "🔄 Rebuilding Docker images (--no-cache)..." -ForegroundColor Magenta
    $composeFiles = @("docker-compose.dev.yml", "docker-compose.yml")
    foreach ($cf in $composeFiles) {
        $cfPath = Join-Path $ProjectDir $cf
        if (Test-Path $cfPath) {
            docker compose -f $cfPath build --no-cache 2>&1 | Write-Host
            if ($LASTEXITCODE -ne 0) {
                Write-Error "❌ Docker build failed"
                exit 1
            }
            Write-Host "✅ Images rebuilt successfully" -ForegroundColor Green
            break
        }
    }
}

# ─── Start via nestdev docker ─────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  start-docker.ps1 — $($script:PROJECT_NAME)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

try {
    node $NestdevPath docker $script:PROJECT_NAME
} catch {
    Write-Error "❌ nestdev docker failed: $_"
    exit 1
}

# Extract ports from .env.runtime
$envRuntimePath = Join-Path $ProjectDir ".env.runtime"
if (Test-Path $envRuntimePath) {
    $envContent = Get-Content $envRuntimePath -Raw

    $backendPort = if ($envContent -match 'BACKEND_PORT=(\d+)') { $Matches[1] } else { $null }
    $frontendPort = if ($envContent -match 'FRONTEND_PORT=(\d+)') { $Matches[1] } else { $null }

    $port = if ($backendPort) { $backendPort } else { $frontendPort }
    if ($port) {
        Set-Content -Path (Join-Path $RuntimeDir "port.txt") -Value $port -NoNewline
    }

    Write-Host ""
    Write-Host "📁 Runtime files:" -ForegroundColor DarkGray
    Write-Host "   .runtime/port.txt  = $($port ?? 'N/A')" -ForegroundColor DarkGray
    Write-Host ""
}

# Health check loop
Write-Host "⏳ Waiting for health check ($($script:HEALTH_ENDPOINT))..." -ForegroundColor Yellow
$checkPort = if ($backendPort) { $backendPort } elseif ($frontendPort) { $frontendPort } else { $script:BASE_PORT }
$timeout = 30
$elapsed = 0

while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:${checkPort}$($script:HEALTH_ENDPOINT)" `
            -TimeoutSec 3 -ErrorAction SilentlyContinue -SkipHttpErrorCheck
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Health check passed (HTTP $($response.StatusCode))" -ForegroundColor Green
            exit 0
        }
    } catch { <# keep polling #> }
    Start-Sleep -Seconds 2
    $elapsed += 2
}

Write-Host "⚠️  Health check did not return 200 within ${timeout}s" -ForegroundColor DarkYellow
Write-Host "   Service may still be starting. Check: http://localhost:${checkPort}$($script:HEALTH_ENDPOINT)"
exit 0
