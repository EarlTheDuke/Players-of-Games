#!/bin/bash
echo "Installing Players of Games..."
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

echo "Python found, installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

echo
echo "Installation completed successfully!"
echo
echo "Next steps:"
echo "1. Copy .env.example to .env and add your API keys"
echo "2. Run: python3 main.py --help for usage options"
echo "3. Try: python3 run_example.py for a demo without API keys"
echo

# Make the script executable
chmod +x install.sh
