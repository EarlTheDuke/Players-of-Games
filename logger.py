"""Logging utilities for game moves and AI reasoning."""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class GameLogger:
    """Logger for game moves, reasoning, and results."""
    
    def __init__(self, game_type: str, log_to_file: bool = True):
        """
        Initialize the game logger.
        
        Args:
            game_type: Type of game being logged (e.g., 'chess', 'tictactoe')
            log_to_file: Whether to save logs to file
        """
        self.game_type = game_type
        self.log_to_file = log_to_file
        self.game_history = []
        self.start_time = datetime.now()
        
        if log_to_file:
            self.log_dir = "logs"
            os.makedirs(self.log_dir, exist_ok=True)
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.log_dir, f"{game_type}_{timestamp}.json")
    
    def log_move(self, player: str, move: str, reasoning: str, 
                 game_state: str, move_number: int, is_valid: bool = True):
        """
        Log a player's move with reasoning.
        
        Args:
            player: Player identifier (e.g., 'grok', 'claude')
            move: The move made
            reasoning: AI's reasoning for the move
            game_state: Current game state representation
            move_number: Move number in the game
            is_valid: Whether the move was valid
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "move_number": move_number,
            "player": player,
            "move": move,
            "reasoning": reasoning,
            "game_state": game_state,
            "is_valid": is_valid
        }
        
        self.game_history.append(log_entry)
        
        # Console output
        status = "✓" if is_valid else "✗"
        print(f"\n{status} Move {move_number} - {player.upper()}")
        print(f"Move: {move}")
        print(f"Reasoning: {reasoning}")
        if not is_valid:
            print("⚠️  Invalid move!")
    
    def log_game_start(self, players: Dict[str, Dict], initial_state: str):
        """
        Log the start of a game.
        
        Args:
            players: Dictionary of player configurations
            initial_state: Initial game state
        """
        start_info = {
            "timestamp": datetime.now().isoformat(),
            "event": "game_start",
            "game_type": self.game_type,
            "players": players,
            "initial_state": initial_state
        }
        
        self.game_history.append(start_info)
        
        print(f"\n🎮 Starting {self.game_type.upper()} game")
        print(f"Players: {list(players.keys())}")
        print("=" * 50)
    
    def log_game_end(self, result: str, winner: Optional[str] = None, 
                     final_state: str = "", total_moves: int = 0):
        """
        Log the end of a game.
        
        Args:
            result: Game result (e.g., 'win', 'draw', 'error')
            winner: Winner if applicable
            final_state: Final game state
            total_moves: Total number of moves played
        """
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        end_info = {
            "timestamp": end_time.isoformat(),
            "event": "game_end",
            "result": result,
            "winner": winner,
            "final_state": final_state,
            "total_moves": total_moves,
            "duration_seconds": duration.total_seconds()
        }
        
        self.game_history.append(end_info)
        
        print("\n" + "=" * 50)
        print(f"🏁 Game ended: {result.upper()}")
        if winner:
            print(f"🏆 Winner: {winner.upper()}")
        print(f"⏱️  Duration: {duration}")
        print(f"📊 Total moves: {total_moves}")
        
        if self.log_to_file:
            self._save_to_file()
    
    def log_error(self, error_type: str, message: str, context: Dict = None):
        """
        Log an error that occurred during the game.
        
        Args:
            error_type: Type of error
            message: Error message
            context: Additional context information
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "error_type": error_type,
            "message": message,
            "context": context or {}
        }
        
        self.game_history.append(error_entry)
        
        print(f"\n❌ Error ({error_type}): {message}")
    
    def _save_to_file(self):
        """Save the game history to a JSON file."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.game_history, f, indent=2, ensure_ascii=False)
            print(f"📝 Game log saved to: {self.log_file}")
        except Exception as e:
            print(f"Failed to save log file: {e}")
    
    def get_game_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the game.
        
        Returns:
            Dictionary containing game summary statistics
        """
        moves = [entry for entry in self.game_history if 'move' in entry]
        valid_moves = [move for move in moves if move.get('is_valid', True)]
        invalid_moves = [move for move in moves if not move.get('is_valid', True)]
        
        summary = {
            "game_type": self.game_type,
            "total_moves": len(moves),
            "valid_moves": len(valid_moves),
            "invalid_moves": len(invalid_moves),
            "players": list(set(move['player'] for move in moves)),
            "duration": (datetime.now() - self.start_time).total_seconds()
        }
        
        return summary
    
    def export_pgn(self, filename: Optional[str] = None) -> str:
        """
        Export chess game to PGN format (chess games only).
        
        Args:
            filename: Optional filename for PGN file
            
        Returns:
            PGN string
        """
        if self.game_type != 'chess':
            raise ValueError("PGN export is only available for chess games")
        
        moves = [entry for entry in self.game_history 
                if 'move' in entry and entry.get('is_valid', True)]
        
        # PGN header
        pgn_lines = [
            f'[Event "AI vs AI - Players of Games"]',
            f'[Date "{self.start_time.strftime("%Y.%m.%d")}"]',
            f'[White "{moves[0]["player"] if moves else "Unknown"}"]',
            f'[Black "{moves[1]["player"] if len(moves) > 1 else "Unknown"}"]',
            f'[Result "*"]',  # Will be updated when game ends
            ''
        ]
        
        # Moves in algebraic notation (simplified - would need chess library for proper conversion)
        move_pairs = []
        for i in range(0, len(moves), 2):
            move_num = (i // 2) + 1
            white_move = moves[i]['move'] if i < len(moves) else ''
            black_move = moves[i + 1]['move'] if i + 1 < len(moves) else ''
            
            if black_move:
                move_pairs.append(f"{move_num}. {white_move} {black_move}")
            elif white_move:
                move_pairs.append(f"{move_num}. {white_move}")
        
        pgn_lines.extend(move_pairs)
        pgn_content = '\n'.join(pgn_lines)
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(pgn_content)
                print(f"📋 PGN exported to: {filename}")
            except Exception as e:
                print(f"Failed to export PGN: {e}")
        
        return pgn_content
