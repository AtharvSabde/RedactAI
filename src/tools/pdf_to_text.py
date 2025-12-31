import fitz
from pathlib import Path
from typing import Union, List

def get_pdf_text(file_path: Union[str, Path], page_chunks: bool = False) -> Union[str, List[str]]:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        page_chunks: If True, return list of text per page; if False, return all text as single string
        
    Returns:
        Either a single string of all text or a list of strings (one per page)
        
    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        Exception: For other PDF processing errors
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    try:
        doc = fitz.open(file_path)
        
        if page_chunks:
            texts = []
            for page in doc:
                page_text = extract_page_text(page)
                texts.append(page_text)
            return texts
        else:
            text = ""
            for page in doc:
                text += extract_page_text(page)
            return text
            
    except Exception as e:
        raise Exception(f"Error processing PDF: {e}")
    finally:
        if 'doc' in locals():
            doc.close()

def extract_page_text(page) -> str:
    """Extract text from a single PDF page."""
    page_text = []
    
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                line_text = []
                for span in line.get("spans", []):
                    line_text.append(span["text"])
                if line_text:
                    page_text.append(" ".join(line_text))
    
    return "\n".join(page_text) + "\n"

if __name__ == "__main__":
    try:
        # Extract all text as single string
        text = get_pdf_text("ok_org_sensitised.pdf")
        
        
        # Extract text page by page
        pages = get_pdf_text("ok_org_sensitised.pdf", page_chunks=True)
        
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")