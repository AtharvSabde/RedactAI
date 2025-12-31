"""
MCP Server for PDF Redaction with Ollama - ENHANCED VERSION
New Features:
1. User can choose which Ollama model to use
2. Auto-opens redacted PDF when complete
3. Custom redaction tool for user modifications
4. Exclude/include specific items
5. Keeps original PDF safe
"""

import sys
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

import os
import json
import base64
import tempfile
import logging
import platform
from typing import Optional, Dict, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Import your existing modules
from tools.ollama_llm import OllamaLLM
from tools.pdf_extractor import get_pdf_text
from tools.data_processor import post_process_sensitive_data, mask_sensitive_data
from tools.pdf_redactor import apply_redactions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("RedactAI")

# Cache for LLM instances (keyed by model name)
llm_cache: Dict[str, OllamaLLM] = {}


class ProgressTracker:
    """Track and report progress through redaction pipeline."""
    
    def __init__(self):
        self.steps = []
        self.start_time = datetime.now()
    
    def add_step(self, step_name: str, status: str = "in_progress", details: str = ""):
        """Add a step to the progress tracker."""
        step = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": (datetime.now() - self.start_time).total_seconds()
        }
        if details:
            step["details"] = details
        self.steps.append(step)
        logger.info(f"[{status.upper()}] {step_name}: {details}")
    
    def complete_step(self, step_name: str, details: str = ""):
        """Mark the last step as completed."""
        if self.steps and self.steps[-1]["step"] == step_name:
            self.steps[-1]["status"] = "completed"
            if details:
                self.steps[-1]["details"] = details
        logger.info(f"[COMPLETED] {step_name}: {details}")
    
    def fail_step(self, step_name: str, error: str):
        """Mark the last step as failed."""
        if self.steps and self.steps[-1]["step"] == step_name:
            self.steps[-1]["status"] = "failed"
            self.steps[-1]["error"] = error
        logger.error(f"[FAILED] {step_name}: {error}")
    
    def get_summary(self) -> Dict:
        """Get progress summary."""
        return {
            "total_time_seconds": (datetime.now() - self.start_time).total_seconds(),
            "steps_completed": len([s for s in self.steps if s["status"] == "completed"]),
            "steps_failed": len([s for s in self.steps if s["status"] == "failed"]),
            "steps": self.steps
        }


def get_llm(model: str = "gemma3:1b", base_url: str = "http://localhost:11434") -> OllamaLLM:
    """
    Get or create LLM instance with caching.
    
    Args:
        model: Ollama model name (e.g., "gemma3:1b", "llama3.2:3b", "mistral:7b")
        base_url: Ollama API base URL
        
    Returns:
        OllamaLLM instance
    """
    cache_key = f"{model}:{base_url}"
    
    if cache_key not in llm_cache:
        llm_cache[cache_key] = OllamaLLM(model=model, base_url=base_url)
        logger.info(f"Initialized LLM with model: {model}")
    
    return llm_cache[cache_key]


def open_pdf(file_path: str) -> bool:
    """
    Auto-open PDF file based on operating system.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Cannot open PDF: File not found at {file_path}")
            return False
        
        system = platform.system()
        
        if system == 'Windows':
            os.startfile(file_path)
            logger.info(f"Opened PDF on Windows: {file_path}")
        elif system == 'Darwin':  # macOS
            os.system(f'open "{file_path}"')
            logger.info(f"Opened PDF on macOS: {file_path}")
        else:  # Linux
            os.system(f'xdg-open "{file_path}"')
            logger.info(f"Opened PDF on Linux: {file_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error opening PDF: {e}")
        return False


def save_base64_to_temp(base64_data: str, suffix: str = ".pdf") -> str:
    """Save base64 encoded data to a temporary file."""
    try:
        # Handle data URL format if present
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(base64.b64decode(base64_data))
            logger.info(f"Saved base64 data to temp file: {tmp.name}")
            return tmp.name
    except Exception as e:
        logger.error(f"Error saving base64 to temp file: {e}")
        raise


def file_to_base64(file_path: str) -> str:
    """Convert file to base64 string with proper error handling."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            base64_str = base64.b64encode(data).decode('utf-8')
            logger.info(f"Converted {file_path} to base64 ({len(base64_str)} chars)")
            return base64_str
    except Exception as e:
        logger.error(f"Error converting file to base64: {e}")
        raise


