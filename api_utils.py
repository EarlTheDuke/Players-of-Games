"""API utilities for calling Grok and Claude APIs."""
import requests
import json
import time
import re
import random
from typing import Optional, Dict, Any
from config import GROK_ENDPOINT, CLAUDE_ENDPOINT, API_TIMEOUT, MAX_RETRIES

try:
    from error_logger import log_error, log_warning, log_info, ErrorCategory
except ImportError:
    # Fallback if error logger not available
    log_error = log_warning = log_info = lambda *args, **kwargs: None
    class ErrorCategory:
        API_ERROR = "API_ERROR"
        NETWORK = "NETWORK"
        PARSING = "PARSING"


def exponential_backoff(attempt: int) -> None:
    """Apply exponential backoff delay."""
    delay = (2 ** attempt) + random.uniform(0, 1)
    time.sleep(delay)


def call_grok(prompt: str, api_key: str, model: str = "grok-beta") -> Optional[str]:
    """
    Call the Grok API with the given prompt.
    
    Args:
        prompt: The prompt to send to Grok
        api_key: Grok API key
        model: Model name to use
    
    Returns:
        The response content or None if failed
    """
    if not api_key:
        raise ValueError("Grok API key not provided")
    
    print(f"DEBUG: Calling Grok API with key starting: {api_key[:10]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"DEBUG: Sending request to {GROK_ENDPOINT}")
            print(f"DEBUG: Payload: {payload}")
            
            response = requests.post(
                GROK_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
            else:
                print(f"Unexpected Grok API response format: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Grok API call attempt {attempt + 1} failed: {e}"
            print(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text[:500]}...")  # Show more content
                
                # Check for specific error types
                if e.response.status_code == 400:
                    print("ERROR: Bad Request - possibly invalid model name or request format")
                elif e.response.status_code == 401:
                    print("ERROR: Unauthorized - check API key")
                elif e.response.status_code == 403:
                    print("ERROR: Forbidden - API key may not have permission")
                elif e.response.status_code == 404:
                    print("ERROR: Not Found - check endpoint URL")
                elif e.response.status_code == 429:
                    print("ERROR: Rate Limited - too many requests")
                    
            if attempt < MAX_RETRIES - 1:
                exponential_backoff(attempt)
            else:
                print("All Grok API retry attempts failed")
                return None
        except json.JSONDecodeError as e:
            print(f"Failed to decode Grok API response: {e}")
            return None
    
    return None


def call_claude(prompt: str, api_key: str, model: str = "claude-3-5-sonnet-20241022") -> Optional[str]:
    """
    Call the Claude API with the given prompt.
    
    Args:
        prompt: The prompt to send to Claude
        api_key: Claude API key
        model: Model name to use
    
    Returns:
        The response content or None if failed
    """
    if not api_key:
        raise ValueError("Claude API key not provided")
    
    print(f"DEBUG: Calling Claude API with key starting: {api_key[:10]}...")
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": model,
        "max_tokens": 500,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"DEBUG: Sending request to {CLAUDE_ENDPOINT}")
            print(f"DEBUG: Payload: {payload}")
            
            response = requests.post(
                CLAUDE_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            data = response.json()
            if 'content' in data and len(data['content']) > 0:
                return data['content'][0]['text']
            else:
                print(f"Unexpected Claude API response format: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Claude API call attempt {attempt + 1} failed: {e}"
            print(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text[:200]}...")
            if attempt < MAX_RETRIES - 1:
                exponential_backoff(attempt)
            else:
                print("All Claude API retry attempts failed")
                return None
        except json.JSONDecodeError as e:
            print(f"Failed to decode Claude API response: {e}")
            return None
    
    return None


def parse_chess_move(response: str) -> Optional[str]:
    """
    Parse a chess move from an AI response, supporting both UCI and algebraic notation.
    
    Args:
        response: The AI response text
    
    Returns:
        UCI move string or None if not found
    """
    if not response:
        return None
    
    # Look for MOVE: prefix first - try UCI format
    uci_match = re.search(r'MOVE:\s*([a-h][1-8][a-h][1-8][qrbnQRBN]?)', response, re.IGNORECASE)
    if uci_match:
        return uci_match.group(1).lower()
    
    # Look for MOVE: prefix with algebraic notation (e.g., Nf3, Nbc6, O-O)
    algebraic_match = re.search(r'MOVE:\s*([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][=QRBN]?[+#]?|O-O-O|O-O)', response, re.IGNORECASE)
    if algebraic_match:
        algebraic_move = algebraic_match.group(1).strip()
        print(f"DEBUG: Found algebraic move: {algebraic_move}")
        # Return the algebraic move - it will be converted to UCI in the chess game validation
        return algebraic_move.lower()
    
    # Fallback: look for UCI pattern anywhere in response
    uci_pattern = r'\b([a-h][1-8][a-h][1-8][qrbnQRBN]?)\b'
    matches = re.findall(uci_pattern, response, re.IGNORECASE)
    if matches:
        return matches[0].lower()
    
    # Fallback: look for algebraic notation anywhere
    algebraic_pattern = r'\b([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][=QRBN]?[+#]?|O-O-O|O-O)\b'
    algebraic_matches = re.findall(algebraic_pattern, response, re.IGNORECASE)
    if algebraic_matches:
        algebraic_move = algebraic_matches[0].strip()
        print(f"DEBUG: Found algebraic move (fallback): {algebraic_move}")
        return algebraic_move.lower()
    
    return None


def parse_tictactoe_move(response: str) -> Optional[tuple]:
    """
    Parse a Tic-Tac-Toe move (row, col) from an AI response.
    
    Args:
        response: The AI response text
    
    Returns:
        (row, col) tuple or None if not found
    """
    if not response:
        return None
    
    # Look for MOVE: prefix first
    move_match = re.search(r'MOVE:\s*(\d),\s*(\d)', response)
    if move_match:
        row, col = int(move_match.group(1)), int(move_match.group(2))
        if 0 <= row <= 2 and 0 <= col <= 2:
            return (row, col)
    
    # Fallback: look for coordinate pattern anywhere
    coord_pattern = r'\b(\d),\s*(\d)\b'
    matches = re.findall(coord_pattern, response)
    for match in matches:
        row, col = int(match[0]), int(match[1])
        if 0 <= row <= 2 and 0 <= col <= 2:
            return (row, col)
    
    return None


def get_api_function(model_name: str):
    """
    Get the appropriate API function based on model name.
    
    Args:
        model_name: Name of the model ('grok' or 'claude')
    
    Returns:
        API function to call
    """
    if model_name.lower() == 'grok':
        return call_grok
    elif model_name.lower() == 'claude':
        return call_claude
    else:
        raise ValueError(f"Unknown model: {model_name}")


def extract_reasoning(response: str) -> str:
    """
    Extract reasoning from AI response.
    
    Args:
        response: The AI response text
    
    Returns:
        Reasoning text or full response if no specific reasoning found
    """
    if not response:
        return "No response received"
    
    reasoning_match = re.search(r'REASONING:\s*(.*?)(?:\n|$)', response, re.IGNORECASE | re.DOTALL)
    if reasoning_match:
        return reasoning_match.group(1).strip()
    
    return response.strip()
