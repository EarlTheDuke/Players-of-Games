"""API utilities for calling Grok and Claude APIs."""
import requests
import json
import time
import re
import random
from typing import Optional, Dict, Any
from config import GROK_ENDPOINT, CLAUDE_ENDPOINT, API_TIMEOUT, MAX_RETRIES


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
    try:
        from debug_console import debug_log, DebugLevel
    except ImportError:
        debug_log = lambda *args, **kwargs: None
        DebugLevel = type('DebugLevel', (), {'API': 'API', 'ERROR': 'ERROR'})()
    
    if not api_key:
        debug_log(f"❌ GROK API ERROR: No API key provided", DebugLevel.ERROR, "API_ERROR")
        raise ValueError("Grok API key not provided")
    
    debug_log(f"🌐 GROK API START: Model={model}, Key={api_key[:10]}...", DebugLevel.API, "GROK_START")
    debug_log(f"🌐 Prompt length: {len(prompt)} chars", DebugLevel.API, "GROK_START")
    
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
            debug_log(f"🌐 GROK ATTEMPT {attempt + 1}/{MAX_RETRIES}: Calling {GROK_ENDPOINT}", 
                     DebugLevel.API, "GROK_ATTEMPT")
            
            import time
            start_time = time.time()
            
            response = requests.post(
                GROK_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            call_duration = time.time() - start_time
            
            debug_log(f"✅ GROK RESPONSE: Status={response.status_code}, Duration={call_duration:.2f}s", 
                     DebugLevel.API, "GROK_SUCCESS")
            
            response.raise_for_status()
            
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content']
                debug_log(f"✅ GROK SUCCESS: Content length={len(content)} chars", 
                         DebugLevel.API, "GROK_SUCCESS")
                debug_log(f"✅ GROK CONTENT PREVIEW: {content[:200]}...", 
                         DebugLevel.API, "GROK_SUCCESS")
                return content
            else:
                debug_log(f"❌ GROK FORMAT ERROR: Unexpected response format: {data}", 
                         DebugLevel.ERROR, "GROK_ERROR")
                return None
                
        except requests.exceptions.RequestException as e:
            call_duration = time.time() - start_time if 'start_time' in locals() else 0
            debug_log(f"❌ GROK ATTEMPT {attempt + 1} FAILED: {e} (Duration: {call_duration:.2f}s)", 
                     DebugLevel.ERROR, "GROK_ERROR")
            
            if hasattr(e, 'response') and e.response is not None:
                debug_log(f"❌ GROK HTTP ERROR: Status={e.response.status_code}", 
                         DebugLevel.ERROR, "GROK_ERROR")
                debug_log(f"❌ GROK ERROR CONTENT: {e.response.text[:500]}", 
                         DebugLevel.ERROR, "GROK_ERROR")
                
                # Check for specific error types
                if e.response.status_code == 400:
                    debug_log("❌ GROK 400: Bad Request - invalid model or request format", 
                             DebugLevel.ERROR, "GROK_ERROR")
                elif e.response.status_code == 401:
                    debug_log("❌ GROK 401: Unauthorized - check API key", 
                             DebugLevel.ERROR, "GROK_ERROR")
                elif e.response.status_code == 403:
                    debug_log("❌ GROK 403: Forbidden - API key lacks permission", 
                             DebugLevel.ERROR, "GROK_ERROR")
                elif e.response.status_code == 404:
                    debug_log("❌ GROK 404: Not Found - check endpoint URL", 
                             DebugLevel.ERROR, "GROK_ERROR")
                elif e.response.status_code == 429:
                    debug_log("❌ GROK 429: Rate Limited - too many requests", 
                             DebugLevel.ERROR, "GROK_ERROR")
                    
            if attempt < MAX_RETRIES - 1:
                debug_log(f"⏳ GROK RETRY: Backing off before attempt {attempt + 2}", 
                         DebugLevel.API, "GROK_RETRY")
                exponential_backoff(attempt)
            else:
                debug_log("❌ GROK FINAL FAILURE: All retry attempts exhausted", 
                         DebugLevel.ERROR, "GROK_FAILURE")
                return None
                
        except json.JSONDecodeError as e:
            debug_log(f"❌ GROK JSON ERROR: Failed to decode response: {e}", 
                     DebugLevel.ERROR, "GROK_ERROR")
            return None
        except Exception as e:
            debug_log(f"❌ GROK UNEXPECTED ERROR: {e}", 
                     DebugLevel.ERROR, "GROK_ERROR")
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
    try:
        from debug_console import debug_log, DebugLevel
    except ImportError:
        debug_log = lambda *args, **kwargs: None
        DebugLevel = type('DebugLevel', (), {'API': 'API', 'ERROR': 'ERROR'})()
    
    if not api_key:
        debug_log(f"❌ CLAUDE API ERROR: No API key provided", DebugLevel.ERROR, "API_ERROR")
        raise ValueError("Claude API key not provided")
    
    debug_log(f"🌐 CLAUDE API START: Model={model}, Key={api_key[:10]}...", DebugLevel.API, "CLAUDE_START")
    debug_log(f"🌐 Prompt length: {len(prompt)} chars", DebugLevel.API, "CLAUDE_START")
    
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
            debug_log(f"🌐 CLAUDE ATTEMPT {attempt + 1}/{MAX_RETRIES}: Calling {CLAUDE_ENDPOINT}", 
                     DebugLevel.API, "CLAUDE_ATTEMPT")
            
            import time
            start_time = time.time()
            
            response = requests.post(
                CLAUDE_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=API_TIMEOUT
            )
            
            call_duration = time.time() - start_time
            
            debug_log(f"✅ CLAUDE RESPONSE: Status={response.status_code}, Duration={call_duration:.2f}s", 
                     DebugLevel.API, "CLAUDE_SUCCESS")
            
            response.raise_for_status()
            
            data = response.json()
            if 'content' in data and len(data['content']) > 0:
                content = data['content'][0]['text']
                debug_log(f"✅ CLAUDE SUCCESS: Content length={len(content)} chars", 
                         DebugLevel.API, "CLAUDE_SUCCESS")
                debug_log(f"✅ CLAUDE CONTENT PREVIEW: {content[:200]}...", 
                         DebugLevel.API, "CLAUDE_SUCCESS")
                return content
            else:
                debug_log(f"❌ CLAUDE FORMAT ERROR: Unexpected response format: {data}", 
                         DebugLevel.ERROR, "CLAUDE_ERROR")
                return None
                
        except requests.exceptions.RequestException as e:
            call_duration = time.time() - start_time if 'start_time' in locals() else 0
            debug_log(f"❌ CLAUDE ATTEMPT {attempt + 1} FAILED: {e} (Duration: {call_duration:.2f}s)", 
                     DebugLevel.ERROR, "CLAUDE_ERROR")
            
            if hasattr(e, 'response') and e.response is not None:
                debug_log(f"❌ CLAUDE HTTP ERROR: Status={e.response.status_code}", 
                         DebugLevel.ERROR, "CLAUDE_ERROR")
                debug_log(f"❌ CLAUDE ERROR CONTENT: {e.response.text[:500]}", 
                         DebugLevel.ERROR, "CLAUDE_ERROR")
                
                # Check for specific error types
                if e.response.status_code == 400:
                    debug_log("❌ CLAUDE 400: Bad Request - invalid model or request format", 
                             DebugLevel.ERROR, "CLAUDE_ERROR")
                elif e.response.status_code == 401:
                    debug_log("❌ CLAUDE 401: Unauthorized - check API key", 
                             DebugLevel.ERROR, "CLAUDE_ERROR")
                elif e.response.status_code == 403:
                    debug_log("❌ CLAUDE 403: Forbidden - API key lacks permission", 
                             DebugLevel.ERROR, "CLAUDE_ERROR")
                elif e.response.status_code == 429:
                    debug_log("❌ CLAUDE 429: Rate Limited - too many requests", 
                             DebugLevel.ERROR, "CLAUDE_ERROR")
                    
            if attempt < MAX_RETRIES - 1:
                debug_log(f"⏳ CLAUDE RETRY: Backing off before attempt {attempt + 2}", 
                         DebugLevel.API, "CLAUDE_RETRY")
                exponential_backoff(attempt)
            else:
                debug_log("❌ CLAUDE FINAL FAILURE: All retry attempts exhausted", 
                         DebugLevel.ERROR, "CLAUDE_FAILURE")
                return None
                
        except json.JSONDecodeError as e:
            debug_log(f"❌ CLAUDE JSON ERROR: Failed to decode response: {e}", 
                     DebugLevel.ERROR, "CLAUDE_ERROR")
            return None
        except Exception as e:
            debug_log(f"❌ CLAUDE UNEXPECTED ERROR: {e}", 
                     DebugLevel.ERROR, "CLAUDE_ERROR")
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