@mcp.tool()
def list_available_models() -> str:
    """
    List all Ollama models available on the local system.
    
    Returns:
        JSON string with list of available models and their details.
        
    Use this to see which models you can use for redaction.
    
    Note: As model size/parameters increase, you get more accurate results but slower processing.
    Choose based on your needs:
    - Smaller models (1B-4B parameters): Fast, good for most documents
    - Medium models (4-12B parameters): Balanced accuracy and speed
    - Larger models (12B+ parameters): High accuracy, slower processing
    """
    try:
        import requests
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        if response.status_code != 200:
            return json.dumps({
                "error": "Cannot connect to Ollama",
                "message": "Make sure Ollama is running with 'ollama serve'"
            }, indent=2)
        
        data = response.json()
        models = data.get("models", [])
        
        if not models:
            return json.dumps({
                "status": "no_models",
                "message": "No models installed. Install one with: ollama pull gemma3:1b",
                "available_models": []
            }, indent=2)
        
        # Extract model names and info
        model_list = []
        for model in models:
            model_list.append({
                "name": model.get("name", "unknown"),
                "size": model.get("size", 0),
                "modified": model.get("modified_at", "")
            })
        
        return json.dumps({
            "status": "success",
            "total_models": len(model_list),
            "models": model_list,
            "guidance": "As model size increases, you get more accurate results but slower processing. Choose based on your priority: speed vs accuracy."
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "message": "Error listing models"
        }, indent=2)


