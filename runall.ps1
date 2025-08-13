# GlyphMind AI Launcher Script
# Installs dependencies and launches both backend and frontend

Write-Host "🧠 GlyphMind AI - Starting System..." -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.10+ and add it to PATH." -ForegroundColor Red
    exit 1
}

# Display Python version
$pythonVersion = python --version
Write-Host "🐍 Using: $pythonVersion" -ForegroundColor Blue

# Upgrade pip
Write-Host "📦 Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "📦 Installing dependencies from requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
} else {
    Write-Host "⚠️  requirements.txt not found, installing basic dependencies..." -ForegroundColor Yellow
    pip install fastapi uvicorn gradio requests pydantic aiohttp beautifulsoup4 aiosqlite numpy
}

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
$directories = @("cache", "data/raw", "data/processed", "logs")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# Initialize configuration files with defaults if they don't exist
Write-Host "⚙️  Initializing configuration..." -ForegroundColor Yellow

$settingsPath = "config/settings.json"
if (-not (Test-Path $settingsPath)) {
    $defaultSettings = @{
        server = @{
            host = "127.0.0.1"
            port = 8000
            reload = $true
            workers = 1
            log_level = "info"
        }
        ui = @{
            title = "🧠 GlyphMind AI"
            theme = "default"
            share = $false
            server_port = 7860
        }
        database = @{
            knowledge_base_path = "knowledge_base/kb.sqlite"
            ledger_path = "ledger/ledger.sqlite"
            cache_path = "cache/"
        }
        evolution = @{
            background_learning_enabled = $true
            learning_interval_minutes = 30
            max_concurrent_searches = 5
            auto_update_knowledge = $true
        }
    }
    $defaultSettings | ConvertTo-Json -Depth 4 | Out-File -FilePath $settingsPath -Encoding UTF8
    Write-Host "  Created: $settingsPath" -ForegroundColor Gray
}

$apiKeysPath = "config/api_keys.json"
if (-not (Test-Path $apiKeysPath)) {
    $defaultApiKeys = @{
        google_search_api_key = $null
        google_search_engine_id = $null
        youtube_api_key = $null
        openai_api_key = $null
        anthropic_api_key = $null
    }
    $defaultApiKeys | ConvertTo-Json -Depth 2 | Out-File -FilePath $apiKeysPath -Encoding UTF8
    Write-Host "  Created: $apiKeysPath" -ForegroundColor Gray
}

# Display startup information
Write-Host ""
Write-Host "🚀 Starting GlyphMind AI Services..." -ForegroundColor Green
Write-Host "   Backend API: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "   Frontend UI: http://127.0.0.1:7860" -ForegroundColor Cyan
Write-Host "   API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""

# Start backend server
Write-Host "🔧 Starting FastAPI Backend..." -ForegroundColor Yellow
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python server/app.py" -PassThru
Write-Host "   Backend PID: $($backendProcess.Id)" -ForegroundColor Gray

# Wait a moment for backend to start
Write-Host "⏳ Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test backend health
try {
    $healthCheck = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method GET -TimeoutSec 5
    Write-Host "✅ Backend health check passed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Backend health check failed, but continuing..." -ForegroundColor Yellow
}

# Start frontend UI
Write-Host "🎨 Starting Gradio Frontend..." -ForegroundColor Yellow
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python ui/ui.py" -PassThru
Write-Host "   Frontend PID: $($frontendProcess.Id)" -ForegroundColor Gray

Write-Host ""
Write-Host "🎉 GlyphMind AI is now running!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Host "📖 Quick Start Guide:" -ForegroundColor White
Write-Host "   1. Open http://127.0.0.1:7860 in your browser" -ForegroundColor Gray
Write-Host "   2. Start chatting with GlyphMind AI" -ForegroundColor Gray
Write-Host "   3. Explore web search and knowledge base features" -ForegroundColor Gray
Write-Host "   4. Check system status in the Status tab" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 Configuration:" -ForegroundColor White
Write-Host "   - Edit config/api_keys.json to add API keys" -ForegroundColor Gray
Write-Host "   - Edit config/settings.json to modify settings" -ForegroundColor Gray
Write-Host ""
Write-Host "❌ To stop: Close both PowerShell windows or press Ctrl+C" -ForegroundColor Red
Write-Host ""

# Keep the launcher window open
Write-Host "Press any key to exit launcher (services will continue running)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
