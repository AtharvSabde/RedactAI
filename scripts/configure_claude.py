#!/usr/bin/env python3
"""
RedactAI - Claude Desktop Configuration Helper

This script automatically configures Claude Desktop to use RedactAI MCP server.
"""

import json
import os
import sys
import platform
from pathlib import Path
from datetime import datetime


def print_success(message):
    print(f"✓ {message}")


def print_error(message):
    print(f"✗ {message}", file=sys.stderr)


def print_info(message):
    print(f"ℹ {message}")


def print_warning(message):
    print(f"⚠ {message}")


def get_claude_config_path():
    """Get the Claude Desktop configuration file path based on OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    elif system == "Linux":
        config_dir = Path.home() / ".config" / "Claude"
    elif system == "Windows":
        config_dir = Path(os.environ.get("APPDATA", "")) / "Claude"
    else:
        print_error(f"Unsupported operating system: {system}")
        return None
    
    return config_dir / "claude_desktop_config.json"


def get_python_path():
    """Get the current Python executable path."""
    return sys.executable


def get_server_path():
    """Get the RedactAI server.py path."""
    # Assume this script is in the scripts/ directory
    current_dir = Path(__file__).parent.parent
    server_path = current_dir / "src" / "server.py"
    
    if not server_path.exists():
        print_error(f"Server file not found at: {server_path}")
        print_info("Please ensure you're running this from the RedactAI directory")
        return None
    
    return server_path


def backup_config(config_path):
    """Backup existing configuration file."""
    if config_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"claude_desktop_config.json.backup.{timestamp}"
        
        try:
            import shutil
            shutil.copy2(config_path, backup_path)
            print_success(f"Backed up existing config to: {backup_path}")
            return True
        except Exception as e:
            print_warning(f"Could not backup config: {e}")
            return False
    return True


def load_config(config_path):
    """Load existing configuration or create empty one."""
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print_info("Loaded existing configuration")
            return config
        except json.JSONDecodeError as e:
            print_error(f"Configuration file is not valid JSON: {e}")
            print_info("Creating new configuration")
            return {}
        except Exception as e:
            print_error(f"Could not read configuration file: {e}")
            return None
    else:
        print_info("No existing configuration found, creating new one")
        return {}


def update_config(config, python_path, server_path):
    """Update configuration with RedactAI server."""
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Check if pdf-redactor already exists
    if "pdf-redactor" in config["mcpServers"]:
        print_warning("pdf-redactor entry already exists in configuration")
        response = input("Do you want to overwrite it? (y/n): ").lower().strip()
        if response != 'y':
            print_info("Skipping configuration update")
            return config, False
    
    # Convert paths to strings and use forward slashes (works on all platforms)
    python_path_str = str(python_path).replace('\\', '/')
    server_path_str = str(server_path).replace('\\', '/')
    
    config["mcpServers"]["pdf-redactor"] = {
        "command": python_path_str,
        "args": [server_path_str]
    }
    
    return config, True


def save_config(config_path, config):
    """Save configuration to file."""
    try:
        # Create directory if it doesn't exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        print_success(f"Configuration saved to: {config_path}")
        return True
    except Exception as e:
        print_error(f"Could not save configuration: {e}")
        return False


def verify_installation():
    """Verify that all required components are available."""
    print_info("Verifying installation...")
    
    all_good = True
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 8) and python_version <= (3, 12):
        print_success(f"Python version OK: {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print_warning(f"Python version {python_version.major}.{python_version.minor} may not be optimal (recommended: 3.8-3.12)")
    
    # Check required packages
    try:
        import fastmcp
        print_success("fastmcp package installed")
    except ImportError:
        print_error("fastmcp package not found")
        print_info("Run: pip install -r requirements.txt")
        all_good = False
    
    try:
        import fitz  # PyMuPDF
        print_success("PyMuPDF package installed")
    except ImportError:
        print_error("PyMuPDF package not found")
        print_info("Run: pip install -r requirements.txt")
        all_good = False
    
    # Check Ollama
    try:
        import subprocess
        result = subprocess.run(['ollama', 'list'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            print_success("Ollama is installed and accessible")
        else:
            print_warning("Ollama command executed but returned error")
            all_good = False
    except FileNotFoundError:
        print_error("Ollama is not installed or not in PATH")
        print_info("Install from: https://ollama.ai")
        all_good = False
    except Exception as e:
        print_warning(f"Could not verify Ollama: {e}")
    
    return all_good


def main():
    """Main configuration function."""
    print("=" * 50)
    print("RedactAI - Claude Desktop Configuration Helper")
    print("=" * 50)
    print()
    
    # Verify installation first
    if not verify_installation():
        print()
        print_warning("Some components are missing. Please install them first.")
        response = input("Continue anyway? (y/n): ").lower().strip()
        if response != 'y':
            print_info("Configuration cancelled")
            return 1
    
    print()
    
    # Get configuration file path
    config_path = get_claude_config_path()
    if not config_path:
        return 1
    
    print_info(f"Configuration file: {config_path}")
    
    # Get Python and server paths
    python_path = get_python_path()
    print_success(f"Python path: {python_path}")
    
    server_path = get_server_path()
    if not server_path:
        return 1
    print_success(f"Server path: {server_path}")
    
    print()
    
    # Backup existing config
    if not backup_config(config_path):
        response = input("Could not backup config. Continue anyway? (y/n): ").lower().strip()
        if response != 'y':
            print_info("Configuration cancelled")
            return 1
    
    # Load existing config
    config = load_config(config_path)
    if config is None:
        return 1
    
    # Update config
    config, updated = update_config(config, python_path, server_path)
    
    if not updated:
        print_info("Configuration not modified")
        return 0
    
    # Save config
    if not save_config(config_path, config):
        return 1
    
    print()
    print("=" * 50)
    print("Configuration Complete! 🎉")
    print("=" * 50)
    print()
    print_success("RedactAI has been configured in Claude Desktop")
    print()
    print("Next steps:")
    print("  1. Restart Claude Desktop application")
    print("  2. In Claude, type: 'List available Ollama models'")
    print("  3. If you see models listed, configuration is successful!")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_info("Configuration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)