@mcp.tool()
def check_ollama_status(
    model: str = "gemma3:1b",
    base_url: str = "http://localhost:11434"
) -> str:
    """
    Check if Ollama service is running and if specified model is available.
    
    Args:
        model: Name of the Ollama model to check (default: "gemma3:1b")
        base_url: Ollama API base URL (default: "http://localhost:11434")
    
    Returns:
        Connection status and model availability.
        
    Use this before running redaction operations to verify your chosen model.
    """
    tracker = ProgressTracker()
    
    try:
        tracker.add_step("Checking Ollama Connection", "in_progress")
        llm_instance = get_llm(model=model, base_url=base_url)
        is_connected = llm_instance.check_connection()
        
        if is_connected:
            tracker.complete_step("Checking Ollama Connection", "Successfully connected")
        else:
            tracker.fail_step("Checking Ollama Connection", "Cannot connect to Ollama")
        
        result = {
            "status": "connected" if is_connected else "disconnected",
            "model": model,
            "base_url": base_url,
            "message": f"Ollama is running and '{model}' is ready" if is_connected else "Cannot connect to Ollama. Make sure it's running with 'ollama serve'",
            "progress": tracker.get_summary()
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        tracker.fail_step("Checking Ollama Connection", str(e))
        return json.dumps({
            "error": str(e),
            "progress": tracker.get_summary()
        }, indent=2)


@mcp.tool()
def analyze_pdf_sensitive_data(
    pdf_path: Optional[str] = None,
    pdf_base64: Optional[str] = None,
    model: str = "gemma3:1b"
) -> str:
    """
    Analyze a PDF document to detect sensitive personal information without redacting.
    
    Args:
        pdf_path: Local file path to the PDF document
        pdf_base64: Base64 encoded PDF data (alternative to pdf_path)
        model: Ollama model to use for analysis (default: "gemma3:1b")
               Use list_available_models() to see all available models.
               Note: Larger models = more accurate but slower processing
    
    Returns:
        JSON string with detailed report of all sensitive data found including:
        - names, emails, phone numbers, addresses
        - IDs/SSNs, credit cards, dates of birth
        - medical info, financial data
        - Progress tracking for each step
        
    Useful for preview before redaction.
    """
    tracker = ProgressTracker()
    temp_file = None
    
    try:
        # Step 1: Initialize
        tracker.add_step("Initialization", "in_progress", f"Setting up with model: {model}")
        llm_instance = get_llm(model=model)
        tracker.complete_step("Initialization", f"LLM instance ready with {model}")
        
        # Step 2: Check Ollama
        tracker.add_step("Ollama Connection Check", "in_progress")
        if not llm_instance.check_connection():
            tracker.fail_step("Ollama Connection Check", "Cannot connect to Ollama")
            return json.dumps({
                "error": "Cannot connect to Ollama. Make sure it's running with 'ollama serve'",
                "progress": tracker.get_summary()
            }, indent=2)
        tracker.complete_step("Ollama Connection Check", "Connected successfully")
        
        # Step 3: Handle input
        tracker.add_step("Input Processing", "in_progress")
        if pdf_base64:
            tracker.add_step("Base64 Decoding", "in_progress", f"Decoding {len(pdf_base64)} chars")
            temp_file = save_base64_to_temp(pdf_base64)
            pdf_path = temp_file
            tracker.complete_step("Base64 Decoding", f"Saved to {temp_file}")
        
        if not pdf_path:
            tracker.fail_step("Input Processing", "No input provided")
            return json.dumps({
                "error": "Either pdf_path or pdf_base64 must be provided",
                "progress": tracker.get_summary()
            }, indent=2)
        
        if not os.path.exists(pdf_path):
            tracker.fail_step("Input Processing", f"File not found: {pdf_path}")
            return json.dumps({
                "error": f"PDF file not found: {pdf_path}",
                "progress": tracker.get_summary()
            }, indent=2)
        
        file_size = os.path.getsize(pdf_path)
        tracker.complete_step("Input Processing", f"File ready ({file_size} bytes)")
        
        # Step 4: Extract text
        tracker.add_step("Text Extraction", "in_progress", "Extracting text from PDF")
        text = get_pdf_text(pdf_path)
        text_length = len(text)
        tracker.complete_step("Text Extraction", f"Extracted {text_length} characters")
        
        # Step 5: Detect sensitive data
        tracker.add_step("Sensitive Data Detection", "in_progress", f"Analyzing with {model}")
        sensitive_data = llm_instance.get_sensitive_data(text)
        
        # Check if LLM actually returned data or if it failed silently
        if sensitive_data is None or (isinstance(sensitive_data, dict) and len(sensitive_data) == 0):
            tracker.fail_step("Sensitive Data Detection", "LLM returned empty result - possible timeout or error")
            return json.dumps({
                "error": "LLM failed to analyze the document. Please check Ollama logs.",
                "suggestion": "Try with a smaller document or check if model is loaded",
                "progress": tracker.get_summary()
            }, indent=2)
        
        tracker.complete_step("Sensitive Data Detection", f"Analysis complete - {len(sensitive_data)} categories checked")
        
        # Step 6: Process results
        tracker.add_step("Results Processing", "in_progress")
        
        if not sensitive_data or all(len(v) == 0 for v in sensitive_data.values()):
            tracker.complete_step("Results Processing", "No sensitive data found")
            result = {
                "status": "no_sensitive_data",
                "message": "No sensitive data detected in the PDF",
                "model_used": model,
                "progress": tracker.get_summary()
            }
        else:
            # Create masked version
            masked_data = mask_sensitive_data(sensitive_data)
            
            # Count items
            category_counts = {k: len(v) for k, v in sensitive_data.items() if v}
            total_items = sum(category_counts.values())
            
            tracker.complete_step("Results Processing", f"Found {total_items} items")
            
            result = {
                "status": "success",
                "total_sensitive_items": total_items,
                "categories": category_counts,
                "masked_data": masked_data,
                "model_used": model,
                "message": f"Found {total_items} sensitive items across {len(category_counts)} categories",
                "progress": tracker.get_summary()
            }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in analyze_pdf_sensitive_data: {error_msg}", exc_info=True)
        tracker.fail_step("Analysis", error_msg)
        return json.dumps({
            "error": error_msg,
            "error_type": type(e).__name__,
            "progress": tracker.get_summary()
        }, indent=2)
    
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logger.info(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")


@mcp.tool()
def redact_pdf(
    pdf_path: Optional[str] = None,
    pdf_base64: Optional[str] = None,
    model: str = "gemma3:1b",
    return_base64: bool = False,
    auto_open: bool = True
) -> str:
    """
    Redact sensitive data from a PDF document with auto-open functionality.
    
    Detects and permanently removes (blacks out) all sensitive information including:
    - names, emails, phone numbers, addresses
    - IDs/SSNs, credit cards, dates of birth
    - medical info, financial data
    
    When auto_open is True, opens BOTH the original and redacted PDFs side-by-side
    for easy comparison.
    
    Args:
        pdf_path: Local file path to the PDF document
        pdf_base64: Base64 encoded PDF data (alternative to pdf_path)
        model: Ollama model to use for detection (default: "gemma3:1b")
               Use list_available_models() to see all available models.
               Note: Larger models = more accurate but slower processing
        return_base64: If true, return PDFs as base64. If false, return file paths only.
        auto_open: If true, automatically opens BOTH original and redacted PDFs
    
    Returns:
        JSON string with:
        - Redacted PDF (as path or base64)
        - Highlighted preview PDF showing what was redacted
        - Detailed summary with masked versions of detected data
        - Statistics on redactions per page
        - Complete progress tracking
    """
    tracker = ProgressTracker()
    temp_file = None
    
    try:
        # Step 1: Initialize
        tracker.add_step("Initialization", "in_progress", f"Setting up with model: {model}")
        llm_instance = get_llm(model=model)
        tracker.complete_step("Initialization", f"LLM instance ready with {model}")
        
        # Step 2: Check Ollama
        tracker.add_step("Ollama Connection Check", "in_progress")
        if not llm_instance.check_connection():
            tracker.fail_step("Ollama Connection Check", "Cannot connect to Ollama")
            return json.dumps({
                "error": "Cannot connect to Ollama. Make sure it's running with 'ollama serve'",
                "progress": tracker.get_summary()
            }, indent=2)
        tracker.complete_step("Ollama Connection Check", "Connected successfully")
        
        # Step 3: Handle input
        tracker.add_step("Input Processing", "in_progress")
        if pdf_base64:
            tracker.add_step("Base64 Decoding", "in_progress", f"Decoding {len(pdf_base64)} chars")
            temp_file = save_base64_to_temp(pdf_base64)
            pdf_path = temp_file
            tracker.complete_step("Base64 Decoding", f"Saved to {temp_file}")
        
        if not pdf_path:
            tracker.fail_step("Input Processing", "No input provided")
            return json.dumps({
                "error": "Either pdf_path or pdf_base64 must be provided",
                "progress": tracker.get_summary()
            }, indent=2)
        
        if not os.path.exists(pdf_path):
            tracker.fail_step("Input Processing", f"File not found: {pdf_path}")
            return json.dumps({
                "error": f"PDF file not found: {pdf_path}",
                "progress": tracker.get_summary()
            }, indent=2)
        
        file_size = os.path.getsize(pdf_path)
        tracker.complete_step("Input Processing", f"File ready ({file_size} bytes)")
        
        # Step 4: Extract text
        tracker.add_step("Text Extraction", "in_progress", "Extracting text from PDF")
        text = get_pdf_text(pdf_path)
        text_length = len(text)
        tracker.complete_step("Text Extraction", f"Extracted {text_length} characters")
        
        # Step 5: Detect sensitive data
        tracker.add_step("Sensitive Data Detection", "in_progress", f"Analyzing with {model}")
        sensitive_data = llm_instance.get_sensitive_data(text)
        
        # Check if LLM actually returned data or if it failed silently
        if sensitive_data is None or (isinstance(sensitive_data, dict) and len(sensitive_data) == 0):
            tracker.fail_step("Sensitive Data Detection", "LLM returned empty result")
            return json.dumps({
                "error": "LLM failed to analyze the document. Please check Ollama logs.",
                "progress": tracker.get_summary()
            }, indent=2)
        
        tracker.complete_step("Sensitive Data Detection", "Analysis complete")
        
        # Step 6: Check if anything found
        if not sensitive_data or all(len(v) == 0 for v in sensitive_data.values()):
            tracker.add_step("Validation", "completed", "No sensitive data to redact")
            return json.dumps({
                "status": "no_sensitive_data",
                "message": "No sensitive data detected, nothing to redact",
                "model_used": model,
                "progress": tracker.get_summary()
            }, indent=2)
        
        # Step 7: Process sensitive values
        tracker.add_step("Data Processing", "in_progress", "Processing detected values")
        sensitive_values = post_process_sensitive_data(sensitive_data)
        
        if not isinstance(sensitive_values, list):
            tracker.fail_step("Data Processing", f"Expected list but got {type(sensitive_values)}")
            return json.dumps({
                "error": f"post_process_sensitive_data returned {type(sensitive_values)} instead of list",
                "progress": tracker.get_summary()
            }, indent=2)
        
        total_values = len(sensitive_values)
        tracker.complete_step("Data Processing", f"Processed {total_values} unique values")
        
        if total_values == 0:
            tracker.add_step("Validation", "completed", "No values to redact after processing")
            return json.dumps({
                "status": "no_sensitive_data",
                "message": "No sensitive data to redact after processing",
                "model_used": model,
                "progress": tracker.get_summary()
            }, indent=2)
        
        # Step 8: Apply redactions
        tracker.add_step("PDF Redaction", "in_progress", f"Applying redactions for {total_values} values")
        redaction_summary, highlighted_path = apply_redactions(pdf_path, sensitive_values)
        tracker.complete_step("PDF Redaction", f"Redacted {redaction_summary['total_redactions']} instances")
        
        # Step 9: Create masked data
        tracker.add_step("Masking Data", "in_progress", "Creating masked report")
        masked_data = mask_sensitive_data(sensitive_data)
        redaction_summary["masked_sensitive_data"] = masked_data
        redaction_summary["model_used"] = model
        tracker.complete_step("Masking Data", "Report ready")
        
        # Step 10: Auto-open PDFs if requested
        if auto_open and not return_base64:
            # First open the original for comparison
            tracker.add_step("Opening Original PDF", "in_progress", "Opening original PDF for review")
            opened_original = open_pdf(pdf_path)
            if opened_original:
                tracker.complete_step("Opening Original PDF", "Original PDF opened")
            else:
                tracker.fail_step("Opening Original PDF", "Could not open original PDF")
            
            # Then open the redacted version
            tracker.add_step("Opening Redacted PDF", "in_progress", "Opening redacted PDF")
            opened_redacted = open_pdf(redaction_summary["redacted_pdf_path"])
            if opened_redacted:
                tracker.complete_step("Opening Redacted PDF", "Redacted PDF opened")
            else:
                tracker.fail_step("Opening Redacted PDF", "Could not open redacted PDF")
        
        # Step 11: Prepare output
        tracker.add_step("Output Preparation", "in_progress")
        
        if return_base64:
            tracker.add_step("Base64 Encoding", "in_progress", "Encoding redacted PDF")
            redacted_base64 = file_to_base64(redaction_summary["redacted_pdf_path"])
            tracker.complete_step("Base64 Encoding", f"Encoded {len(redacted_base64)} chars")
            
            tracker.add_step("Base64 Encoding Highlighted", "in_progress", "Encoding preview PDF")
            highlighted_base64 = file_to_base64(highlighted_path)
            tracker.complete_step("Base64 Encoding Highlighted", f"Encoded {len(highlighted_base64)} chars")
            
            result = {
                "status": "success",
                "total_redactions": redaction_summary["total_redactions"],
                "total_pages": redaction_summary["total_pages"],
                "masked_data": masked_data,
                "model_used": model,
                "redacted_pdf_base64": redacted_base64,
                "highlighted_pdf_base64": highlighted_base64,
                "message": f"Successfully redacted {redaction_summary['total_redactions']} instances using {model}",
                "progress": tracker.get_summary()
            }
        else:
            result = {
                "status": "success",
                "total_redactions": redaction_summary["total_redactions"],
                "total_pages": redaction_summary["total_pages"],
                "masked_data": masked_data,
                "model_used": model,
                "redacted_pdf_path": redaction_summary["redacted_pdf_path"],
                "highlighted_pdf_path": highlighted_path,
                "pdf_opened": auto_open,
                "message": f"Successfully redacted {redaction_summary['total_redactions']} instances using {model}",
                "progress": tracker.get_summary()
            }
        
        tracker.complete_step("Output Preparation", "Ready to return")
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in redact_pdf: {error_msg}", exc_info=True)
        
        import traceback
        full_traceback = traceback.format_exc()
        
        tracker.fail_step("Redaction", error_msg)
        
        return json.dumps({
            "error": error_msg,
            "error_type": type(e).__name__,
            "traceback": full_traceback,
            "progress": tracker.get_summary()
        }, indent=2)
    
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logger.info(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")


@mcp.tool()
def redact_pdf_custom(
    pdf_path: str,
    exclude_items: Optional[List[str]] = None,
    include_items: Optional[List[str]] = None,
    model: str = "gemma3:1b",
    auto_open: bool = True,
    return_base64: bool = False
) -> str:
    """
    Create a custom redacted PDF with user-specified exclusions and additions.
    
    This tool allows you to modify redactions after reviewing the initial result:
    - EXCLUDE items that shouldn't be redacted (false positives)
    - INCLUDE additional items that should be redacted (missed by LLM)
    
    Always starts from the ORIGINAL PDF to ensure clean redaction.
    When auto_open is True, opens BOTH the original and redacted PDFs side-by-side.
    
    Args:
        pdf_path: Path to the ORIGINAL PDF (not a redacted version)
        exclude_items: List of exact strings to NOT redact (e.g., ["John Doe", "john@email.com"])
        include_items: List of exact strings to forcefully redact (e.g., ["Secret Project", "XYZ Corp"])
        model: Ollama model to use for detection (default: "gemma3:1b")
               Use list_available_models() to see all available models.
               Note: Larger models = more accurate but slower processing
        auto_open: If true, automatically opens BOTH original and redacted PDFs
        return_base64: If true, return PDFs as base64
    
    Returns:
        JSON string with updated redacted PDF and summary
        
    Example:
        User sees first redaction and says: "Don't redact my name, but DO redact 'Google'"
        Call: redact_pdf_custom(
            pdf_path="resume.pdf",
            exclude_items=["Atharv Sabde"],
            include_items=["Google", "Confidential Project"],
            model="llama3.2:3b"  # Choose any available model
        )
    """
    tracker = ProgressTracker()
    
    try:
        tracker.add_step("Custom Redaction Setup", "in_progress", f"Using model: {model}")
        
        # Validate inputs
        if not pdf_path or not os.path.exists(pdf_path):
            tracker.fail_step("Custom Redaction Setup", f"PDF not found: {pdf_path}")
            return json.dumps({
                "error": f"PDF file not found: {pdf_path}",
                "progress": tracker.get_summary()
            }, indent=2)
        
        exclude_items = exclude_items or []
        include_items = include_items or []
        
        tracker.complete_step("Custom Redaction Setup", 
                             f"Exclude: {len(exclude_items)} items, Include: {len(include_items)} items")
        
        # Step 1: Initialize LLM
        tracker.add_step("Initialization", "in_progress")
        llm_instance = get_llm(model=model)
        
        if not llm_instance.check_connection():
            tracker.fail_step("Initialization", "Cannot connect to Ollama")
            return json.dumps({
                "error": "Cannot connect to Ollama",
                "progress": tracker.get_summary()
            }, indent=2)
        
        tracker.complete_step("Initialization", f"LLM ready with {model}")
        
        # Step 2: Extract text
        tracker.add_step("Text Extraction", "in_progress")
        text = get_pdf_text(pdf_path)
        tracker.complete_step("Text Extraction", f"Extracted {len(text)} characters")
        
        # Step 3: Detect sensitive data
        tracker.add_step("Sensitive Data Detection", "in_progress", f"Running LLM analysis with {model}")
        sensitive_data = llm_instance.get_sensitive_data(text)
        
        if not sensitive_data or (isinstance(sensitive_data, dict) and len(sensitive_data) == 0):
            tracker.fail_step("Sensitive Data Detection", "LLM returned empty result")
            return json.dumps({
                "error": "LLM failed to analyze document",
                "progress": tracker.get_summary()
            }, indent=2)
        
        tracker.complete_step("Sensitive Data Detection", "Analysis complete")
        
        # Step 4: Process and apply user preferences
        tracker.add_step("Applying User Preferences", "in_progress")
        
        # Get all detected values
        sensitive_values = post_process_sensitive_data(sensitive_data)
        
        # Remove excluded items (case-insensitive)
        excluded_count = 0
        if exclude_items:
            exclude_lower = [item.lower() for item in exclude_items]
            original_count = len(sensitive_values)
            sensitive_values = [v for v in sensitive_values if v.lower() not in exclude_lower]
            excluded_count = original_count - len(sensitive_values)
        
        # Add included items
        included_count = 0
        if include_items:
            for item in include_items:
                if item and item not in sensitive_values:
                    sensitive_values.append(item)
                    included_count += 1
        
        tracker.complete_step("Applying User Preferences", 
                             f"Excluded {excluded_count}, Added {included_count}")
        
        if len(sensitive_values) == 0:
            tracker.add_step("Validation", "completed", "No items to redact after filtering")
            return json.dumps({
                "status": "no_sensitive_data",
                "message": "No items to redact after applying your preferences",
                "excluded_count": excluded_count,
                "included_count": included_count,
                "model_used": model,
                "progress": tracker.get_summary()
            }, indent=2)
        
        # Step 5: Apply redactions
        tracker.add_step("PDF Redaction", "in_progress", 
                        f"Redacting {len(sensitive_values)} values")
        redaction_summary, highlighted_path = apply_redactions(pdf_path, sensitive_values)
        tracker.complete_step("PDF Redaction", 
                             f"Redacted {redaction_summary['total_redactions']} instances")
        
        # Step 6: Create report
        tracker.add_step("Creating Report", "in_progress")
        masked_data = mask_sensitive_data(sensitive_data)
        tracker.complete_step("Creating Report", "Report ready")
        
        # Step 7: Auto-open PDFs if requested
        if auto_open and not return_base64:
            # First open the original for comparison
            tracker.add_step("Opening Original PDF", "in_progress", "Opening original for comparison")
            opened_original = open_pdf(pdf_path)
            if opened_original:
                tracker.complete_step("Opening Original PDF", "Original opened")
            else:
                tracker.fail_step("Opening Original PDF", "Could not open original")
            
            # Then open the redacted version
            tracker.add_step("Opening Redacted PDF", "in_progress", "Opening redacted PDF")
            opened_redacted = open_pdf(redaction_summary["redacted_pdf_path"])
            if opened_redacted:
                tracker.complete_step("Opening Redacted PDF", "Redacted opened")
            else:
                tracker.fail_step("Opening Redacted PDF", "Could not open redacted")
        
        # Step 8: Prepare output
        tracker.add_step("Output Preparation", "in_progress")
        
        if return_base64:
            redacted_base64 = file_to_base64(redaction_summary["redacted_pdf_path"])
            highlighted_base64 = file_to_base64(highlighted_path)
            
            result = {
                "status": "success",
                "mode": "custom",
                "total_redactions": redaction_summary["total_redactions"],
                "total_pages": redaction_summary["total_pages"],
                "user_modifications": {
                    "excluded_count": excluded_count,
                    "included_count": included_count,
                    "final_item_count": len(sensitive_values)
                },
                "masked_data": masked_data,
                "model_used": model,
                "redacted_pdf_base64": redacted_base64,
                "highlighted_pdf_base64": highlighted_base64,
                "message": f"Custom redaction complete: {redaction_summary['total_redactions']} instances using {model}",
                "progress": tracker.get_summary()
            }
        else:
            result = {
                "status": "success",
                "mode": "custom",
                "total_redactions": redaction_summary["total_redactions"],
                "total_pages": redaction_summary["total_pages"],
                "user_modifications": {
                    "excluded_count": excluded_count,
                    "included_count": included_count,
                    "final_item_count": len(sensitive_values)
                },
                "masked_data": masked_data,
                "model_used": model,
                "redacted_pdf_path": redaction_summary["redacted_pdf_path"],
                "highlighted_pdf_path": highlighted_path,
                "pdf_opened": auto_open,
                "message": f"Custom redaction complete: {redaction_summary['total_redactions']} instances using {model}",
                "progress": tracker.get_summary()
            }
        
        tracker.complete_step("Output Preparation", "Complete")
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in redact_pdf_custom: {error_msg}", exc_info=True)
        
        import traceback
        full_traceback = traceback.format_exc()
        
        tracker.fail_step("Custom Redaction", error_msg)
        
        return json.dumps({
            "error": error_msg,
            "error_type": type(e).__name__,
            "traceback": full_traceback,
            "progress": tracker.get_summary()
        }, indent=2)


if __name__ == "__main__":
    mcp.run()