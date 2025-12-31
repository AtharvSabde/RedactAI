"""
Ollama LLM wrapper for sensitive data detection 
Fixes:
1. Unicode encoding errors in Windows console
2. Robust JSON parsing with error recovery
3. Better prompt engineering for valid JSON
4. Fixed JSON-in-prompt issue - now uses plain string prompts
"""
import json
import re
import requests
from typing import Dict, List


class OllamaLLM:
    """Wrapper for Ollama API to detect sensitive data."""

    def __init__(
        self,
        model: str = "gemma3:1b",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url

    def get_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """
        Analyze text and return structured sensitive data.

        Args:
            text: Text to analyze

        Returns:
            Dict with categories as keys and lists of sensitive values
        """

        # Simplified prompt - let the schema handle the structure
        prompt = f"""Extract all sensitive and personal information from the following text. 
        
Categories to find:
- names: Full names of people
- emails: Email addresses
- phones: Phone numbers
- addresses: Physical addresses
- ids: ID numbers (SSN, passport, license, etc.)
- cards: Credit card numbers
- dobs: Dates of birth
- medical: Medical information
- financial: Financial information (account numbers, etc.)
- other_pii: Any other personally identifiable information

Text to analyze:
---
{text}
---"""

        # Define the exact JSON schema we want Ollama to return
        response_schema = {
            "type": "object",
            "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
                "emails": {"type": "array", "items": {"type": "string"}},
                "phones": {"type": "array", "items": {"type": "string"}},
                "addresses": {"type": "array", "items": {"type": "string"}},
                "ids": {"type": "array", "items": {"type": "string"}},
                "cards": {"type": "array", "items": {"type": "string"}},
                "dobs": {"type": "array", "items": {"type": "string"}},
                "medical": {"type": "array", "items": {"type": "string"}},
                "financial": {"type": "array", "items": {"type": "string"}},
                "other_pii": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["names", "emails", "phones", "addresses", "ids", "cards", "dobs", "medical", "financial", "other_pii"]
        }

        try:
            # FIXED: Using JSON schema format for guaranteed structure
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
                "format": response_schema,  # Schema ensures exact JSON structure
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300,
            )

            if response.status_code != 200:
                print(f"[ERROR] Ollama error: {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return self._empty_structure()

            result = response.json()
            response_text = result.get("response", "")

            # If Ollama already returned valid JSON
            if isinstance(response_text, dict):
                return self._validate_structure(response_text)

            # If JSON is returned as a string, parse it
            return self._extract_and_fix_json(response_text)

        except requests.exceptions.Timeout:
            print("[ERROR] LLM request timed out - try a faster model or smaller document")
            return self._empty_structure()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Connection error: {e}")
            return self._empty_structure()

        except Exception as e:
            print(f"[ERROR] Unexpected error in get_sensitive_data: {e}")
            return self._empty_structure()


    def _extract_and_fix_json(self, response_text: str) -> Dict[str, List[str]]:
        """
        Extract and parse JSON from LLM response with robust error recovery.
        Fixes common JSON formatting issues from LLMs.
        """
        try:
            # Step 1: Try direct JSON parse first (if model returned clean JSON)
            try:
                data = json.loads(response_text.strip())
                if isinstance(data, dict):
                    return self._validate_structure(data)
            except json.JSONDecodeError:
                pass  # Try extraction methods
            
            # Step 2: Extract JSON from markdown code blocks
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
            else:
                # Step 3: Find JSON object in response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                else:
                    print("[WARNING] No JSON object found in LLM response")
                    print(f"[INFO] Response preview: {response_text[:300]}...")
                    return self._empty_structure()
            
            # Step 4: Fix common JSON formatting errors
            json_str = self._fix_json_formatting(json_str)
            
            # Step 5: Parse the fixed JSON
            data = json.loads(json_str)
            
            if isinstance(data, dict):
                return self._validate_structure(data)
            else:
                print("[WARNING] LLM returned non-dict JSON")
                return self._empty_structure()
                
        except json.JSONDecodeError as e:
            print(f"[WARNING] JSON parse error: {e}")
            print(f"[INFO] Response preview: {response_text[:200]}...")
            return self._empty_structure()
        except Exception as e:
            print(f"[ERROR] Unexpected error in JSON extraction: {e}")
            return self._empty_structure()
    
    def _fix_json_formatting(self, json_str: str) -> str:
        """
        Fix common JSON formatting errors produced by LLMs.
        """
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix single quotes to double quotes (but be careful with apostrophes in text)
        # Only fix quotes around keys and at string boundaries
        json_str = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', json_str)  # Keys
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)    # Values
        
        # Remove any non-JSON text before first { or after last }
        first_brace = json_str.find('{')
        last_brace = json_str.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = json_str[first_brace:last_brace+1]
        
        return json_str
    
    def _validate_structure(self, data: Dict) -> Dict[str, List[str]]:
        """
        Ensure the JSON has all required keys with proper structure.
        """
        required_keys = [
            "names", "emails", "phones", "addresses", "ids",
            "cards", "dobs", "medical", "financial", "other_pii"
        ]
        
        validated = {}
        for key in required_keys:
            value = data.get(key, [])
            
            # Ensure it's a list
            if not isinstance(value, list):
                if isinstance(value, str):
                    validated[key] = [value] if value else []
                else:
                    validated[key] = []
            else:
                # Filter out non-string items and empty strings
                validated[key] = [str(item) for item in value if item and isinstance(item, (str, int, float))]
        
        return validated
    
    def _empty_structure(self) -> Dict[str, List[str]]:
        """Return empty structure when JSON extraction fails."""
        return {
            "names": [],
            "emails": [],
            "phones": [],
            "addresses": [],
            "ids": [],
            "cards": [],
            "dobs": [],
            "medical": [],
            "financial": [],
            "other_pii": []
        }
    
    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False