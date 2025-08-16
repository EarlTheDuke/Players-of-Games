"""Simple demo without external dependencies."""
import os
import sys
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any


class SimpleTicTacToe:
    """Simple Tic-Tac-Toe implementation for demo purposes."""
    
    def __init__(self):
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_player = 'X'
        self.players = {'X': 'Grok', 'O': 'Claude'}
        self.move_count = 0
    
    def display_board(self) -> str:
        """Display the current board state."""
        lines = []
        lines.append("  0   1   2")
        for i, row in enumerate(self.board):
            line = f"{i} "
            for j, cell in enumerate(row):
                display_cell = cell if cell != ' ' else ' '
                if j < 2:
                    line += f"{display_cell} | "
                else:
                    line += display_cell
            lines.append(line)
            if i < 2:
                lines.append("  ---------")
        return '\n'.join(lines)
    
    def get_legal_moves(self) -> List[str]:
        """Get all legal moves."""
        moves = []
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == ' ':
                    moves.append(f"{row},{col}")
        return moves
    
    def make_move(self, row: int, col: int) -> bool:
        """Make a move if valid."""
        if 0 <= row <= 2 and 0 <= col <= 2 and self.board[row][col] == ' ':
            self.board[row][col] = self.current_player
            self.move_count += 1
            return True
        return False
    
    def check_winner(self) -> Optional[str]:
        """Check for a winner."""
        # Check rows
        for row in self.board:
            if row[0] == row[1] == row[2] != ' ':
                return row[0]
        
        # Check columns
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != ' ':
                return self.board[0][col]
        
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != ' ':
            return self.board[0][0]
        
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != ' ':
            return self.board[0][2]
        
        return None
    
    def is_board_full(self) -> bool:
        """Check if board is full."""
        for row in self.board:
            for cell in row:
                if cell == ' ':
                    return False
        return True
    
    def is_game_over(self) -> bool:
        """Check if game is over."""
        return self.check_winner() is not None or self.is_board_full()
    
    def switch_player(self):
        """Switch to the other player."""
        self.current_player = 'O' if self.current_player == 'X' else 'X'


class SimpleLogger:
    """Simple logger for demo purposes."""
    
    def __init__(self):
        self.history = []
        self.start_time = datetime.now()
    
    def log(self, message: str, data: Dict = None):
        """Log a message with optional data."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'data': data or {}
        }
        self.history.append(entry)
        print(f"📝 {message}")


def simulate_ai_move(game: SimpleTicTacToe, player: str) -> Tuple[Optional[Tuple[int, int]], str]:
    """Simulate an AI move with simple strategy."""
    legal_moves = game.get_legal_moves()
    if not legal_moves:
        return None, "No legal moves available"
    
    # Simple AI strategy
    reasoning_templates = {
        'X': [
            "I'll take the center for strategic advantage",
            "Blocking opponent's potential win",
            "Taking a corner for better positioning",
            "This move sets up a potential winning line"
        ],
        'O': [
            "Responding to opponent's strategy",
            "Taking the best available position",
            "This move maintains balance in the game",
            "Preparing for a counter-attack"
        ]
    }
    
    # Priority moves: center, then corners, then edges
    priority_positions = ["1,1", "0,0", "0,2", "2,0", "2,2", "0,1", "1,0", "1,2", "2,1"]
    
    for pos in priority_positions:
        if pos in legal_moves:
            row, col = map(int, pos.split(','))
            reasoning = reasoning_templates[player][hash(pos) % len(reasoning_templates[player])]
            return (row, col), reasoning
    
    # Fallback to first legal move
    if legal_moves:
        row, col = map(int, legal_moves[0].split(','))
        return (row, col), "Taking the first available move"
    
    return None, "No moves available"


def demo_tic_tac_toe():
    """Demo a complete Tic-Tac-Toe game."""
    print("🎮 Players of Games - Simple Demo")
    print("=" * 50)
    print("🎯 Tic-Tac-Toe: Grok (X) vs Claude (O)")
    print("=" * 50)
    
    game = SimpleTicTacToe()
    logger = SimpleLogger()
    
    logger.log("Game started", {
        'players': game.players,
        'initial_board': game.display_board()
    })
    
    print("\nInitial board:")
    print(game.display_board())
    print()
    
    move_number = 1
    while not game.is_game_over():
        current_symbol = game.current_player
        current_player_name = game.players[current_symbol]
        
        print(f"Move {move_number}: {current_player_name} ({current_symbol})")
        
        # Get AI move
        move, reasoning = simulate_ai_move(game, current_symbol)
        
        if move is None:
            logger.log("No valid moves available", {'player': current_player_name})
            break
        
        row, col = move
        print(f"  Move: {row},{col}")
        print(f"  Reasoning: {reasoning}")
        
        # Apply move
        if game.make_move(row, col):
            logger.log("Move applied", {
                'player': current_player_name,
                'move': f"{row},{col}",
                'reasoning': reasoning,
                'move_number': move_number
            })
            
            print(f"\nBoard after move {move_number}:")
            print(game.display_board())
            print()
            
            game.switch_player()
            move_number += 1
        else:
            logger.log("Invalid move attempted", {
                'player': current_player_name,
                'move': f"{row},{col}"
            })
            break
    
    # Game over
    winner = game.check_winner()
    if winner:
        winner_name = game.players[winner]
        print(f"🏆 Game Over! Winner: {winner_name} ({winner})")
        logger.log("Game ended", {
            'result': 'win',
            'winner': winner_name,
            'total_moves': move_number - 1
        })
    elif game.is_board_full():
        print("🤝 Game Over! It's a draw!")
        logger.log("Game ended", {
            'result': 'draw',
            'total_moves': move_number - 1
        })
    else:
        print("❌ Game ended unexpectedly")
        logger.log("Game ended", {
            'result': 'error',
            'total_moves': move_number - 1
        })
    
    duration = datetime.now() - logger.start_time
    print(f"⏱️  Game duration: {duration}")
    print(f"📊 Total moves: {move_number - 1}")
    
    return logger.history


def demo_chess_concepts():
    """Demo chess concepts without the chess library."""
    print("\n🎮 Chess Concepts Demo")
    print("=" * 50)
    
    print("Chess game features (requires python-chess library):")
    print("✓ Full chess rules and move validation")
    print("✓ FEN notation for position representation")
    print("✓ UCI notation for moves (e.g., e2e4, g1f3)")
    print("✓ PGN export for game analysis")
    print("✓ Position analysis (material, king safety, etc.)")
    print()
    
    print("Example chess moves and reasoning:")
    chess_examples = [
        ("e2e4", "Control the center and open lines for piece development"),
        ("g1f3", "Develop knight toward the center, attacking e5"),
        ("f1c4", "Develop bishop, targeting the f7 weakness"),
        ("e1g1", "Castle kingside for king safety")
    ]
    
    for move, reasoning in chess_examples:
        print(f"  Move: {move}")
        print(f"  Reasoning: {reasoning}")
        print()


def demo_api_concepts():
    """Demo API interaction concepts."""
    print("🔌 API Integration Demo")
    print("=" * 50)
    
    print("How AI models are prompted:")
    print()
    
    # Example chess prompt
    print("📋 Example Chess Prompt:")
    print("-" * 30)
    chess_prompt = """You are playing chess as White.

