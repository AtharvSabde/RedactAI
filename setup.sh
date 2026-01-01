#!/bin/bash

# RedactAI Automated Installation Script
# For macOS and Linux

set -e  # Exit on error

echo "=========================================="
echo "   RedactAI Automated Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
print_info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Found Python $PYTHON_VERSION"
else
    print_error "Python 3 is not installed. Please install Python 3.8-3.12"
    exit 1
fi

# Clone repository
print_info "Cloning RedactAI repository..."
if [ -d "RedactAI" ]; then
    print_warning "RedactAI directory already exists. Using existing directory."
    cd RedactAI
    git pull origin main || print_warning "Could not update repository"
else
    git clone https://github.com/AtharvSabde/RedactAI.git
    cd RedactAI
    print_success "Repository cloned successfully"
fi

# Create virtual environment
print_info "Creating virtual environment..."
python3 -m venv venv
print_success "Virtual environment created"

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip --quiet
print_success "Pip upgraded"

# Install dependencies
print_info "Installing dependencies..."
pip install -r requirements.txt --quiet
print_success "Dependencies installed"

# Check Ollama installation
print_info "Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    print_success "Ollama is installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        print_success "Ollama is running"
    else
        print_warning "Ollama is not running. Starting Ollama..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open -a Ollama || print_warning "Could not start Ollama automatically. Please start it manually."
        else
            nohup ollama serve > /dev/null 2>&1 &
            sleep 2
            if curl -s http://localhost:11434/api/tags &> /dev/null; then
                print_success "Ollama started successfully"
            else
                print_warning "Could not start Ollama. Please run 'ollama serve' manually."
            fi
        fi
    fi
else
    print_error "Ollama is not installed."
    print_info "Please install Ollama from: https://ollama.ai"
    print_info "After installing Ollama, run: ollama serve"
    exit 1
fi

# Pull recommended model
print_info "Checking for Ollama models..."
if ollama list | grep -q "gemma3:4b"; then
    print_success "Model gemma3:4b already installed"
else
    print_info "Pulling recommended model (gemma3:4b). This may take a few minutes..."
    if ollama pull gemma3:4b; then
        print_success "Model gemma3:4b installed successfully"
    else
        print_warning "Could not pull model. You can install it later with: ollama pull gemma3:4b"
    fi
fi

# Get paths
PYTHON_PATH=$(pwd)/venv/bin/python
SERVER_PATH=$(pwd)/src/server.py

print_success "Installation paths determined:"
echo "  Python: $PYTHON_PATH"
echo "  Server: $SERVER_PATH"

# Configure Claude Desktop
print_info "Configuring Claude Desktop..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
else
    # Linux
    CONFIG_DIR="$HOME/.config/Claude"
fi

CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Backup existing config if it exists
if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    print_success "Backed up existing config to: $BACKUP_FILE"
fi

# Create or update config
if [ -f "$CONFIG_FILE" ]; then
    # Config exists, update it properly
    print_info "Updating existing Claude Desktop configuration..."
    
    # Use Python to safely update JSON
    python3 << 'EOF'
import json
import sys
import os

config_file = os.environ.get('CONFIG_FILE')
python_path = os.environ.get('PYTHON_PATH')
server_path = os.environ.get('SERVER_PATH')

try:
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    if 'mcpServers' not in config:
        config['mcpServers'] = {}
    
    # Check if pdf-redactor exists
    if 'pdf-redactor' in config['mcpServers']:
        print("WARNING: pdf-redactor entry already exists, overwriting...")
    
    config['mcpServers']['pdf-redactor'] = {
        'command': python_path,
        'args': [server_path]
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("SUCCESS: Configuration updated")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        print_success "Claude Desktop configuration updated"
    else
        print_error "Could not update configuration automatically"
        print_info "Please update manually: $CONFIG_FILE"
    fi
else
    # Create new config
    print_info "Creating new Claude Desktop configuration..."
    cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "$PYTHON_PATH",
      "args": [
        "$SERVER_PATH"
      ]
    }
  }
}
EOF
    print_success "Claude Desktop configuration created"
fi

echo ""
echo "=========================================="
echo "   Installation Complete! 🎉"
echo "=========================================="
echo ""
print_success "RedactAI has been successfully installed and configured!"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Desktop application"
echo "  2. In Claude, type: 'List available Ollama models'"
echo "  3. If you see models listed, installation is successful!"
echo ""
echo "Configuration file location:"
echo "  $CONFIG_FILE"
echo ""
print_info "For troubleshooting, see: https://github.com/AtharvSabde/RedactAI"
echo ""
