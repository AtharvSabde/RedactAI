# 📦 RedactAI Installation Guide

Complete setup instructions for installing and configuring RedactAI with Claude Desktop.

---

## Prerequisites

Before you begin, ensure you have:

✅ **Python 3.8 - 3.12** installed on your system  
✅ **Claude Desktop** application ([Download here](https://claude.ai/download))  
✅ **Ollama** installed and running ([Download here](https://ollama.ai))

---

## Installation Methods

Choose either the **Automated Setup** (recommended) or **Manual Setup** below.

---

## 🚀 Option 1: Automated Setup (Recommended)

The automated script will:
- Create a virtual environment
- Install all dependencies
- Pull the recommended Ollama model
- Configure Claude Desktop automatically
- Verify the installation

### For macOS/Linux:

```bash
curl -O https://raw.githubusercontent.com/AtharvSabde/RedactAI/main/setup.sh && bash setup.sh
```

### For Windows (PowerShell):

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/AtharvSabde/RedactAI/main/setup.ps1" -OutFile "setup.ps1"; .\setup.ps1
```

**After successful installation:**
1. Restart Claude Desktop application
2. Test by typing in Claude: `List available Ollama models`

---

## 🛠️ Option 2: Manual Setup

Follow these steps if you prefer manual installation or if the automated script doesn't work.

### Step 1: Install Ollama

**macOS:**
```bash
# Download and install from https://ollama.ai
# Or use Homebrew
brew install ollama

# Start Ollama service
ollama serve
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

**Windows:**
- Download installer from https://ollama.ai
- Run the installer
- Ollama will start automatically as a service

### Step 2: Pull an Ollama Model

```bash
# Recommended: Balanced model for production use
ollama pull gemma3:4b

# Alternative options:
# Fast model (1B parameters)
ollama pull gemma3:1b

# High accuracy model (12B parameters)
ollama pull gemma3:12b
```

Verify installation:
```bash
ollama list
```

### Step 3: Clone the Repository

```bash
git clone https://github.com/AtharvSabde/RedactAI.git
cd RedactAI
```

### Step 4: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
python --version  # Verify Python version
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
python --version  # Verify Python version
```

### Step 5: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Get Required Paths

**Get Python executable path:**

```bash
# macOS/Linux
which python

# Windows (PowerShell)
where.exe python
```

**Get server.py path:**

```bash
# macOS/Linux
pwd  # Note the current directory path
# Full path will be: /your/path/to/RedactAI/src/server.py

# Windows (PowerShell)
pwd  # Note the current directory path
# Full path will be: C:\your\path\to\RedactAI\src\server.py
```

### Step 7: Configure Claude Desktop

**Locate your Claude configuration file:**

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

**Edit the configuration file:**

Add the following JSON configuration, replacing the paths with your actual paths from Step 6:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "/Users/YourUsername/RedactAI/venv/bin/python",
      "args": [
        "/Users/YourUsername/RedactAI/src/server.py"
      ]
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "C:/Users/YourUsername/RedactAI/venv/Scripts/python.exe",
      "args": [
        "C:/Users/YourUsername/RedactAI/src/server.py"
      ]
    }
  }
}
```

**⚠️ Important Notes:**
- Use forward slashes (`/`) in paths, even on Windows
- Replace `YourUsername` with your actual username
- Ensure paths point to YOUR installation directory
- If you have other MCP servers, add this as an additional entry

**Example with multiple MCP servers:**
```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "/Users/YourUsername/RedactAI/venv/bin/python",
      "args": [
        "/Users/YourUsername/RedactAI/src/server.py"
      ]
    },
    "other-server": {
      "command": "/path/to/other/python",
      "args": ["/path/to/other/server.py"]
    }
  }
}
```

### Step 8: Restart Claude Desktop

1. Completely quit Claude Desktop (not just close the window)
   - **macOS:** Cmd+Q or right-click icon → Quit
   - **Windows:** Right-click system tray icon → Exit
   - **Linux:** Close application completely
2. Reopen Claude Desktop

### Step 9: Verify Installation

In Claude Desktop, try these commands:

```
List available Ollama models
```

```
Check if Ollama is running
```

If you see a response with model information, **installation is successful!** 🎉

---

## 📋 Quick Reference

### Check Ollama Status

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama (if not running)
ollama serve

# List installed models
ollama list
```

### Test Server Manually (Optional)

```bash
# Navigate to RedactAI directory
cd /path/to/RedactAI

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run server
python src/server.py
```

### Update RedactAI

```bash
cd /path/to/RedactAI
git pull origin main
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt --upgrade
```

---

## 🔧 Automated Configuration Script

If you prefer to automate Claude Desktop configuration after manual installation:

```bash
# Navigate to RedactAI directory
cd /path/to/RedactAI

# Run configuration helper
python scripts/configure_claude.py
```

This script will:
- Detect your Python path automatically
- Find your Claude config file location
- Update the configuration safely
- Backup existing config before changes

---

## ✅ Post-Installation Checklist

- [ ] Ollama is installed and running (`ollama list` shows models)
- [ ] At least one model is pulled (recommended: `gemma3:4b`)
- [ ] Virtual environment is created and activated
- [ ] Dependencies are installed (`pip list` shows required packages)
- [ ] Claude Desktop config file is updated with correct paths
- [ ] Claude Desktop is restarted
- [ ] Test command works: `List available Ollama models`

---

## 🆘 Troubleshooting

### Issue: "Cannot connect to Ollama"

**Solution:**
```bash
# Start Ollama service
ollama serve

# In another terminal, verify
curl http://localhost:11434/api/tags
```

### Issue: "MCP server not showing in Claude"

**Solutions:**
1. Verify paths in `claude_desktop_config.json` are absolute (not relative)
2. Check for syntax errors in JSON (use [jsonlint.com](https://jsonlint.com))
3. Ensure Python path points to virtual environment Python, not system Python
4. Restart Claude Desktop completely (quit and reopen)
5. Check Claude logs:
   - **macOS:** `~/Library/Logs/Claude/mcp*.log`
   - **Windows:** `%APPDATA%\Claude\logs\mcp*.log`
   - **Linux:** `~/.local/state/Claude/logs/mcp*.log`

### Issue: "Command 'python' not found"

**Solution:**
Try `python3` instead:
```bash
python3 -m venv venv
```

Update Claude config to use `python3`:
```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "/path/to/venv/bin/python3",
      ...
    }
  }
}
```

### Issue: "Module not found" errors

**Solution:**
```bash
# Ensure you're in the virtual environment
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Windows path with backslashes not working

**Solution:**
Use forward slashes even on Windows:
```json
"command": "C:/Users/YourName/RedactAI/venv/Scripts/python.exe"
```

---

## 📞 Need Help?

- **GitHub Issues:** [Create an issue](https://github.com/AtharvSabde/RedactAI/issues)
- **Documentation:** [Full README](https://github.com/AtharvSabde/RedactAI)
- **Ollama Docs:** [https://ollama.ai/docs](https://ollama.ai/docs)
- **MCP Documentation:** [https://modelcontextprotocol.io](https://modelcontextprotocol.io)

---

## 🎯 Next Steps

Once installation is complete:

1. **Read the Usage Guide:** Learn how to use RedactAI effectively
2. **Try Examples:** Test with sample PDFs (start with simple documents)
3. **Explore Models:** Try different Ollama models to find your preference
4. **Custom Redaction:** Learn about exclude/include features

**Happy Redacting! 🛡️**
