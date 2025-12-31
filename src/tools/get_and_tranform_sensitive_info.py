import os
import fitz
import json
import re
import requests
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple


class OllamaLLM:
    """Wrapper for Ollama API to detect sensitive data."""
    
    def __init__(self, model: str = "gemma2:12b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        
    def get_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """
        Analyze text and return structured sensitive data.
        
        Returns:
            Dict with categories as keys and lists of sensitive values
        """
        prompt = f"""Analyze this text and identify ALL sensitive/personal data. Return ONLY a JSON object with these categories:
{{
  "names": ["list of person names"],
  "emails": ["list of email addresses"],
  "phones": ["list of phone numbers"],
  "addresses": ["list of physical addresses"],
  "ids": ["list of ID/SSN/passport numbers"],
  "cards": ["list of credit card numbers"],
  "dobs": ["list of dates of birth"],
  "medical": ["list of medical info"],
  "financial": ["list of financial info like account numbers"],
  "other_pii": ["list of other personal identifiable information"]
}}

Extract EXACT text as it appears. If a category has no items, use empty array [].

Text to analyze:
{text}

JSON object:"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1
                },
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                return self._extract_json(response_text)
            else:
                print(f"Ollama error: {response.status_code}")
                return {}
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return {}
    
    def _extract_json(self, response_text: str) -> Dict[str, List[str]]:
        """Extract and parse JSON from LLM response."""
        try:
            # Find JSON object
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                return data if isinstance(data, dict) else {}
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response preview: {response_text[:300]}")
            return {}


def get_pdf_text(file_path: str) -> str:
    """Extract all text from PDF."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def post_process_sensitive_data(sensitive_data: Dict[str, List[str]]) -> List[str]:
    """Flatten sensitive data dict into list of unique values."""
    all_values = []
    for category, values in sensitive_data.items():
        if isinstance(values, list):
            all_values.extend(values)
    # Remove duplicates while preserving order
    seen = set()
    unique_values = []
    for val in all_values:
        if val and val not in seen:
            seen.add(val)
            unique_values.append(val)
    return unique_values


def mask_sensitive_data(sensitive_data: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Create masked versions of sensitive data for reporting.
    Shows first 2 and last 2 characters, masks the middle.
    """
    masked_data = {}
    
    for category, values in sensitive_data.items():
        masked_values = []
        for value in values:
            if not isinstance(value, str) or len(value) < 3:
                masked_values.append(value)
                continue
                
            # Special handling for emails
            if '@' in value and '.' in value:
                try:
                    username, domain = value.split('@', 1)
                    if len(username) <= 2:
                        masked_username = '*' * len(username)
                    else:
                        masked_username = username[:2] + '*' * (len(username) - 2)
                    
                    domain_parts = domain.rsplit('.', 1)
                    if len(domain_parts) == 2:
                        domain_name, tld = domain_parts
                        if len(domain_name) <= 2:
                            masked_domain = '*' * len(domain_name)
                        else:
                            masked_domain = domain_name[:2] + '*' * (len(domain_name) - 2)
                        masked_value = f"{masked_username}@{masked_domain}.{tld}"
                    else:
                        masked_value = f"{masked_username}@{domain[:2]}***"
                except:
                    masked_value = value[:2] + '*' * (len(value) - 4) + value[-2:]
            
            # General masking: keep first 2 and last 2 chars
            elif len(value) <= 4:
                masked_value = '*' * len(value)
            else:
                masked_value = value[:2] + '*' * (len(value) - 4) + value[-2:]
            
            masked_values.append(masked_value)
        
        masked_data[category] = masked_values
    
    return masked_data


def apply_redactions(pdf_path: str, sensitive_values: List[str]) -> Tuple[Dict, str]:
    """
    Apply redactions to PDF and create highlighted version.
    
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
    
    print(f" Searching for {len(sensitive_values)} sensitive values across {len(doc_redacted)} pages...")
    
    for page_num, (page_redacted, page_highlighted) in enumerate(zip(doc_redacted, doc_highlighted), 1):
        page_stats = {
            "page": page_redacted.number + 1,
            "number_of_redactions": 0,
        }
        
        for sensitive_value in sensitive_values:
            if not sensitive_value or len(sensitive_value) < 2:
                continue
                
            # Search for exact matches (case-sensitive to avoid false positives)
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


def redact_pdf(pdf_path: str, llm: OllamaLLM) -> Tuple[Dict, str]:
    """
    Main function to redact sensitive data from PDF.
    
    Returns:
        Tuple of (redaction_summary, highlighted_path)
    """
    print(f"\nProcessing PDF: {pdf_path}")
    
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
    # Configuration
    PDF_PATH = r"C:\Users\atharv\Desktop\New folder\src\AtharvSabde_Resume.pdf"
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f" PDF not found: {PDF_PATH}")
        return
    
    # Check Ollama connection
    print(" Checking Ollama connection...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("Ollama is not responding. Start it with: ollama serve")
            return
        print("Connected to Ollama")
    except requests.exceptions.RequestException:
        print(" Cannot connect to Ollama. Make sure it's running: ollama serve")
        return
    
    # Initialize LLM
    llm = OllamaLLM(model="gemma3:12b")
    
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