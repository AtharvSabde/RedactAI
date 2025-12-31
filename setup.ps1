# RedactAI Automated Installation Script for Windows PowerShell
# Version 2.0 - Enhanced with better error handling and progress tracking

$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'  # Speeds up Invoke-WebRequest

# Color functions
function Write-Success { param($msg) Write-Host "[SUCCESS] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "[WARNING] $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n==> $msg" -ForegroundColor Magenta }

# Banner
Clear-Host
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     RedactAI Setup Wizard v2.0" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Step "Step 1/8: Checking Python installation"
try {
    $pythonCmd = Get-Command python -ErrorAction Stop
    $pythonVersion = python --version 2>&1
    Write-Success "Found $pythonVersion at: $($pythonCmd.Source)"
    
    # Check Python version
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 8 -and $minor -le 12) {
            Write-Success "Python version is compatible (3.8-3.12)"
        } elseif ($major -eq 3 -and $minor -gt 12) {
            Write-Warn "Python 3.$minor detected. Recommended: 3.8-3.12, but will try anyway"
        } else {
            Write-Fail "Python version must be 3.8-3.12"
            Read-Host "`nPress Enter to exit"
            exit 1
        }
    }
} catch {
    Write-Fail "Python is not installed or not in PATH"
    Write-Info "Download Python 3.8-3.12 from: https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Step 2: Check Git
Write-Step "Step 2/8: Checking Git installation"
try {
    $gitCmd = Get-Command git -ErrorAction Stop
    $gitVersion = git --version 2>&1
    Write-Success "Found $gitVersion at: $($gitCmd.Source)"
} catch {
    Write-Fail "Git is not installed or not in PATH"
    Write-Info "Download Git from: https://git-scm.com/download/win"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Step 3: Clone or Update Repository
Write-Step "Step 3/8: Setting up RedactAI repository"
$repoUrl = "https://github.com/AtharvSabde/RedactAI.git"
$repoDir = "RedactAI"

if (Test-Path $repoDir) {
    Write-Warn "RedactAI directory already exists"
    $response = Read-Host "Update existing installation? (y/n)"
    if ($response -eq 'y') {
        Write-Info "Updating repository..."
        Push-Location $repoDir
        try {
            git pull origin main 2>&1 | Out-Null
            Write-Success "Repository updated"
        } catch {
            Write-Warn "Could not update repository: $_"
        }
        Pop-Location
    }
} else {
    Write-Info "Cloning repository from GitHub..."
    try {
        git clone $repoUrl 2>&1 | ForEach-Object { 
            if ($_ -match "Receiving objects:|Resolving deltas:") { 
                Write-Host "." -NoNewline -ForegroundColor Gray 
            } 
        }
        Write-Host ""
        Write-Success "Repository cloned successfully"
    } catch {
        Write-Fail "Failed to clone repository: $_"
        Read-Host "`nPress Enter to exit"
        exit 1
    }
}

# Change to repo directory
try {
    Set-Location $repoDir
    Write-Info "Working directory: $(Get-Location)"
} catch {
    Write-Fail "Could not enter RedactAI directory"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Step 4: Create Virtual Environment
Write-Step "Step 4/8: Creating virtual environment"
if (Test-Path "venv") {
    Write-Warn "Virtual environment already exists, using existing"
} else {
    Write-Info "Creating Python virtual environment..."
    try {
        python -m venv venv
        Write-Success "Virtual environment created"
    } catch {
        Write-Fail "Failed to create virtual environment: $_"
        Read-Host "`nPress Enter to exit"
        exit 1
    }
}

# Step 5: Activate Virtual Environment
Write-Step "Step 5/8: Activating virtual environment"
$venvActivate = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    try {
        & $venvActivate
        Write-Success "Virtual environment activated"
        Write-Info "Python location: $(Get-Command python | Select-Object -ExpandProperty Source)"
    } catch {
        Write-Fail "Failed to activate virtual environment: $_"
        Read-Host "`nPress Enter to exit"
        exit 1
    }
} else {
    Write-Fail "Virtual environment activation script not found"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Step 6: Install Dependencies
Write-Step "Step 6/8: Installing Python dependencies"
Write-Info "This may take 1-2 minutes..."
try {
    python -m pip install --upgrade pip --quiet 2>&1 | Out-Null
    Write-Success "Pip upgraded"
    
    pip install -r requirements.txt --quiet 2>&1 | Out-Null
    Write-Success "Dependencies installed successfully"
    
    # Verify key packages
    $packages = @("fastmcp", "fitz", "pymupdf")
    foreach ($pkg in $packages) {
        $installed = pip list 2>&1 | Select-String $pkg
        if ($installed) {
            Write-Success "  ✓ $pkg installed"
        }
    }
} catch {
    Write-Fail "Failed to install dependencies: $_"
    Write-Info "Try running manually: pip install -r requirements.txt"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Step 7: Check and Configure Ollama
Write-Step "Step 7/8: Checking Ollama setup"
try {
    $ollamaCmd = Get-Command ollama -ErrorAction Stop
    $ollamaVersion = ollama --version 2>&1
    Write-Success "Found Ollama: $ollamaVersion"
    
    # Test if Ollama is running
    Write-Info "Testing Ollama connection..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Success "Ollama is running"
        
        # Check for models
        Write-Info "Checking installed models..."
        $models = ollama list 2>&1
        
        if ($models -match "gemma3:4b") {
            Write-Success "Model gemma3:4b already installed"
        } else {
            Write-Info "Recommended model gemma3:4b not found"
            $response = Read-Host "Pull gemma3:4b now? This will download ~2-3GB (y/n)"
            if ($response -eq 'y') {
                Write-Info "Pulling gemma3:4b... This may take 5-10 minutes depending on your internet speed"
                try {
                    ollama pull gemma3:4b
                    Write-Success "Model gemma3:4b installed successfully"
                } catch {
                    Write-Warn "Could not pull model: $_"
                    Write-Info "You can install it later with: ollama pull gemma3:4b"
                }
            } else {
                Write-Info "Skipped model download. Install later with: ollama pull gemma3:4b"
            }
        }
    } catch {
        Write-Warn "Ollama is installed but not running"
        Write-Info "Please start Ollama:"
        Write-Info "  - Check system tray for Ollama icon"
        Write-Info "  - Or run: ollama serve"
        Write-Info "Then restart this installation"
    }
} catch {
    Write-Warn "Ollama is not installed"
    Write-Info "Ollama is required to run RedactAI"
    Write-Info "Download from: https://ollama.ai"
    $response = Read-Host "`nContinue without Ollama? You'll need to install it later (y/n)"
    if ($response -ne 'y') {
        exit 1
    }
}

# Step 8: Configure Claude Desktop
Write-Step "Step 8/8: Configuring Claude Desktop"

$currentDir = Get-Location
$pythonPath = Join-Path $currentDir "venv\Scripts\python.exe"
$serverPath = Join-Path $currentDir "src\server.py"

# Verify files exist
if (-not (Test-Path $pythonPath)) {
    Write-Fail "Python executable not found at: $pythonPath"
    Read-Host "`nPress Enter to exit"
    exit 1
}

if (-not (Test-Path $serverPath)) {
    Write-Fail "Server file not found at: $serverPath"
    Read-Host "`nPress Enter to exit"
    exit 1
}

# Convert to forward slashes for JSON
$pythonPathJson = $pythonPath -replace '\\', '/'
$serverPathJson = $serverPath -replace '\\', '/'

Write-Info "Configuration paths:"
Write-Host "  Python: $pythonPathJson" -ForegroundColor Gray
Write-Host "  Server: $serverPathJson" -ForegroundColor Gray

$configDir = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

# Create config directory
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Info "Created Claude config directory"
}

# Backup existing config
if (Test-Path $configFile) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$configFile.backup.$timestamp"
    Copy-Item $configFile $backupFile
    Write-Success "Backed up existing config to: $backupFile"
}

# Create or update config
try {
    if (Test-Path $configFile) {
        Write-Info "Updating existing Claude Desktop configuration..."
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        
        # Check if pdf-redactor already exists
        if ($config.mcpServers.PSObject.Properties.Name -contains "pdf-redactor") {
            Write-Warn "pdf-redactor already exists in configuration"
            $response = Read-Host "Overwrite existing configuration? (y/n)"
            if ($response -eq 'y') {
                $config.mcpServers.'pdf-redactor' = @{
                    command = $pythonPathJson
                    args = @($serverPathJson)
                }
                Write-Success "Configuration updated"
            } else {
                Write-Info "Skipped configuration update"
            }
        } else {
            # Add new server
            if (-not $config.mcpServers) {
                $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
            }
            
            $config.mcpServers | Add-Member -MemberType NoteProperty -Name "pdf-redactor" -Value @{
                command = $pythonPathJson
                args = @($serverPathJson)
            }
            Write-Success "Added pdf-redactor to configuration"
        }
        
        $config | ConvertTo-Json -Depth 10 | Set-Content $configFile -Encoding UTF8
        Write-Success "Claude Desktop configured successfully"
        
    } else {
        Write-Info "Creating new Claude Desktop configuration..."
        $config = @{
            mcpServers = @{
                "pdf-redactor" = @{
                    command = $pythonPathJson
                    args = @($serverPathJson)
                }
            }
        }
        
        $config | ConvertTo-Json -Depth 10 | Set-Content $configFile -Encoding UTF8
        Write-Success "Claude Desktop configuration created"
    }
} catch {
    Write-Fail "Failed to configure Claude Desktop: $_"
    Write-Info "Manual configuration required. Add this to: $configFile"
    Write-Host @"
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "$pythonPathJson",
      "args": ["$serverPathJson"]
    }
  }
}
"@ -ForegroundColor Yellow
}

# Final Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "     Installation Complete! 🎉" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Success "RedactAI has been successfully installed!"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart Claude Desktop application" -ForegroundColor White
Write-Host "  2. In Claude, type: 'List available Ollama models'" -ForegroundColor White
Write-Host "  3. If you see models, you're ready to go!" -ForegroundColor White
Write-Host ""
Write-Host "Installation Location:" -ForegroundColor Cyan
Write-Host "  $currentDir" -ForegroundColor Gray
Write-Host ""
Write-Host "Configuration File:" -ForegroundColor Cyan
Write-Host "  $configFile" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  README: https://github.com/AtharvSabde/RedactAI" -ForegroundColor Gray
Write-Host "  Setup Guide: $currentDir\INSTALLATION.md" -ForegroundColor Gray
Write-Host ""
Write-Host "Troubleshooting:" -ForegroundColor Cyan
Write-Host "  Run: python scripts\configure_claude.py" -ForegroundColor Gray
Write-Host "  Or visit: https://github.com/AtharvSabde/RedactAI/issues" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"