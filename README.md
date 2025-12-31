# RedactAI 🛡️

**Privacy firewall for your PDFs before sending to LLMs**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

---

## 🤐 The Problem

Large Language Models are becoming a default tool for reviewing, summarizing, and extracting insights from documents. But there is a hidden cost.

Most LLMs require raw document input. When you upload a contract, medical record, resume, or internal report, you are often sending unfiltered sensitive data along with it.

This creates real risks:

Personally identifiable information is exposed unintentionally

Confidential or regulated data leaves your control

Manual redaction is slow, error-prone, and inconsistent

Existing redaction tools are either rule-based, cloud-only, or break document structure

In practice, teams are forced to choose between using LLMs effectively and protecting privacy. That trade-off should not exist.

## 🛡️ The Solution

**RedactAI** is an MCP (Model Context Protocol) server that provides AI-powered sensitive data detection and redaction for PDF documents. It leverages local Ollama models to identify and permanently remove personally identifiable information (PII) from PDFs while maintaining document integrity.

Simply provide a PDF file path, and RedactAI will:

- ✅ **Automatically detect** sensitive data (names, emails, dates, IDs, medical info, financial data)
- ✅ **Redact permanently** by blacking out sensitive information
- ✅ **Let you preview** with side-by-side comparison before and after
- ✅ **Choose your model** for speed vs accuracy trade-offs
- ✅ **Customize redactions** by excluding false positives or adding missed items

