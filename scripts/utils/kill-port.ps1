<#
.SYNOPSIS
    Kill processes on specified ports and release port allocations.

.DESCRIPTION
    This script kills processes listening on the specified ports and
    optionally releases the port allocations from the port registry.

.PARAMETER Ports
    Comma-separated list of ports to kill processes on.

.PARAMETER Release
    Release port allocations from registry after killing processes.

.PARAMETER Force
    Force kill processes (SIGKILL instead of SIGTERM).

.PARAMETER All
    Kill all services managed by this project.

.EXAMPLE
    .\kill-port.ps1 -Ports 8000,3800
    .\kill-port.ps1 -Ports 8000 -Release
    .\kill-port.ps1 -All -Force
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Ports = "",

    [Parameter(Mandatory=$false)]
    [switch]$Release,

    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$All
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..").FullName

function Find-Pid-On-Port {
    param([int]$Port)

    $pids = @()
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $pids += $conn.OwningProcess
        }
    } catch {
        # Fallback to netstat
        $result = netstat -ano | Select-String ":$Port\s" | Select-String "LISTENING"
        foreach ($line in $result) {
            $parts = $line -split '\s+'
            $pid = $parts[-1]
            if ($pid -match '^\d+$') {
                $pids += [int]$pid
            }
        }
    }
    return $pids | Select-Object -Unique
}

function Stop-Process-Tree {
    param([int]$Pid, [switch]$Force)

    try {
        $proc = Get-Process -Id $Pid -ErrorAction SilentlyContinue
        if (-not $proc) { return }

        # Get child processes
        $children = Get-CimInstance -ClassName Win32_Process |
            Where-Object { $_.ParentProcessId -eq $Pid }

        # Kill children first
        foreach ($child in $children) {
            Stop-Process-Tree -Pid $child.ProcessId -Force:$Force
        }

        # Kill the process
        if ($Force) {
            Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
            taskkill /F /PID $Pid 2>$null | Out-Null
        } else {
            Stop-Process -Id $Pid -ErrorAction SilentlyContinue
            taskkill /PID $Pid 2>$null | Out-Null
        }

        Write-Host "  Killed process $Pid" -ForegroundColor Gray
    } catch {
        # Process may have already exited
    }
}

function Release-Port-Allocation {
    param([int]$Port)

    $registryPath = Join-Path $ProjectRoot "docs\PORT_REGISTRY.json"
    if (-not (Test-Path $registryPath)) { return }

    try {
        $registry = Get-Content $registryPath | ConvertFrom-Json
        $updated = $false

        foreach ($alloc in $registry.allocations) {
            if ($alloc.port -eq $Port -and $alloc.status -eq "active") {
                $alloc.status = "inactive"
                $alloc.lastUsedAt = (Get-Date).ToUniversalTime().ToString("o")
                $updated = $true
            }
        }

        if ($updated) {
            $registry.lastUpdated = (Get-Date).ToUniversalTime().ToString("o")
            $registry | ConvertTo-Json -Depth 10 | Set-Content $registryPath
            Write-Host "  Released port allocation for $Port" -ForegroundColor Green
        }
    } catch {
        Write-Warning "Failed to update port registry"
    }
}

# Main logic
if ($All) {
    # Get all active ports from registry
    $registryPath = Join-Path $ProjectRoot "docs\PORT_REGISTRY.json"
    if (Test-Path $registryPath) {
        $registry = Get-Content $registryPath | ConvertFrom-Json
        $portList = @()
        foreach ($alloc in $registry.allocations) {
            if ($alloc.status -eq "active") {
                $portList += $alloc.port
            }
        }
        $Ports = $portList -join ","
    } else {
        Write-Error "Port registry not found at $registryPath"
        exit 1
    }
}

if (-not $Ports) {
    Write-Error "No ports specified. Use -Ports 8000,3800 or -All"
    exit 1
}

$portArray = $Ports -split "," | Where-Object { $_ -match '^\d+$' }

foreach ($portStr in $portArray) {
    $port = [int]$portStr
    Write-Host "Processing port $port..." -ForegroundColor Cyan

    $pids = Find-Pid-On-Port -Port $port

    if ($pids.Count -eq 0) {
        Write-Host "  No process found on port $port" -ForegroundColor Yellow
    } else {
        Write-Host "  Found $($pids.Count) process(es) on port $port"
        foreach ($pid in $pids) {
            Stop-Process-Tree -Pid $pid -Force:$Force
        }
    }

    if ($Release) {
        Release-Port-Allocation -Port $port
    }
}

Write-Host "`nDone!" -ForegroundColor Green
