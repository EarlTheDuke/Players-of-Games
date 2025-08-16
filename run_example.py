"""Example script to demonstrate Players of Games functionality."""
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

from games.tictactoe_game import TicTacToeGame
from games.chess_game import ChessGame
from unittest.mock import Mock, patch


def mock_api_call(prompt, api_key, model=None):
    """Mock API call that returns a simple move."""
    if "chess" in prompt.lower() or "fen" in prompt.lower():
        # Return a basic chess move
        return "MOVE: e2e4\nREASONING: Control the center of the board."
    else:
        # Return a basic tic-tac-toe move
        return "MOVE: 1,1\nREASONING: Take the center square for strategic advantage."


def demo_tictactoe():
    """Demonstrate a Tic-Tac-Toe game with mocked API calls."""
    print("🎮 Demo: Tic-Tac-Toe Game")
    print("=" * 40)
    
    players = {'player1': 'grok', 'player2': 'claude'}
    game = TicTacToeGame(players, log_to_file=False)
    
    # Mock the API calls
    with patch('games.base_game.get_api_function') as mock_get_api:
        mock_get_api.return_value = mock_api_call
        
        # Play a few moves manually to demonstrate
        print("Initial board:")
        print(game.get_state_display())
        
        # Make some moves
        moves = ["1,1", "0,0", "0,1", "2,2", "2,1"]
        for i, move in enumerate(moves):
            if game.is_game_over():
                break
                
            current_player = game.current_player
            success = game.validate_and_apply_action(move)
            
            print(f"\nMove {i+1}: {current_player} plays {move}")
            print(f"Valid: {success}")
            print(game.get_state_display())
            
            if success:
                game.next_player()
        
        # Check game result
        if game.is_game_over():
            result_type, winner = game.get_game_result()
            print(f"\n🏁 Game Over! Result: {result_type}")
            if winner:
                print(f"🏆 Winner: {winner}")


def demo_chess_basics():
    """Demonstrate basic chess game functionality."""
    print("\n🎮 Demo: Chess Game Basics")
    print("=" * 40)
    
    players = {'white': 'grok', 'black': 'claude'}
    game = ChessGame(players, log_to_file=False)
    
    print("Initial position:")
    print(game.get_state_display())
    print(f"\nFEN: {game.get_state_text()}")
    print(f"Legal moves: {len(game.get_legal_actions())}")
    
    # Make a few moves
    moves = ["e2e4", "e7e5", "g1f3", "b8c6"]
    for move in moves:
        if game.validate_and_apply_action(move):
            print(f"\nAfter {move}:")
            print(game.get_state_display())
            game.next_player()
        else:
            print(f"Invalid move: {move}")
    
    # Show game info
    game_info = game.get_game_info()
    print(f"\nGame info:")
    for key, value in game_info.items():
        print(f"  {key}: {value}")


def demo_logging():
    """Demonstrate logging functionality."""
    print("\n📝 Demo: Logging System")
    print("=" * 40)
    
    from logger import GameLogger
    
    logger = GameLogger("demo", log_to_file=False)
    
    # Simulate some game events
    logger.log_game_start(
        players={'player1': 'grok', 'player2': 'claude'},
        initial_state="Initial game state"
    )
    
    logger.log_move(
        player="grok",
        move="e2e4",
        reasoning="This move controls the center and allows for piece development.",
        game_state="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        move_number=1
    )
    
    logger.log_move(
        player="claude",
        move="e7e5",
        reasoning="Responding in the center to maintain equality.",
        game_state="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
        move_number=2
    )
    
    logger.log_game_end(
        result="demo",
        winner=None,
        final_state="Demo completed",
        total_moves=2
    )
    
    # Show summary
    summary = logger.get_game_summary()
    print(f"\nGame summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def main():
    """Run all demos."""
    print("🚀 Players of Games - Demo Mode")
    print("This demo shows the core functionality without requiring API keys.")
    print("=" * 60)
    
    try:
        demo_tictactoe()
        demo_chess_basics()
        demo_logging()
        
        print("\n✅ Demo completed successfully!")
        print("\nTo run with real AI models:")
        print("1. Set up your API keys in .env file")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run: python main.py --game chess --player1 grok --player2 claude")
        print("4. Or try the web interface: python main.py --web")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