**Privacy First**: All processing happens locally with Ollama - your data never leaves your machine.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [MCP Configuration](#-mcp-configuration)
- [Model Selection](#-model-selection)
- [Usage Examples](#-usage-examples)
- [Available Tools](#-available-tools)
- [Workflow Example](#-workflow-example)
- [Technical Details](#-technical-details)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🤖 **Flexible Model Selection**
- Choose from any locally installed Ollama model (gemma3:1b, llama3.2:3b, mistral:7b, etc.)
- Trade-off between speed and accuracy based on model size
- Automatic model caching for improved performance

### 🔍 **Comprehensive PII Detection**
Automatically detects and redacts:
- **Names**: Full names of people (John Doe, Dr. Smith, Jane M. Johnson)
- **Emails**: Email addresses (john@email.com, contact@company.org)
- **Phones**: Phone numbers (+1-555-123-4567, (555) 123-4567)
- **Addresses**: Physical addresses (123 Main St, Apt 4B, New York, NY 10001)
- **IDs/SSNs**: ID numbers (123-45-6789, Passport: AB1234567)
- **Credit Cards**: Card numbers (1234-5678-9012-3456)
- **Dates of Birth**: DOB: 01/15/1990, Born: January 15, 1990
- **Medical Info**: Diagnosis codes, patient IDs, prescription info
- **Financial Data**: Account numbers, transaction details, salary info
- **Other PII**: Social media handles, URLs with personal info

### 🎯 **Smart Redaction Modes**

**1. Automatic Redaction** - Full AI-powered detection and redaction

**2. Analysis Mode** - Preview sensitive data before redacting

**3. Custom Redaction** - Fine-tune results with exclude/include lists

### 📄 **Dual Output**
- **Redacted PDF**: Permanently blacks out sensitive information
- **Highlighted PDF**: Preview showing what was detected (yellow highlights)

### 🚀 **User Experience Features**
- Auto-opens both original and redacted PDFs for side-by-side comparison
- Detailed progress tracking for each operation step
- Masked data reporting (shows first/last characters only)
- Cross-platform support (Windows, macOS, Linux)

---

## 🏗️ Architecture

### Technology Stack
- **MCP Framework**: FastMCP for Model Context Protocol implementation
- **LLM Integration**: Ollama API with structured JSON responses
- **PDF Processing**: PyMuPDF (fitz) for text extraction and redaction
- **Text Analysis**: Custom data processor with masking utilities

### Core Components

**1. MCP Server** (`src/server.py`)
- Exposes 5 primary tools via MCP protocol
- Handles LLM instance caching
- Progress tracking and error recovery

**2. Ollama LLM Wrapper** (`src/tools/ollama_llm.py`)
- Robust JSON parsing with error recovery
- Structured schema for consistent output
- Connection health checking

**3. PDF Extractor** (`src/tools/pdf_extractor.py`)
- Text extraction from PDF documents
- Support for page-by-page or full document extraction

**4. Data Processor** (`src/tools/data_processor.py`)
- Flattens and deduplicates sensitive data
- Creates masked versions for secure reporting

**5. PDF Redactor** (`src/tools/pdf_redactor.py`)
- Applies black redactions to matched text
- Generates highlighted preview version
- Per-page redaction statistics

---

## 🔧 Prerequisites

Before installing RedactAI, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python --version
   ```

2. **Ollama installed and running**
   - Download from: https://ollama.ai
   - After installation, start the service:
     ```bash
     ollama serve
     ```

3. **At least one Ollama model** (recommended):
   ```bash
   # Fast model (recommended for getting started)
   ollama pull gemma3:1b
   
   # Balanced model (recommended for production)
   ollama pull gemma3:4b
   
   # Accurate model (for maximum precision)
   ollama pull gemma3:12b
   ```

4. **Claude Desktop** (for MCP integration)
   - Download from: https://claude.ai/download

---

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/AtharvSabde/RedactAI.git
cd RedactAI
```

### Step 2: Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Ollama Connection

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, test it
ollama list
```

---

## ⚙️ MCP Configuration

To use RedactAI with Claude Desktop, you need to add it to your MCP configuration.

### Step 1: Locate Your Config File

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Edit the Configuration

Open `claude_desktop_config.json` and add the RedactAI server:

```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "/path/to/your/RedactAI/venv/Scripts/python.exe",
      "args": [
        "/path/to/your/RedactAI/src/server.py"
      ]
    }
  }
}
```

### Step 3: Update Paths

**⚠️ IMPORTANT:** Replace the paths with your actual installation location.

**Windows Example:**
```json
{
  "mcpServers": {
    "pdf-redactor": {
      "command": "C:/Users/YourUsername/Desktop/RedactAI/venv/Scripts/python.exe",
      "args": [
        "C:/Users/YourUsername/Desktop/RedactAI/src/server.py"
      ]
    }
  }
}
```

**macOS/Linux Example:**
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

### Step 4: Restart Claude Desktop

Close and reopen Claude Desktop to load the new MCP server.

### Step 5: Verify Installation

In Claude, try:
```
List available Ollama models
```

If you see a list of models, RedactAI is successfully configured! 🎉

---

## 🎯 Model Selection

Choose the right model based on your needs:

| Model | Parameters | Speed | Accuracy | Best For |
|-------|-----------|-------|----------|----------|
| **gemma3:1b** | 1 Billion | ⚡ Fast (14s) | Basic | Quick scans, simple documents |
| **gemma3:4b** | 4 Billion | ⚖️ Balanced (49s) | High | **Recommended** - Production use |
| **gemma3:12b** | 12 Billion | 🐢 Slow (108s) | Higher | Maximum accuracy, complex documents |

### Benchmark Results (2-page resume):

- **gemma3:1b**: 9 redactions in 14 seconds (basic detection)
- **gemma3:4b**: 38 redactions in 49 seconds (aggressive detection) ⭐ **Recommended**
- **gemma3:12b**: 14 redactions in 108 seconds (smart/selective)

**Recommendation:** Start with `gemma3:4b` for the best balance of speed and accuracy.

### General Guidelines:

| Model Size | Parameters | Speed | Accuracy | Best For |
|------------|-----------|-------|----------|----------|
| Small | 1B-4B | ⚡⚡⚡ | ⭐⭐ | Quick processing, simple documents |
| Medium | 4B-12B | ⚡⚡ | ⭐⭐⭐ | Balanced use, most documents |
| Large | 12B+ | ⚡ | ⭐⭐⭐⭐ | High accuracy, complex documents |

---

## 🚀 Usage Examples

### Example 1: Basic Redaction

In Claude Desktop, simply say:

```
Redact "C:\Users\atharv\Desktop\resume.pdf"
```

RedactAI will:
1. ✅ Analyze the PDF with the default model (gemma3:1b)
2. ✅ Detect all sensitive information
3. ✅ Create a redacted version
4. ✅ Auto-open both PDFs side-by-side for comparison

### Example 2: Using a Different Model

```
Redact my resume using gemma3:4b model for better accuracy
```

### Example 3: Custom Redaction

After seeing the first redaction:

```
Redact again but don't redact my name "John Doe" and DO redact "Google" and "Project X"
```

RedactAI will use the `redact_pdf_custom` tool to:
- Exclude: "John Doe"
- Include: "Google", "Project X"

### Example 4: Analysis Only (Preview)

```
Analyze "C:\Documents\contract.pdf" without redacting
```

This shows you what would be redacted without creating a new file.

### Example 5: Check Available Models

```
What Ollama models do I have available?
```

### Example 6: Check Ollama Status

```
Is Ollama running and ready?
```

---

## 🛠️ Available Tools

RedactAI provides 5 MCP tools:

### 1. `list_available_models()`
Lists all Ollama models installed on your system with size and details.

**Returns**: JSON with model list and size-to-accuracy guidance

**Use case:** Check which models you can use before redacting.

---

### 2. `check_ollama_status(model, base_url)`
Verifies Ollama service is running and specified model is available.

**Parameters:**
- `model` (optional): Model name to check (default: "gemma3:1b")
- `base_url` (optional): Ollama API URL (default: "http://localhost:11434")

**Use case:** Troubleshooting connection issues.

---

### 3. `analyze_pdf_sensitive_data(pdf_path, pdf_base64, model)`
Analyzes PDF to detect sensitive information WITHOUT redacting.

**Parameters:**
- `pdf_path`: Local file path to PDF
- `pdf_base64` (optional): Base64 encoded PDF data
- `model` (optional): Ollama model to use (default: "gemma3:1b")

**Returns:**
- Masked preview of detected data
- Categories and counts
- No files created

**Use case:** Preview before permanent redaction.

---

### 4. `redact_pdf(pdf_path, pdf_base64, model, return_base64, auto_open)`
Permanently redacts sensitive data from PDF.

**Parameters:**
- `pdf_path`: Local file path to PDF
- `pdf_base64` (optional): Base64 encoded PDF data
- `model` (optional): Model to use (default: "gemma3:1b")
- `return_base64` (optional): Return as base64 (default: false)
- `auto_open` (optional): Auto-open PDFs (default: true)

**Returns:**
- Redacted PDF (blacked out sensitive data)
- Highlighted preview PDF (shows what was redacted)
- Detailed summary with masked data
- Statistics per page

**Use case:** Main redaction workflow.

---

### 5. `redact_pdf_custom(pdf_path, exclude_items, include_items, model, auto_open, return_base64)`
Custom redaction with user-specified exclusions and additions.

**Parameters:**
- `pdf_path`: Path to ORIGINAL PDF (required)
- `exclude_items`: List of strings to NOT redact
- `include_items`: List of strings to forcefully redact
- `model` (optional): Model to use (default: "gemma3:1b")
- `auto_open` (optional): Auto-open PDFs (default: true)
- `return_base64` (optional): Return as base64 (default: false)

**Example:**
```json
{
  "pdf_path": "resume.pdf",
  "exclude_items": ["John Doe", "john@email.com"],
  "include_items": ["Secret Project", "XYZ Corp"],
  "model": "gemma3:4b"
}
```

**Use case:** Fine-tune redactions after initial pass. User reviews initial redaction and says "don't redact my name, but DO redact 'Google'".

---

## 🔄 Workflow Example

```plaintext
1. User uploads PDF → analyze_pdf_sensitive_data()
2. Review masked sensitive data → Decide what to redact
3. Run redact_pdf() → Get redacted + highlighted PDFs
4. Both PDFs auto-open side-by-side
5. If adjustments needed → Use redact_pdf_custom()
   - Exclude false positives
   - Include additional items
6. Final redacted PDF ready for sharing
```

---

## 🔬 Technical Details

### Progress Tracking
Every operation includes detailed progress tracking with timestamps and elapsed time for each step:
- Connection status
- Text extraction
- LLM analysis
- Redaction application
- File generation

### JSON Schema Enforcement
The LLM wrapper uses structured JSON schemas to ensure consistent output format, with fallback error recovery mechanisms. The system enforces a strict schema with all required PII categories.

### Data Masking Strategy
Sensitive data in reports is masked showing only first 2 and last 2 characters:
- **General**: `Jo***oe` (John Doe)
- **Emails**: Special handling - `jo***n@em***l.com` (john@email.com)
- **Short values**: Fully masked with asterisks

### Redaction Algorithm
The system performs exact text matching across all pages:
1. Searches for each sensitive value in the document
2. Applies black redactions (`fill=(0, 0, 0)`) to the main document
3. Creates yellow highlights (`stroke=[1, 1, 0]`) in the preview version
4. Tracks statistics per page

### Error Handling
The system includes comprehensive error handling:
- **Connection failures**: Validates Ollama connectivity before processing
- **LLM timeouts**: 300-second timeout with clear error messages
- **JSON parsing**: Multiple fallback strategies for malformed responses
  - Direct JSON parse
  - Markdown code block extraction
  - Regex-based JSON extraction
  - Common formatting fixes
- **File operations**: Graceful handling of permission issues with temp directory fallback

### Platform Support
Auto-open functionality is cross-platform:
- **Windows**: Uses `os.startfile()`
- **macOS**: Uses `open` command
- **Linux**: Uses `xdg-open` command

---

## 🐛 Troubleshooting

### Issue 1: "Cannot connect to Ollama"

**Solution:**
```bash
# Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

---

### Issue 2: "Model not found"

**Solution:**
```bash
# List installed models
ollama list

# Install missing model
ollama pull gemma3:1b
```

---

### Issue 3: "MCP server not showing in Claude"

**Solution:**
1. Verify paths in `claude_desktop_config.json` are correct
2. Use forward slashes (`/`) even on Windows, or escape backslashes (`\\`)
3. Restart Claude Desktop completely
4. Check Claude logs:
   - Windows: `%APPDATA%\Claude\logs`
   - macOS: `~/Library/Logs/Claude`

---

### Issue 4: "PDFs not opening automatically"

**Solution:**
- Ensure you have a PDF viewer installed (Adobe Reader, browser, etc.)
- Try manually opening from the output path
- Set `auto_open: false` in the tool call if it's causing issues

---

### Issue 5: "Redaction too slow"

**Solution:**
- Use a smaller model: `gemma3:1b` (fastest)
- Process fewer pages at once
- Upgrade your hardware (more RAM/CPU helps)

---

### Issue 6: "LLM returned empty result"

**Solution:**
```bash
# Check Ollama logs
ollama logs

# Restart Ollama
# Windows: Stop and restart the service
# macOS/Linux: 
killall ollama
ollama serve
```

---

### Issue 7: "Too many/too few redactions"

**Solution:**
- Try different models: `gemma3:4b` or `gemma3:12b`
- Use `redact_pdf_custom` to fine-tune results
- Exclude false positives or include missed items

---

## 📁 Project Structure

```
RedactAI/
├── src/
│   ├── server.py              # Main MCP server (FastMCP)
│   ├── tools/
│   │   ├── ollama_llm.py      # Ollama LLM integration
│   │   ├── pdf_extractor.py   # PDF text extraction
│   │   ├── data_processor.py  # Sensitive data processing
│   │   └── pdf_redactor.py    # PDF redaction logic
│   └── __pycache__/
├── venv/                       # Virtual environment
├── .gitignore
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔒 Security Considerations

1. **Original files are never modified** - Redactions create new files
2. **Temporary files are cleaned up** - Automatic cleanup in finally blocks
3. **Masked reporting** - Sensitive data never exposed in full in logs/responses
4. **Local processing** - All LLM operations run locally via Ollama (no cloud APIs)
5. **No data transmission** - Your sensitive documents stay on your machine

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/RedactAI.git
cd RedactAI

# Create venv and install dependencies
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Test changes
python src/server.py
```


---

## 💡 Important Notes

- This is an **MCP server** - it exposes tools via the Model Context Protocol, not a standalone CLI application
- The server must be running and connected to an MCP client (like Claude Desktop) to use the tools
- All operations return detailed JSON responses with progress tracking and error information
- The system requires Ollama to be running locally at `http://localhost:11434` by default
- Larger models provide better accuracy but require more computational resources and time
- The highlighted PDF serves as a preview/audit trail of what was redacted

---

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for Claude and MCP
- [Ollama](https://ollama.ai) for local LLM infrastructure
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing
- [FastMCP](https://github.com/jlowin/fastmcp) for MCP server framework

---

## 📧 Contact

**Atharv Sabde**
- GitHub: [@AtharvSabde](https://github.com/AtharvSabde)
- Project: [RedactAI](https://github.com/AtharvSabde/RedactAI)

---

## 🌟 Star the Repo!

If RedactAI helped you protect your privacy, please ⭐ star the repo on GitHub!

---

**Built with ❤️ for privacy-conscious AI users**
