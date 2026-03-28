# Quickstart verification script — checks that the Docker stack is healthy.
# Usage: .\scripts\docker\quickstart-verify.ps1

$BackendUrl = if ($env:BACKEND_URL) { $env:BACKEND_URL } else { "http://localhost:8082" }
$FrontendUrl = if ($env:FRONTEND_URL) { $env:FRONTEND_URL } else { "http://localhost:3082" }
$ApiKey = if ($env:API_ACCESS_KEY) { $env:API_ACCESS_KEY } else { "dev-secret-key" }

$pass = 0
$fail = 0

function Check-Url {
    param([string]$Label, [string]$Url, [int]$Expected = 200, [string]$HeaderName = "", [string]$HeaderValue = "")
    try {
        $headers = @{}
        if ($HeaderName -and $HeaderValue) {
            $headers[$HeaderName] = $HeaderValue
        }
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -Headers $headers -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) {
            Write-Host "  $Label`: PASS ($($resp.StatusCode))" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "  $Label`: FAIL (got $($resp.StatusCode), expected $Expected)" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "  $Label`: FAIL ($($_.Exception.Message))" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "Verifying AI Real Estate Assistant stack..." -ForegroundColor Cyan
Write-Host ""

Check-Url -Label "Backend health" -Url "$BackendUrl/health"
Check-Url -Label "Frontend" -Url "$FrontendUrl/"
Check-Url -Label "API auth" -Url "$BackendUrl/api/v1/verify-auth" -HeaderName "X-API-Key" -HeaderValue $ApiKey

Write-Host ""
if ($fail -eq 0) {
    Write-Host "All checks passed. Open $FrontendUrl to start chatting." -ForegroundColor Green
    exit 0
} else {
    Write-Host "$fail check(s) failed. See logs: docker compose -f deploy/compose/docker-compose.yml logs" -ForegroundColor Red
    exit 1
}
