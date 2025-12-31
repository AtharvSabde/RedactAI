# RedactAI Setup Script for Windows
# Simple and reliable version

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host "  RedactAI Installation Wizard"
Write-Host "========================================"
Write-Host ""

# Check Python
Write-Host "[1/8] Checking Python..." -ForegroundColor Cyan
try {
    $pyVer = python --version
    Write-Host "Found: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    Write-Host "Install from: https://www.python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Git
Write-Host "[2/8] Checking Git..." -ForegroundColor Cyan
try {
    $gitVer = git --version
    Write-Host "Found: $gitVer" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git not found" -ForegroundColor Red
    Write-Host "Install from: https://git-scm.com"
    Read-Host "Press Enter to exit"
    exit 1
}

# Clone repo
Write-Host "[3/8] Cloning repository..." -ForegroundColor Cyan
if (Test-Path "RedactAI") {
    Write-Host "Directory exists, updating..." -ForegroundColor Yellow
    Set-Location RedactAI
    git pull origin main
} else {
    git clone https://github.com/AtharvSabde/RedactAI.git
    Set-Location RedactAI
    Write-Host "Cloned successfully" -ForegroundColor Green
}

# Create venv
Write-Host "[4/8] Creating virtual environment..." -ForegroundColor Cyan
if (Test-Path "venv") {
    Write-Host "Already exists" -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "Created" -ForegroundColor Green
}

# Activate venv
Write-Host "[5/8] Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1
Write-Host "Activated" -ForegroundColor Green

# Install deps
Write-Host "[6/8] Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "Installed" -ForegroundColor Green

# Check Ollama
Write-Host "[7/8] Checking Ollama..." -ForegroundColor Cyan
try {
    $ollamaVer = ollama --version
    Write-Host "Found: $ollamaVer" -ForegroundColor Green
    
    Write-Host "Checking models..." -ForegroundColor Cyan
    $models = ollama list
    if ($models -match "gemma3:4b") {
        Write-Host "gemma3:4b already installed" -ForegroundColor Green
    } else {
        Write-Host "Install gemma3:4b? (y/n): " -NoNewline
        $resp = Read-Host
        if ($resp -eq "y") {
            ollama pull gemma3:4b
            Write-Host "Model installed" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "Ollama not found - install from https://ollama.ai" -ForegroundColor Yellow
}

# Configure Claude
Write-Host "[8/8] Configuring Claude Desktop..." -ForegroundColor Cyan

$currentDir = Get-Location
$pythonPath = Join-Path $currentDir "venv\Scripts\python.exe"
$serverPath = Join-Path $currentDir "src\server.py"
$pythonJson = $pythonPath -replace '\\', '/'
$serverJson = $serverPath -replace '\\', '/'

$configDir = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

if (Test-Path $configFile) {
    $backup = "$configFile.backup." + (Get-Date -Format "yyyyMMdd_HHmmss")
    Copy-Item $configFile $backup
    Write-Host "Backed up config" -ForegroundColor Green
}

try {
    if (Test-Path $configFile) {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        if (-not $config.mcpServers) {
            $config | Add-Member -Name "mcpServers" -Value @{} -MemberType NoteProperty
        }
        if ($config.mcpServers.PSObject.Properties.Name -contains "pdf-redactor") {
            Write-Host "pdf-redactor exists, overwriting..." -ForegroundColor Yellow
        }
        $config.mcpServers | Add-Member -Name "pdf-redactor" -Value @{
            command = $pythonJson
            args = @($serverJson)
        } -MemberType NoteProperty -Force
    } else {
        $config = @{
            mcpServers = @{
                "pdf-redactor" = @{
                    command = $pythonJson
                    args = @($serverJson)
                }
            }
        }
    }
    $config | ConvertTo-Json -Depth 10 | Set-Content $configFile
    Write-Host "Configured successfully" -ForegroundColor Green
} catch {
    Write-Host "Config failed: $_" -ForegroundColor Red
}

# Done
Write-Host ""
Write-Host "========================================"
Write-Host "  Installation Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "1. Restart Claude Desktop"
Write-Host "2. Type: List available Ollama models"
Write-Host "3. Start redacting!"
Write-Host ""
Write-Host "Location: $currentDir"
Write-Host "Config: $configFile"
Write-Host ""
Read-Host "Press Enter to exit"