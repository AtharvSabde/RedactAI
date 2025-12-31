# File: main.py
"""
Main entry point for PDF redaction tool.
"""
import os
import json
from ollama_llm import OllamaLLM
from pdf_extractor import get_pdf_text
from data_processor import post_process_sensitive_data, mask_sensitive_data
from pdf_redactor import apply_redactions


def redact_pdf(pdf_path: str, llm: OllamaLLM):
    """
    Main function to redact sensitive data from PDF.
    
    Args:
        pdf_path: Path to input PDF
        llm: OllamaLLM instance
        
    Returns:
        Tuple of (redaction_summary, highlighted_path)
    """
    print(f"\n Processing PDF: {pdf_path}")
    
    # Extract text
    print("Extracting text from PDF...")
    text = get_pdf_text(pdf_path)
    print(f"   Extracted {len(text)} characters")
    
    # Detect sensitive data
    print("Analyzing with Ollama (this may take a minute)...")
    sensitive_data = llm.get_sensitive_data(text)
    
    if not sensitive_data or all(len(v) == 0 for v in sensitive_data.values()):
        print("No sensitive data detected")
        return {"error": "No sensitive data found"}, None
    
    # Show what was found
    print("\n Sensitive data detected:")
    total_items = 0
    for category, values in sensitive_data.items():
        if values:
            print(f"   {category}: {len(values)} item(s)")
            total_items += len(values)
    
    # Flatten to list of values
    sensitive_values = post_process_sensitive_data(sensitive_data)
    print(f"\n Total unique sensitive values to redact: {len(sensitive_values)}")
    
    # Apply redactions
    print("\n Applying redactions to PDF...")
    redaction_summary, highlighted_path = apply_redactions(pdf_path, sensitive_values)
    
    # Create masked version for safe reporting
    masked_data = mask_sensitive_data(sensitive_data)
    redaction_summary["masked_sensitive_data"] = masked_data
    redaction_summary["raw_categories"] = {k: len(v) for k, v in sensitive_data.items() if v}
    
    print(f"\n Complete! Redacted {redaction_summary['total_redactions']} instances")
    print(f" Redacted PDF: {redaction_summary['redacted_pdf_path']}")
    print(f" Highlighted PDF: {highlighted_path}")
    
    return redaction_summary, highlighted_path


def main():
    """Main entry point."""
    # Configuration
    PDF_PATH = "ok_org_sensitised.pdf"
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f" PDF not found: {PDF_PATH}")
        return
    
    # Initialize LLM
    llm = OllamaLLM(model="gemma2:12b")
    
    # Check Ollama connection
    print("🔌 Checking Ollama connection...")
    if not llm.check_connection():
        print(" Cannot connect to Ollama. Make sure it's running: ollama serve")
        return
    print("Connected to Ollama")
    
    # Process PDF
    try:
        redaction_summary, highlighted_path = redact_pdf(PDF_PATH, llm)
        
        # Save summary as JSON
        summary_path = PDF_PATH.replace(".pdf", "_redaction_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(redaction_summary, f, indent=2)
        print(f"Summary saved: {summary_path}")
        
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()