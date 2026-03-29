# ┌──────────────────────────────────────────────────────────────────┐
# │ AI-generated changes below this line are forbidden without      │
# │ human review. This is the unified local-dev start script.       │
# │ Edit env.ps1 for project-specific configuration.                │
# └──────────────────────────────────────────────────────────────────┘
#Requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$RuntimeDir = Join-Path $ProjectDir ".runtime"

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

# ─── Setup environment ───────────────────────────────────────────
Set-Location $ProjectDir
Initialize-ProjectEnvironment

# ─── Create .runtime directory ───────────────────────────────────
if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
}

# ─── Cleanup function ────────────────────────────────────────────
$script:NestdevProcess = $null

function Invoke-Cleanup {
    Write-Host ""
    Write-Host "🧹 Cleaning up .runtime/..." -ForegroundColor Yellow

    # Stop the nestdev child process
    if ($script:NestdevProcess -and -not $script:NestdevProcess.HasExited) {
        Write-Host "🛑 Stopping nestdev (PID $($script:NestdevProcess.Id))..." -ForegroundColor Red
        try {
            Stop-Process -Id $script:NestdevProcess.Id -Force -ErrorAction SilentlyContinue
            $script:NestdevProcess.WaitForExit(5000) | Out-Null
        } catch { <# ignore #> }
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

# Register Ctrl+C handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Invoke-Cleanup } -ErrorAction SilentlyContinue
try {
    [Console]::TreatControlCAsInput = $false
} catch { <# non-interactive #> }

# ─── Start via nestdev ───────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  start.ps1 — $($script:PROJECT_NAME)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Launch nestdev
$script:NestdevProcess = Start-Process -FilePath "node" -ArgumentList "`"$NestdevPath`" start `"$($script:PROJECT_NAME)`"" `
    -WorkingDirectory $ProjectDir -PassThru -NoNewWindow

# Wait briefly for port allocation
Start-Sleep -Seconds 3

# Extract ports from .env.runtime and write runtime files
$envRuntimePath = Join-Path $ProjectDir ".env.runtime"
if (Test-Path $envRuntimePath) {
    $envContent = Get-Content $envRuntimePath -Raw

    $backendPort = if ($envContent -match 'BACKEND_PORT=(\d+)') { $Matches[1] } else { $null }
    $frontendPort = if ($envContent -match 'FRONTEND_PORT=(\d+)') { $Matches[1] } else { $null }

    # Write single-service port.txt
    $port = if ($backendPort) { $backendPort } else { $frontendPort }
    if ($port) {
        Set-Content -Path (Join-Path $RuntimeDir "port.txt") -Value $port -NoNewline
    }

    # Write multi-service ports.json
    $portsObj = @{}
    if ($frontendPort) { $portsObj.frontend = [int]$frontendPort }
    if ($backendPort) { $portsObj.backend = [int]$backendPort }
    if ($portsObj.Count -gt 0) {
        $portsObj | ConvertTo-Json | Set-Content -Path (Join-Path $RuntimeDir "ports.json")
    }

    # Write PID file
    Set-Content -Path (Join-Path $RuntimeDir "pid.txt") -Value $script:NestdevProcess.Id -NoNewline

    Write-Host ""
    Write-Host "📁 Runtime files:" -ForegroundColor DarkGray
    Write-Host "   .runtime/port.txt  = $($port ?? 'N/A')" -ForegroundColor DarkGray
    Write-Host "   .runtime/pid.txt   = $($script:NestdevProcess.Id)" -ForegroundColor DarkGray
    Write-Host ""
}

# Wait for nestdev to exit
try {
    $script:NestdevProcess.WaitForExit()
} catch {
    <# interrupted #>
} finally {
    Invoke-Cleanup
}
