<#
.SYNOPSIS
    Cross-platform port management wrapper for AI Real Estate Assistant.

.DESCRIPTION
    Provides port allocation, release, and process killing capabilities.
    Delegates to Python port-manager.py for core logic.

.PARAMETER Action
    Action to perform: allocate, release, status, kill, find

.PARAMETER Category
    Port category: frontend or backend

.PARAMETER Port
    Specific port number (for release/kill actions)

.PARAMETER ServiceName
    Service name for allocation

.PARAMETER PreferredPort
    Preferred port number (will try this first)

.PARAMETER Force
    Force kill processes

.PARAMETER Json
    Output as JSON

.EXAMPLE
    .\port-manager.ps1 -Action allocate -Category backend
    .\port-manager.ps1 -Action allocate -Category frontend -ServiceName "my-app-web"
    .\port-manager.ps1 -Action kill -Port 8000 -Force
    .\port-manager.ps1 -Action status -Json
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("allocate", "release", "status", "kill", "find")]
    [string]$Action,

    [Parameter(Mandatory=$false)]
    [ValidateSet("frontend", "backend")]
    [string]$Category,

    [Parameter(Mandatory=$false)]
    [int]$Port,

    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "",

    [Parameter(Mandatory=$false)]
    [int]$PreferredPort = 0,

    [Parameter(Mandatory=$false)]
    [switch]$Force,

    [Parameter(Mandatory=$false)]
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item "$ScriptDir\..\..").FullName

# Find Python
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} else {
    Write-Error "Python not found. Please install Python 3.8+ and ensure it's on PATH."
    exit 1
}

# Build arguments
$Args = @(
    "$ScriptDir\port-manager.py",
    "--action", $Action,
    "--project-root", $ProjectRoot
)

if ($Category) { $Args += @("--category", $Category) }
if ($Port -gt 0) { $Args += @("--port", $Port) }
if ($Force) { $Args += "--force" }
if ($ServiceName) { $Args += @("--service-name", $ServiceName) }
if ($PreferredPort -gt 0) { $Args += @("--preferred", $PreferredPort) }
if ($Json) { $Args += "--json" }

# Execute
& $PythonCmd @Args
exit $LASTEXITCODE
