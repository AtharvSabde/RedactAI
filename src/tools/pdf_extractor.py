"""
PDF text extraction utilities.
"""
import fitz
from pathlib import Path


def get_pdf_text(file_path: str, page_chunks: bool = False):
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        page_chunks: If True, return list of text per page; if False, return all text
        
    Returns:
        Either a single string of all text or a list of strings (one per page)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        doc = fitz.open(file_path)
        
        if page_chunks:
            texts = []
            for page in doc:
                page_text = page.get_text()
                texts.append(page_text)
            doc.close()
            return texts
        else:
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
            
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")
