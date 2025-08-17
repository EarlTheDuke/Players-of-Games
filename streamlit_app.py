"""Streamlit Cloud entry point for Players of Games."""
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main Streamlit app
from main import run_streamlit_app

if __name__ == "__main__":
    run_streamlit_app()
