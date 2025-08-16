# Players of Games 🎮

A Python application that pits AI models like Grok (from xAI) against Claude (from Anthropic) in various games including Chess and Tic-Tac-Toe. Watch as different AI models battle it out using strategic reasoning!

## Features

- **Multiple Games**: Currently supports Chess and Tic-Tac-Toe, with extensible architecture for more games
- **AI vs AI**: Grok and Claude models compete using API calls
- **Dual Interface**: Console mode for quick games, Streamlit web interface for interactive visualization
- **Comprehensive Logging**: Detailed logs of moves, reasoning, and game analysis
- **Chess Integration**: Full chess support with PGN export using python-chess library
- **Error Handling**: Robust error handling with fallback to random moves when AI fails
- **Position Analysis**: Basic game analysis and statistics

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd players-of-games

# Install dependencies
pip install -r requirements.txt
```

### 2. API Keys Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
GROK_API_KEY=your_grok_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

**Getting API Keys:**
- **Grok API**: Visit [x.ai](https://x.ai) to get your API key
- **Claude API**: Visit [console.anthropic.com](https://console.anthropic.com) to get your API key

### 3. Run Your First Game

**Console Mode (Quick):**
```bash
# Chess: Grok vs Claude
python main.py --game chess --player1 grok --player2 claude

# Tic-Tac-Toe: Claude vs Grok  
python main.py --game tictactoe --player1 claude --player2 grok

# Multiple games for statistics
python main.py --game chess --player1 grok --player2 claude --num-games 5
```

**Web Interface (Interactive):**
```bash
# Launch Streamlit web interface
python main.py --web
streamlit run main.py -- --web
```

## Usage Examples

### Console Mode

```bash
# Basic chess game
python main.py --game chess --player1 grok --player2 claude

# Multiple Tic-Tac-Toe games
python main.py --game tictactoe --player1 claude --player2 grok --num-games 10

# Disable file logging
python main.py --game chess --player1 grok --player2 claude --no-log
```

### Web Interface

The Streamlit interface provides:
- **Interactive Game Board**: Visual representation of the current game state
- **Real-time Move Log**: See AI reasoning for each move
- **Position Analysis**: Strategic insights and statistics
- **Game Controls**: Start new games, advance moves, or auto-play
- **Multiple Game Support**: Switch between Chess and Tic-Tac-Toe

Launch with: `python main.py --web`

## Project Structure

```
players_of_games/
├── main.py              # Entry point: CLI and Streamlit interface
├── config.py            # Configuration and API settings
├── api_utils.py         # API calling utilities for Grok and Claude
├── logger.py            # Game logging and history management
├── games/
│   ├── __init__.py
│   ├── base_game.py     # Abstract base class for all games
│   ├── chess_game.py    # Chess implementation using python-chess
│   └── tictactoe_game.py # Tic-Tac-Toe implementation
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## How It Works

### Game Flow
1. **Initialize**: Create game instance with specified AI players
2. **Game Loop**: 
   - Generate context-aware prompt for current player
   - Call AI API (Grok or Claude) with game state and legal moves
   - Parse AI response to extract move and reasoning
   - Validate move and apply to game state
   - Log move and reasoning
   - Switch to next player
3. **End Game**: Determine winner, log results, export game data

### AI Integration
- **Prompts**: Contextual prompts include current game state, legal moves, and instructions
- **Parsing**: Regex-based parsing to extract moves from natural language responses
- **Error Handling**: Retry logic with exponential backoff, fallback to random legal moves
- **Reasoning**: Extract and log AI's strategic reasoning for each move

### Extensibility
Adding new games is straightforward:
1. Create new game class inheriting from `BaseGame`
2. Implement abstract methods for game logic
3. Add prompt templates to `config.py`
4. Update main.py to include the new game

## Game Details

### Chess
- Full chess rules using `python-chess` library
- FEN notation for game states
- UCI notation for moves
- PGN export for game analysis
- Position analysis (material, mobility, king safety)

### Tic-Tac-Toe
- 3x3 grid implementation
- Coordinate-based moves (row,col)
- Win condition detection
- Strategic analysis (center control, winning opportunities)

## Configuration

### API Settings
- **Models**: Configurable model names in `config.py`
- **Endpoints**: API endpoints for both services
- **Timeouts**: Request timeout and retry settings
- **Rate Limiting**: Built-in retry logic with exponential backoff

### Game Settings
- **Prompts**: Customizable prompt templates for each game
- **Logging**: Configurable logging levels and output formats
- **Analysis**: Optional position analysis and statistics

## Logging and Analysis

### Game Logs
- **JSON Format**: Structured logs with timestamps and metadata
- **Move History**: Complete record of moves and AI reasoning
- **Error Tracking**: Detailed error logs and recovery actions
- **Statistics**: Game duration, move counts, and outcomes

### Export Formats
- **Chess PGN**: Standard chess game notation
- **JSON Logs**: Complete game history and analysis
- **Statistics**: Win/loss records and performance metrics

## Troubleshooting

### Common Issues

**Missing API Keys**
```
❌ Missing required API keys: GROK_API_KEY, CLAUDE_API_KEY
```
Solution: Create `.env` file with your API keys (see setup section)

**API Rate Limits**
```
API call attempt 1 failed: 429 Too Many Requests
```
Solution: The system includes automatic retry with exponential backoff

**Invalid Moves**
```
⚠️ Invalid move!
```
Solution: System automatically retries up to 3 times, then uses random legal move

**Module Import Errors**
```
ModuleNotFoundError: No module named 'chess'
```
Solution: Install dependencies with `pip install -r requirements.txt`

### Debug Mode
Enable detailed logging by modifying the logger configuration in `logger.py`.

## Contributing

### Adding New Games
1. Create new game class in `games/` directory
2. Inherit from `BaseGame` and implement required methods
3. Add prompt templates to `config.py`
4. Update `main.py` to include new game option
5. Add tests for the new game

### Example: Adding Connect Four
```python
# games/connect_four.py
from .base_game import BaseGame

class ConnectFourGame(BaseGame):
    def __init__(self, players, log_to_file=True):
        super().__init__(players, log_to_file)
        self.board = [[' ' for _ in range(7)] for _ in range(6)]
        # ... implement game logic
```

## Future Enhancements

- **More Games**: Connect Four, Checkers, Go (simple versions)
- **Tournament Mode**: Round-robin tournaments with multiple AIs
- **Advanced Analysis**: Integration with chess engines for position evaluation
- **Web Dashboard**: Enhanced statistics and game analysis
- **Model Comparison**: A/B testing different AI models and prompts
- **Multiplayer**: Human vs AI modes

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- **python-chess**: Excellent chess library by Niklas Fiekas
- **Streamlit**: Great framework for quick web interfaces
- **xAI**: For providing the Grok API
- **Anthropic**: For providing the Claude API

---

**Have fun watching AIs battle it out!** 🤖⚔️🤖
