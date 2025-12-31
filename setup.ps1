# RedactAI Automated Installation Script
# For Windows PowerShell

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   RedactAI Automated Installation" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Helper functions
function Print-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Print-Info {
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor Blue
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Check Python installation
Print-Info "Checking Python installation..."
try {
    $pythonVersion = python --version 2>&1
    Print-Success "Found $pythonVersion"
} catch {
    Print-Error "Python is not installed or not in PATH"
    Print-Info "Please install Python 3.8-3.12 from https://www.python.org"
    exit 1
}

# Check if git is installed
Print-Info "Checking Git installation..."
try {
    $gitVersion = git --version 2>&1
    Print-Success "Found Git"
} catch {
    Print-Error "Git is not installed"
    Print-Info "Please install Git from https://git-scm.com/download/win"
    exit 1
}

# Clone repository
Print-Info "Cloning RedactAI repository..."
if (Test-Path "RedactAI") {
    Print-Warning "RedactAI directory already exists. Using existing directory."
    Set-Location RedactAI
    git pull origin main 2>&1 | Out-Null
} else {
    git clone https://github.com/AtharvSabde/RedactAI.git 2>&1 | Out-Null
    Set-Location RedactAI
    Print-Success "Repository cloned successfully"
}

# Create virtual environment
Print-Info "Creating virtual environment..."
python -m venv venv
Print-Success "Virtual environment created"

# Activate virtual environment
Print-Info "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1
Print-Success "Virtual environment activated"

# Upgrade pip
Print-Info "Upgrading pip..."
python -m pip install --upgrade pip --quiet
Print-Success "Pip upgraded"

# Install dependencies
Print-Info "Installing dependencies..."
pip install -r requirements.txt --quiet
Print-Success "Dependencies installed"

# Check Ollama installation
Print-Info "Checking Ollama installation..."
try {
    $ollamaVersion = ollama --version 2>&1
    Print-Success "Ollama is installed"
    
    # Check if Ollama is running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
        Print-Success "Ollama is running"
    } catch {
        Print-Warning "Ollama is not running"
        Print-Info "Please start Ollama (it should start automatically on Windows)"
        Print-Info "Check your system tray for the Ollama icon"
    }
} catch {
    Print-Error "Ollama is not installed"
    Print-Info "Please install Ollama from: https://ollama.ai"
    Print-Info "After installation, Ollama will start automatically"
    exit 1
}

# Pull recommended model
Print-Info "Checking for Ollama models..."
$models = ollama list 2>&1
if ($models -match "gemma3:4b") {
    Print-Success "Model gemma3:4b already installed"
} else {
    Print-Info "Pulling recommended model (gemma3:4b). This may take a few minutes..."
    try {
        ollama pull gemma3:4b
        Print-Success "Model gemma3:4b installed successfully"
    } catch {
        Print-Warning "Could not pull model. You can install it later with: ollama pull gemma3:4b"
    }
}

# Get paths
$currentDir = Get-Location
$pythonPath = Join-Path $currentDir "venv\Scripts\python.exe"
$serverPath = Join-Path $currentDir "src\server.py"

# Convert backslashes to forward slashes for JSON
$pythonPathJson = $pythonPath -replace '\\', '/'
$serverPathJson = $serverPath -replace '\\', '/'

Print-Success "Installation paths determined:"
Write-Host "  Python: $pythonPathJson"
Write-Host "  Server: $serverPathJson"

# Configure Claude Desktop
Print-Info "Configuring Claude Desktop..."

$configDir = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

# Create config directory if it doesn't exist
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Backup existing config if it exists
if (Test-Path $configFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$configFile.backup.$timestamp"
    Copy-Item $configFile $backupFile
    Print-Success "Backed up existing config to: $backupFile"
}

# Create or update config
if (Test-Path $configFile) {
    # Config exists, add our server
    Print-Info "Updating existing Claude Desktop configuration..."
    
    try {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        
        # Check if pdf-redactor already exists
        if ($config.mcpServers.PSObject.Properties.Name -contains "pdf-redactor") {
            Print-Warning "pdf-redactor entry already exists in config. Skipping update."
            Print-Warning "To reconfigure, please edit manually: $configFile"
        } else {
            # Add our server
            if (-not $config.mcpServers) {
                $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
            }
            
            $config.mcpServers | Add-Member -MemberType NoteProperty -Name "pdf-redactor" -Value @{
                command = $pythonPathJson
                args = @($serverPathJson)
            }
            
            $config | ConvertTo-Json -Depth 10 | Set-Content $configFile
            Print-Success "Claude Desktop configuration updated"
        }
    } catch {
        Print-Error "Could not update configuration automatically"
        Print-Info "Please update manually: $configFile"
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
} else {
    # Create new config
    Print-Info "Creating new Claude Desktop configuration..."
    
    $config = @{
        mcpServers = @{
            "pdf-redactor" = @{
                command = $pythonPathJson
                args = @($serverPathJson)
            }
        }
    }
    
    $config | ConvertTo-Json -Depth 10 | Set-Content $configFile
    Print-Success "Claude Desktop configuration created"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Installation Complete! 🎉" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Print-Success "RedactAI has been successfully installed and configured!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart Claude Desktop application"
Write-Host "  2. In Claude, type: 'List available Ollama models'"
Write-Host "  3. If you see models listed, installation is successful!"
Write-Host ""
Write-Host "Configuration file location:"
Write-Host "  $configFile"
Write-Host ""
Print-Info "For troubleshooting, see: https://github.com/AtharvSabde/RedactAI"
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")