"""
PDF redaction functionality.
"""
import fitz
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple


def apply_redactions(pdf_path: str, sensitive_values: List[str]) -> Tuple[Dict, str]:
    """
    Apply redactions to PDF and create highlighted version.
    
    Args:
        pdf_path: Path to input PDF
        sensitive_values: List of sensitive strings to redact
        
    Returns:
        Tuple of (redaction_summary, highlighted_path)
    """
    doc_redacted = fitz.open(pdf_path)
    doc_highlighted = fitz.open(pdf_path)
    
    redaction_summary = {
        "total_pages": len(doc_redacted),
        "redacted_pages": [],
        "total_redactions": 0
    }
    
    print(f"Searching for {len(sensitive_values)} sensitive values across {len(doc_redacted)} pages...")
    
    for page_num, (page_redacted, page_highlighted) in enumerate(zip(doc_redacted, doc_highlighted), 1):
        page_stats = {
            "page": page_redacted.number + 1,
            "number_of_redactions": 0,
        }
        
        for sensitive_value in sensitive_values:
            if not sensitive_value or len(sensitive_value) < 2:
                continue
                
            # Search for exact matches
            text_instances = page_redacted.search_for(sensitive_value)
            
            for inst in text_instances:
                # Add highlight to preview document
                highlight = page_highlighted.add_highlight_annot(inst)
                highlight.set_colors(stroke=[1, 1, 0])  # Yellow highlight
                highlight.update()
                
                # Add redaction to redacted document
                page_redacted.add_redact_annot(inst, fill=(0, 0, 0))  # Black redaction
            
            if text_instances:
                page_stats["number_of_redactions"] += len(text_instances)
        
        # Apply all redactions on this page
        page_redacted.apply_redactions()
        
        redaction_summary["redacted_pages"].append(page_stats)
        redaction_summary["total_redactions"] += page_stats["number_of_redactions"]
        
        if page_stats["number_of_redactions"] > 0:
            print(f"  Page {page_num}: {page_stats['number_of_redactions']} redaction(s)")
    
    # Save files
    try:
        base_path = Path(pdf_path)
        redacted_path = str(base_path.parent / f"{base_path.stem}_redacted.pdf")
        highlighted_path = str(base_path.parent / f"{base_path.stem}_highlighted.pdf")
        
        doc_redacted.save(redacted_path, garbage=4, deflate=True, clean=True)
        doc_highlighted.save(highlighted_path, garbage=4, deflate=True, clean=True)
        
    except Exception as e:
        print(f"Could not save to original directory: {e}")
        print("   Saving to temp directory instead...")
        
        with tempfile.NamedTemporaryFile(suffix='_redacted.pdf', delete=False) as temp_file:
            redacted_path = temp_file.name
        highlighted_path = redacted_path.replace("_redacted.pdf", "_highlighted.pdf")
        
        doc_redacted.save(redacted_path, garbage=4, deflate=True, clean=True)
        doc_highlighted.save(highlighted_path, garbage=4, deflate=True, clean=True)
    
    doc_redacted.close()
    doc_highlighted.close()
    
    redaction_summary["redacted_pdf_path"] = redacted_path
    redaction_summary["highlighted_pdf_path"] = highlighted_path
    
    return redaction_summary, highlighted_path

