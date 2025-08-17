"""Configuration settings for Players of Games."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration - Handle both local and Streamlit Cloud
try:
    import streamlit as st
    # Running in Streamlit Cloud - try both formats
    try:
        # Try direct key access first
        GROK_API_KEY = st.secrets["GROK_API_KEY"]
        CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]
    except KeyError:
        # Try nested format as backup
        GROK_API_KEY = st.secrets.get("grok", {}).get("api_key", os.getenv('GROK_API_KEY'))
        CLAUDE_API_KEY = st.secrets.get("claude", {}).get("api_key", os.getenv('CLAUDE_API_KEY'))
except ImportError:
    # Running locally
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
except Exception as e:
    # Fallback to environment variables
    print(f"Error loading secrets: {e}")
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# Model names - Updated for current API versions
GROK_MODEL = "grok-4"  # Updated to Grok 4
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# API Endpoints
GROK_ENDPOINT = "https://api.x.ai/v1/chat/completions"
CLAUDE_ENDPOINT = "https://api.anthropic.com/v1/messages"

# Default prompts
CHESS_PROMPT_TEMPLATE = """You are playing chess as {color}. 

Current board state (FEN): {fen}
Current board position:
{board_display}

Legal moves available: {legal_moves}

Please analyze the position and choose your next move. Respond with:
1. Your chosen move in UCI notation (e.g., "e2e4", "g1f3", "e7e8q" for promotion)
2. Brief reasoning for your choice

Format your response like this:
MOVE: [your_move_in_uci]
REASONING: [your_reasoning]
"""

TICTACTOE_PROMPT_TEMPLATE = """You are playing Tic-Tac-Toe as {symbol}.

Current board state:
{board_display}

Available moves: {legal_moves}

Choose your next move by specifying the row and column (0-2).
Format your response like this:
MOVE: [row],[col]
REASONING: [your_reasoning]
"""

# Game settings
MAX_RETRIES = 3
API_TIMEOUT = 60  # Increased timeout for better reliability
MAX_TOKENS = 500
