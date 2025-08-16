"""Basic tests for Players of Games functionality."""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from games.chess_game import ChessGame
from games.tictactoe_game import TicTacToeGame
from api_utils import parse_chess_move, parse_tictactoe_move, extract_reasoning
from logger import GameLogger


class TestChessGame:
    """Test chess game functionality."""
    
    def test_chess_game_initialization(self):
        """Test chess game initializes correctly."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = ChessGame(players, log_to_file=False)
        
        assert game.get_game_name() == "chess"
        assert len(game.get_legal_actions()) == 20  # Starting position has 20 legal moves
        assert not game.is_game_over()
        assert game.get_state_text().startswith("rnbqkbnr")  # Starting FEN
    
    def test_chess_move_validation(self):
        """Test chess move validation."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = ChessGame(players, log_to_file=False)
        
        # Valid move
        assert game.validate_and_apply_action("e2e4") == True
        
        # Invalid move (piece doesn't exist)
        assert game.validate_and_apply_action("e5e6") == False
        
        # Invalid format
        assert game.validate_and_apply_action("invalid") == False
    
    def test_chess_game_state(self):
        """Test chess game state tracking."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = ChessGame(players, log_to_file=False)
        
        initial_fen = game.get_state_text()
        game.validate_and_apply_action("e2e4")
        new_fen = game.get_state_text()
        
        assert initial_fen != new_fen
        assert "e4" in new_fen or game.board.piece_at(28) is not None  # e4 square


class TestTicTacToeGame:
    """Test Tic-Tac-Toe game functionality."""
    
    def test_tictactoe_initialization(self):
        """Test Tic-Tac-Toe game initializes correctly."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = TicTacToeGame(players, log_to_file=False)
        
        assert game.get_game_name() == "tictactoe"
        assert len(game.get_legal_actions()) == 9  # All squares empty
        assert not game.is_game_over()
        assert game.get_state_text() == "         "  # Empty board
    
    def test_tictactoe_move_validation(self):
        """Test Tic-Tac-Toe move validation."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = TicTacToeGame(players, log_to_file=False)
        
        # Valid move
        assert game.validate_and_apply_action("1,1") == True
        
        # Invalid move (occupied square)
        assert game.validate_and_apply_action("1,1") == False
        
        # Invalid move (out of bounds)
        assert game.validate_and_apply_action("3,3") == False
        
        # Invalid format
        assert game.validate_and_apply_action("invalid") == False
    
    def test_tictactoe_win_detection(self):
        """Test Tic-Tac-Toe win detection."""
        players = {'player1': 'grok', 'player2': 'claude'}
        game = TicTacToeGame(players, log_to_file=False)
        
        # Create winning condition for X (player1)
        game.validate_and_apply_action("0,0")  # X
        game.next_player()
        game.validate_and_apply_action("1,0")  # O
        game.next_player()
        game.validate_and_apply_action("0,1")  # X
        game.next_player()
        game.validate_and_apply_action("1,1")  # O
        game.next_player()
        game.validate_and_apply_action("0,2")  # X wins (top row)
        
        assert game.is_game_over()
        result_type, winner = game.get_game_result()
        assert result_type == "win"
        assert winner == "player1"


class TestApiUtils:
    """Test API utility functions."""
    
    def test_parse_chess_move(self):
        """Test chess move parsing."""
        # With MOVE: prefix
        response1 = "MOVE: e2e4\nREASONING: Control the center"
        assert parse_chess_move(response1) == "e2e4"
        
        # Without prefix
        response2 = "I think e2e4 is a good move because it controls the center."
        assert parse_chess_move(response2) == "e2e4"
        
        # Promotion move
        response3 = "MOVE: e7e8q\nREASONING: Promote to queen"
        assert parse_chess_move(response3) == "e7e8q"
        
        # No valid move
        response4 = "I'm not sure what to do here."
        assert parse_chess_move(response4) is None
    
    def test_parse_tictactoe_move(self):
        """Test Tic-Tac-Toe move parsing."""
        # With MOVE: prefix
        response1 = "MOVE: 1,2\nREASONING: Block opponent"
        assert parse_tictactoe_move(response1) == (1, 2)
        
        # Without prefix
        response2 = "I'll play 0,1 to control the center."
        assert parse_tictactoe_move(response2) == (0, 1)
        
        # Invalid coordinates
        response3 = "MOVE: 3,3\nREASONING: Invalid move"
        assert parse_tictactoe_move(response3) is None
        
        # No valid move
        response4 = "I'm thinking about this position."
        assert parse_tictactoe_move(response4) is None
    
    def test_extract_reasoning(self):
        """Test reasoning extraction."""
        response1 = "MOVE: e2e4\nREASONING: This controls the center and opens lines for development."
        reasoning = extract_reasoning(response1)
        assert "controls the center" in reasoning.lower()
        
        response2 = "Just some general text without specific reasoning format."
        reasoning = extract_reasoning(response2)
        assert reasoning == response2.strip()


class TestGameLogger:
    """Test game logging functionality."""
    
    def test_logger_initialization(self):
        """Test logger initializes correctly."""
        logger = GameLogger("chess", log_to_file=False)
        assert logger.game_type == "chess"
        assert logger.game_history == []
    
    def test_log_move(self):
        """Test move logging."""
        logger = GameLogger("chess", log_to_file=False)
        
        logger.log_move(
            player="grok",
            move="e2e4",
            reasoning="Control the center",
            game_state="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            move_number=1
        )
        
        assert len(logger.game_history) == 1
        move_entry = logger.game_history[0]
        assert move_entry["player"] == "grok"
        assert move_entry["move"] == "e2e4"
        assert move_entry["reasoning"] == "Control the center"
    
    def test_game_summary(self):
        """Test game summary generation."""
        logger = GameLogger("chess", log_to_file=False)
        
        # Add some mock moves
        logger.log_move("grok", "e2e4", "Good move", "state1", 1, True)
        logger.log_move("claude", "e7e5", "Response", "state2", 2, True)
        logger.log_move("grok", "invalid", "Bad move", "state3", 3, False)
        
        summary = logger.get_game_summary()
        assert summary["total_moves"] == 3
        assert summary["valid_moves"] == 2
        assert summary["invalid_moves"] == 1
        assert "grok" in summary["players"]
        assert "claude" in summary["players"]


# Mock tests for API calls (since we don't want to make real API calls in tests)
class TestApiCalls:
    """Test API calling with mocks."""
    
    @patch('api_utils.requests.post')
    def test_grok_api_call_success(self, mock_post):
        """Test successful Grok API call."""
        from api_utils import call_grok
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'MOVE: e2e4\nREASONING: Good opening move'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_grok("Test prompt", "fake_api_key")
        assert result == 'MOVE: e2e4\nREASONING: Good opening move'
    
    @patch('api_utils.requests.post')
    def test_claude_api_call_success(self, mock_post):
        """Test successful Claude API call."""
        from api_utils import call_claude
        
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'content': [{'text': 'MOVE: 1,1\nREASONING: Control the center'}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_claude("Test prompt", "fake_api_key")
        assert result == 'MOVE: 1,1\nREASONING: Control the center'
    
    @patch('api_utils.requests.post')
    def test_api_call_failure(self, mock_post):
        """Test API call failure handling."""
        from api_utils import call_grok
        
        # Mock failed response
        mock_post.side_effect = Exception("Network error")
        
        result = call_grok("Test prompt", "fake_api_key")
        assert result is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
