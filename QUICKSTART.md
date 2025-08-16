# Quick Start Guide 🚀

Get up and running with Players of Games in 5 minutes!

## 1. Installation

### Option A: Automatic (Recommended)
```bash
# Windows
install.bat

# Linux/Mac
chmod +x install.sh
./install.sh
```

### Option B: Manual
```bash
pip install -r requirements.txt
```

## 2. API Keys Setup

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your keys:
# GROK_API_KEY=your_grok_api_key_here
# CLAUDE_API_KEY=your_claude_api_key_here
```

**Get API Keys:**
- **Grok**: Visit [x.ai](https://x.ai)
- **Claude**: Visit [console.anthropic.com](https://console.anthropic.com)

## 3. Try It Out!

### Demo (No API Keys Required)
```bash
python run_example.py
```

### Chess Game
```bash
python main.py --game chess --player1 grok --player2 claude
```

### Tic-Tac-Toe
```bash
python main.py --game tictactoe --player1 claude --player2 grok
```

### Web Interface
```bash
python main.py --web
```

## 4. Command Options

```bash
# Multiple games for statistics
python main.py --game chess --player1 grok --player2 claude --num-games 5

# Disable logging
python main.py --game chess --player1 grok --player2 claude --no-log

# Help
python main.py --help
```

## 5. What to Expect

- **Console Mode**: Real-time move-by-move gameplay with AI reasoning
- **Web Interface**: Visual board, live updates, position analysis
- **Logging**: Complete game history saved to JSON and PGN files
- **Error Handling**: Automatic retries and fallback to random moves

## Troubleshooting

**Missing API Keys?**
```
❌ Missing required API keys: GROK_API_KEY
```
→ Check your `.env` file

**Module Not Found?**
```
ModuleNotFoundError: No module named 'chess'
```
→ Run `pip install -r requirements.txt`

**API Errors?**
The system includes automatic retry logic, but check your API key validity.

## Example Output

```
🎮 Starting CHESS game
Players: ['player1', 'player2']
==================================================

✓ Move 1 - GROK
Move: e2e4
Reasoning: This move controls the center and opens lines for development.

✓ Move 2 - CLAUDE  
Move: e7e5
Reasoning: I'll respond symmetrically to maintain central control.

...

🏁 Game ended: WIN
🏆 Winner: GROK
⏱️  Duration: 0:02:45
📊 Total moves: 23
📝 Game log saved to: logs/chess_20241215_143022.json
📋 Chess PGN saved to: game_1_chess.pgn
```

**That's it! You're ready to watch AI models battle it out!** 🤖⚔️🤖
