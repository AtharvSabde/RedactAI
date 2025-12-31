# RedactAI Automated Installation Script for Windows PowerShell

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   RedactAI Automated Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Blue
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8-3.12 from https://www.python.org" -ForegroundColor Blue
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if git is installed
Write-Host "Checking Git installation..." -ForegroundColor Blue
try {
    $gitVersion = git --version 2>&1
    Write-Host "Found Git" -ForegroundColor Green
} catch {
    Write-Host "Git is not installed" -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/download/win" -ForegroundColor Blue
    Read-Host "Press Enter to exit"
    exit 1
}

# Clone repository
Write-Host "Cloning RedactAI repository..." -ForegroundColor Blue
if (Test-Path "RedactAI") {
    Write-Host "RedactAI directory already exists. Using existing directory." -ForegroundColor Yellow
    Set-Location RedactAI
    git pull origin main 2>&1 | Out-Null
} else {
    git clone https://github.com/AtharvSabde/RedactAI.git 2>&1 | Out-Null
    Set-Location RedactAI
    Write-Host "Repository cloned successfully" -ForegroundColor Green
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Blue
python -m venv venv
Write-Host "Virtual environment created" -ForegroundColor Green

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Blue
& .\venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated" -ForegroundColor Green

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Blue
python -m pip install --upgrade pip --quiet
Write-Host "Pip upgraded" -ForegroundColor Green

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Blue
pip install -r requirements.txt --quiet
Write-Host "Dependencies installed" -ForegroundColor Green

# Check Ollama installation
Write-Host "Checking Ollama installation..." -ForegroundColor Blue
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "Ollama is installed" -ForegroundColor Green
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
        Write-Host "Ollama is running" -ForegroundColor Green
    } catch {
        Write-Host "Ollama is not running" -ForegroundColor Yellow
        Write-Host "Please start Ollama from your system tray" -ForegroundColor Blue
    }
} catch {
    Write-Host "Ollama is not installed" -ForegroundColor Red
    Write-Host "Please install Ollama from: https://ollama.ai" -ForegroundColor Blue
    Read-Host "Press Enter to exit"
    exit 1
}

# Pull recommended model
Write-Host "Checking for Ollama models..." -ForegroundColor Blue
$models = ollama list 2>&1
if ($models -match "gemma3:4b") {
    Write-Host "Model gemma3:4b already installed" -ForegroundColor Green
} else {
    Write-Host "Pulling recommended model (gemma3:4b). This may take a few minutes..." -ForegroundColor Blue
    try {
        ollama pull gemma3:4b
        Write-Host "Model gemma3:4b installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "Could not pull model. You can install it later with: ollama pull gemma3:4b" -ForegroundColor Yellow
    }
}

# Get paths
$currentDir = Get-Location
$pythonPath = Join-Path $currentDir "venv\Scripts\python.exe"
$serverPath = Join-Path $currentDir "src\server.py"

# Convert to forward slashes
$pythonPathJson = $pythonPath -replace '\\', '/'
$serverPathJson = $serverPath -replace '\\', '/'

Write-Host "Installation paths determined:" -ForegroundColor Green
Write-Host "  Python: $pythonPathJson"
Write-Host "  Server: $serverPathJson"

# Configure Claude Desktop
Write-Host "Configuring Claude Desktop..." -ForegroundColor Blue

$configDir = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

# Create config directory
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Backup existing config
if (Test-Path $configFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$configFile.backup.$timestamp"
    Copy-Item $configFile $backupFile
    Write-Host "Backed up existing config" -ForegroundColor Green
}

# Create or update config
if (Test-Path $configFile) {
    Write-Host "Updating existing Claude Desktop configuration..." -ForegroundColor Blue
    
    try {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        
        if ($config.mcpServers.PSObject.Properties.Name -contains "pdf-redactor") {
            Write-Host "pdf-redactor already exists in config" -ForegroundColor Yellow
        } else {
            if (-not $config.mcpServers) {
                $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
            }
            
            $config.mcpServers | Add-Member -MemberType NoteProperty -Name "pdf-redactor" -Value @{
                command = $pythonPathJson
                args = @($serverPathJson)
            }
            
            $config | ConvertTo-Json -Depth 10 | Set-Content $configFile
            Write-Host "Claude Desktop configuration updated" -ForegroundColor Green
        }
    } catch {
        Write-Host "Could not update configuration automatically" -ForegroundColor Red
        Write-Host "Please update manually: $configFile" -ForegroundColor Blue
    }
} else {
    Write-Host "Creating new Claude Desktop configuration..." -ForegroundColor Blue
    
    $config = @{
        mcpServers = @{
            "pdf-redactor" = @{
                command = $pythonPathJson
                args = @($serverPathJson)
            }
        }
    }
    
    $config | ConvertTo-Json -Depth 10 | Set-Content $configFile
    Write-Host "Claude Desktop configuration created" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "RedactAI has been successfully installed!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Desktop application"
Write-Host "  2. In Claude, type: List available Ollama models"
Write-Host "  3. If you see models listed, installation is successful!"
Write-Host ""
Write-Host "Configuration file: $configFile"
Write-Host ""
Write-Host "For troubleshooting: https://github.com/AtharvSabde/RedactAI" -ForegroundColor Blue
Write-Host ""
Read-Host "Press Enter to exit"