Current board state (FEN): rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
Legal moves available: a2a3, a2a4, b2b3, b2b4, c2c3, c2c4, d2d3, d2d4, e2e3, e2e4...

Please analyze the position and choose your next move. Respond with:
1. Your chosen move in UCI notation (e.g., "e2e4")
2. Brief reasoning for your choice

Format your response like this:
MOVE: [your_move_in_uci]
REASONING: [your_reasoning]"""
    
    print(chess_prompt)
    print()
    
    print("📋 Example AI Response:")
    print("-" * 30)
    ai_response = """MOVE: e2e4
REASONING: This is a classical opening move that controls the center squares d5 and f5, 
opens lines for the bishop and queen, and follows opening principles of rapid development."""
    
    print(ai_response)
    print()
    
    # Example tic-tac-toe prompt
    print("📋 Example Tic-Tac-Toe Prompt:")
    print("-" * 30)
    ttt_prompt = """You are playing Tic-Tac-Toe as X.

Current board state:
  0   1   2
0   |   |  
  ---------
1   | X |  
  ---------
2   |   |  

Available moves: 0,0, 0,1, 0,2, 1,0, 1,2, 2,0, 2,1, 2,2

Choose your next move by specifying the row and column (0-2).
Format your response like this:
MOVE: [row],[col]
REASONING: [your_reasoning]"""
    
    print(ttt_prompt)
    print()


def demo_logging():
    """Demo logging functionality."""
    print("📝 Logging System Demo")
    print("=" * 50)
    
    print("Game logs include:")
    print("✓ Complete move history with timestamps")
    print("✓ AI reasoning for each move")
    print("✓ Game state after each move")
    print("✓ Error handling and recovery")
    print("✓ Game statistics and analysis")
    print("✓ Export to JSON and PGN formats")
    print()
    
    # Example log entry
    print("📋 Example Log Entry:")
    print("-" * 30)
    log_entry = {
        "timestamp": "2024-12-15T14:30:22.123456",
        "move_number": 1,
        "player": "grok",
        "move": "e2e4",
        "reasoning": "Control the center and open lines for development",
        "game_state": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "is_valid": True
    }
    
    print(json.dumps(log_entry, indent=2))


def main():
    """Run the simple demo."""
    print("🚀 Players of Games - Simple Demo")
    print("This demo shows core functionality without requiring external libraries.")
    print("For the full experience with AI APIs, follow the installation guide.")
    print("=" * 80)
    
    try:
        # Run Tic-Tac-Toe demo
        game_history = demo_tic_tac_toe()
        
        # Show other concepts
        demo_chess_concepts()
        demo_api_concepts()
        demo_logging()
        
        print("\n✅ Demo completed successfully!")
        print("\n🎯 Next Steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up API keys in .env file")
        print("3. Run: python main.py --game chess --player1 grok --player2 claude")
        print("4. Or try web interface: python main.py --web")
        print()
        print("📚 See QUICKSTART.md for detailed instructions")
        
        return game_history
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
