"""Tic-Tac-Toe game implementation."""
from typing import List, Optional, Tuple
from .base_game import BaseGame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_utils import parse_tictactoe_move
from config import TICTACTOE_PROMPT_TEMPLATE


class TicTacToeGame(BaseGame):
    """Tic-Tac-Toe game implementation."""
    
    def __init__(self, players: dict, log_to_file: bool = True):
        """
        Initialize Tic-Tac-Toe game.
        
        Args:
            players: Dictionary mapping player names to model types
            log_to_file: Whether to log game to file
        """
        super().__init__(players, log_to_file)
        
        # Initialize 3x3 board with empty spaces
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        
        # Map players to symbols
        self.player_symbols = {}
        player_names = list(players.keys())
        self.player_symbols[player_names[0]] = 'X'
        self.player_symbols[player_names[1]] = 'O'
        
        # Track whose turn it is (X always goes first)
        self.current_symbol = 'X'
    
    def get_game_name(self) -> str:
        """Return the name of the game."""
        return "tictactoe"
    
    def get_state_text(self) -> str:
        """Return a compact text representation of the board state."""
        flat_board = []
        for row in self.board:
            flat_board.extend(row)
        return ''.join(flat_board)
    
    def get_state_display(self) -> str:
        """Return a human-readable display of the board."""
        display_lines = []
        display_lines.append("  0   1   2")
        for i, row in enumerate(self.board):
            display_row = f"{i} "
            for j, cell in enumerate(row):
                display_cell = cell if cell != ' ' else ' '
                if j < 2:
                    display_row += f"{display_cell} | "
                else:
                    display_row += display_cell
            display_lines.append(display_row)
            if i < 2:
                display_lines.append("  ---------")
        
        return '\n'.join(display_lines)
    
    def get_legal_actions(self) -> List[str]:
        """Return list of legal moves as "row,col" strings."""
        legal_moves = []
        for row in range(3):
            for col in range(3):
                if self.board[row][col] == ' ':
                    legal_moves.append(f"{row},{col}")
        return legal_moves
    
    def is_game_over(self) -> bool:
        """Check if the game is over."""
        # Check for winner
        winner = self._check_winner()
        if winner:
            return True
        
        # Check for draw (board full)
        return self._is_board_full()
    
    def get_game_result(self) -> Tuple[str, Optional[str]]:
        """
        Get the game result.
        
        Returns:
            Tuple of (result_type, winner)
        """
        winner_symbol = self._check_winner()
        
        if winner_symbol:
            # Find the player with the winning symbol
            for player, symbol in self.player_symbols.items():
                if symbol == winner_symbol:
                    return "win", player
        
        if self._is_board_full():
            return "draw", None
        
        return "ongoing", None
    
    def validate_and_apply_action(self, action: str) -> bool:
        """
        Validate and apply a Tic-Tac-Toe move.
        
        Args:
            action: Move in "row,col" format
            
        Returns:
            True if move was valid and applied
        """
        try:
            # Parse the action
            parts = action.split(',')
            if len(parts) != 2:
                return False
            
            row, col = int(parts[0].strip()), int(parts[1].strip())
            
            # Check bounds
            if not (0 <= row <= 2 and 0 <= col <= 2):
                return False
            
            # Check if cell is empty
            if self.board[row][col] != ' ':
                return False
            
            # Apply the move
            current_player_symbol = self.player_symbols[self.current_player]
            self.board[row][col] = current_player_symbol
            
            return True
            
        except (ValueError, IndexError):
            return False
    
    def get_prompt(self) -> str:
        """Generate a Tic-Tac-Toe prompt for the current player."""
        current_symbol = self.player_symbols[self.current_player]
        legal_moves = self.get_legal_actions()
        
        return TICTACTOE_PROMPT_TEMPLATE.format(
            symbol=current_symbol,
            board_display=self.get_state_display(),
            legal_moves=", ".join(legal_moves)
        )
    
    def parse_action_from_response(self, response: str) -> Optional[str]:
        """Parse a move from the AI's response."""
        parsed_move = parse_tictactoe_move(response)
        if parsed_move:
            row, col = parsed_move
            return f"{row},{col}"
        return None
    
    def _check_winner(self) -> Optional[str]:
        """
        Check if there's a winner.
        
        Returns:
            Winning symbol ('X' or 'O') or None if no winner
        """
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
    
    def _is_board_full(self) -> bool:
        """Check if the board is full."""
        for row in self.board:
            for cell in row:
                if cell == ' ':
                    return False
        return True
    
    def get_game_info(self) -> dict:
        """Get detailed information about the current game state."""
        winner_symbol = self._check_winner()
        winner_player = None
        
        if winner_symbol:
            for player, symbol in self.player_symbols.items():
                if symbol == winner_symbol:
                    winner_player = player
                    break
        
        return {
            "board_state": self.get_state_text(),
            "current_player": self.current_player,
            "current_symbol": self.player_symbols[self.current_player],
            "move_count": sum(1 for row in self.board for cell in row if cell != ' '),
            "legal_moves_count": len(self.get_legal_actions()),
            "winner": winner_player,
            "is_draw": self._is_board_full() and not winner_symbol,
            "game_over": self.is_game_over()
        }
    
    def get_position_analysis(self) -> dict:
        """Get basic position analysis for Tic-Tac-Toe."""
        analysis = {
            "center_control": self._analyze_center_control(),
            "corner_control": self._analyze_corner_control(),
            "winning_opportunities": self._count_winning_opportunities(),
            "blocking_needed": self._check_blocking_needed()
        }
        return analysis
    
    def _analyze_center_control(self) -> dict:
        """Analyze control of the center square."""
        center_piece = self.board[1][1]
        return {
            "center_occupied": center_piece != ' ',
            "center_owner": center_piece if center_piece != ' ' else None
        }
    
    def _analyze_corner_control(self) -> dict:
        """Analyze control of corner squares."""
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        x_corners = 0
        o_corners = 0
        
        for row, col in corners:
            piece = self.board[row][col]
            if piece == 'X':
                x_corners += 1
            elif piece == 'O':
                o_corners += 1
        
        return {
            "x_corners": x_corners,
            "o_corners": o_corners,
            "empty_corners": 4 - x_corners - o_corners
        }
    
    def _count_winning_opportunities(self) -> dict:
        """Count immediate winning opportunities for each player."""
        x_wins = 0
        o_wins = 0
        
        # Check all possible winning lines
        winning_lines = [
            # Rows
            [(0, 0), (0, 1), (0, 2)],
            [(1, 0), (1, 1), (1, 2)],
            [(2, 0), (2, 1), (2, 2)],
            # Columns
            [(0, 0), (1, 0), (2, 0)],
            [(0, 1), (1, 1), (2, 1)],
            [(0, 2), (1, 2), (2, 2)],
            # Diagonals
            [(0, 0), (1, 1), (2, 2)],
            [(0, 2), (1, 1), (2, 0)]
        ]
        
        for line in winning_lines:
            pieces = [self.board[row][col] for row, col in line]
            
            # Count X's and O's in this line
            x_count = pieces.count('X')
            o_count = pieces.count('O')
            empty_count = pieces.count(' ')
            
            # Check for winning opportunity (2 of same symbol + 1 empty)
            if x_count == 2 and empty_count == 1:
                x_wins += 1
            elif o_count == 2 and empty_count == 1:
                o_wins += 1
        
        return {
            "x_winning_moves": x_wins,
            "o_winning_moves": o_wins
        }
    
    def _check_blocking_needed(self) -> dict:
        """Check if blocking moves are needed."""
        opportunities = self._count_winning_opportunities()
        
        current_symbol = self.player_symbols[self.current_player]
        opponent_symbol = 'O' if current_symbol == 'X' else 'X'
        
        opponent_wins = (opportunities['o_winning_moves'] 
                        if opponent_symbol == 'O' 
                        else opportunities['x_winning_moves'])
        
        return {
            "opponent_can_win": opponent_wins > 0,
            "opponent_winning_moves": opponent_wins,
            "must_block": opponent_wins > 0
        }
