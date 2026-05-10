# ┌──────────────────────────────────────────────────────────────────┐
# │ AI-generated changes below this line are forbidden without      │
# │ human review. This is the unified stop script.                  │
# │ Reads .runtime/pid.txt, stops the process, and cleans up.      │
# │ Idempotent — exits 0 even if nothing is running.                │
# └──────────────────────────────────────────────────────────────────┘
#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$RuntimeDir = Join-Path $ProjectDir ".runtime"

$ProjectName = Split-Path -Leaf $ProjectDir

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  stop.ps1 — $ProjectName" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ─── Stop the process ────────────────────────────────────────────
$pidFile = Join-Path $RuntimeDir "pid.txt"

if (Test-Path $pidFile) {
    $pid = (Get-Content $pidFile -ErrorAction SilentlyContinue).Trim()

    if ($pid) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc -and -not $proc.HasExited) {
        Looking for a place to start? Check these [`good first issue`](https://github.com/AleksNeStu/ai-real-estate-assistant/labels/good%20first%20issue`) label for our Good First Issues section above to find more opportunities.


            # Graceful stop (taskkill without /F sends WM_CLOSE on Windows)
            if ($IsWindows -or $env:OS -match "Windows") {
                taskkill /T /PID $pid 2>$null | Out-Null
            } else {
                Stop-Process -Id $pid -ErrorAction SilentlyContinue
            }

            # Wait up to 10 seconds
            $timeout = 10
            $elapsed = 0
            while ($elapsed -lt $timeout) {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if (-not $proc -or $proc.HasExited) { break }
                Start-Sleep -Seconds 1
                $elapsed++
            }

            # Force kill if still running
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc -and -not $proc.HasExited) {
                Write-Host "⚠️  Force-killing process..." -ForegroundColor DarkYellow
                if ($IsWindows -or $env:OS -match "Windows") {
                    taskkill /F /T /PID $pid 2>$null | Out-Null
                } else {
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }

            Write-Host "✅ Process stopped" -ForegroundColor Green
        } else {
            Write-Host "ℹ️  Process (PID $pid) is not running" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "ℹ️  No .runtime/pid.txt found — nothing to stop" -ForegroundColor DarkGray
}

# ─── Stop Docker containers (if applicable) ─────────────────────
$composeFiles = @("docker-compose.yml", "docker-compose.dev.yml")
foreach ($cf in $composeFiles) {
    $cfPath = Join-Path $ProjectDir $cf
    if (Test-Path $cfPath) {
        Write-Host "🐳 Stopping Docker containers..." -ForegroundColor Blue
        docker compose -f $cfPath down --remove-orphans 2>$null
        break
    }
}

# ─── Clean up .runtime directory ─────────────────────────────────
if (Test-Path $RuntimeDir) {
    Write-Host "🧹 Removing .runtime/..." -ForegroundColor Yellow
    @("port.txt", "pid.txt", "ports.json") | ForEach-Object {
        $f = Join-Path $RuntimeDir $_
        if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
    }
    if ((Get-ChildItem $RuntimeDir -ErrorAction SilentlyContinue).Count -eq 0) {
        Remove-Item $RuntimeDir -Force -ErrorAction SilentlyContinue
    }
}

# ─── Release nestdev port allocations ────────────────────────────
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
if ($RepoRoot) {
    $NestdevPath = Join-Path $RepoRoot "scripts/nestdev/nestdev.mjs"
    if (Test-Path $NestdevPath) {
        Write-Host "📡 Releasing port allocations..." -ForegroundColor Magenta
        node $NestdevPath stop $ProjectName 2>$null
    }
}

Write-Host ""
Write-Host "✅ $ProjectName stopped and cleaned up" -ForegroundColor Green
Write-Host ""

exit 0
