"""
Utilities for processing and masking sensitive data.
"""
from typing import Dict, List


def post_process_sensitive_data(sensitive_data: Dict[str, List[str]]) -> List[str]:
    """
    Flatten sensitive data dict into list of unique values.
    
    Args:
        sensitive_data: Dict with categories and their values
        
    Returns:
        List of unique sensitive values
    """
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
    
    Args:
        sensitive_data: Dict with categories and their values
        
    Returns:
        Dict with masked values
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