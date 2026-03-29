# ┌──────────────────────────────────────────────────────────────────┐
# │ AI-generated changes below this line are forbidden without      │
# │ human review. This file configures the project-specific         │
# │ environment for the unified local-dev script system.            │
# └──────────────────────────────────────────────────────────────────┘

$script:PROJECT_TYPE = "node"
$script:PROJECT_NAME = "ai-real-estate-assistant"
$script:BASE_PORT = 3803
$script:BACKEND_PORT = 8004
$script:START_CMD = 'npm run dev -- --port ${PORT}'
$script:HEALTH_ENDPOINT = "/health"

function Initialize-ProjectEnvironment {
    switch ($script:PROJECT_TYPE) {
        "node" {
            if (-not (Test-Path "node_modules")) {
                Write-Host "📦 Installing Node.js dependencies..." -ForegroundColor Cyan
                npm install
            }
        }
        default {
            Write-Error "❌ Unknown PROJECT_TYPE: $($script:PROJECT_TYPE)"
            exit 1
        }
    }
}
