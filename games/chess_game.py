"""Chess game implementation using python-chess library."""
import chess
import chess.pgn
from typing import List, Optional, Tuple
from .base_game import BaseGame
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_utils import parse_chess_move
from config import CHESS_PROMPT_TEMPLATE
import io
from datetime import datetime


class ChessGame(BaseGame):
    """Chess game implementation."""
    
    def __init__(self, players: dict, log_to_file: bool = True):
        """
        Initialize chess game.
        
        Args:
            players: Dictionary mapping player names to model types
            log_to_file: Whether to log game to file
        """
        super().__init__(players, log_to_file)
        self.board = chess.Board()
        
        # Map players to colors
        self.player_colors = {}
        player_names = list(players.keys())
        self.player_colors[player_names[0]] = chess.WHITE
        self.player_colors[player_names[1]] = chess.BLACK
        
        # For PGN export
        self.moves_san = []
    
    def get_game_name(self) -> str:
        """Return the name of the game."""
        return "chess"
    
    def get_state_text(self) -> str:
        """Return FEN representation of the current board state."""
        return self.board.fen()
    
    def get_state_display(self) -> str:
        """Return a human-readable display of the current board."""
        return str(self.board)
    
    def get_legal_actions(self) -> List[str]:
        """Return list of legal moves in UCI notation."""
        return [str(move) for move in self.board.legal_moves]
    
    def is_game_over(self) -> bool:
        """Check if the chess game is over."""
        return self.board.is_game_over()
    
    def get_game_result(self) -> Tuple[str, Optional[str]]:
        """
        Get the chess game result.
        
        Returns:
            Tuple of (result_type, winner)
        """
        if not self.board.is_game_over():
            return "ongoing", None
        
        result = self.board.result()
        
        if result == "1-0":
            # White wins
            white_player = self._get_player_by_color(chess.WHITE)
            return "win", white_player
        elif result == "0-1":
            # Black wins
            black_player = self._get_player_by_color(chess.BLACK)
            return "win", black_player
        else:
            # Draw
            return "draw", None
    
    def _get_player_by_color(self, color: chess.Color) -> str:
        """Get player name by chess color."""
        for player, player_color in self.player_colors.items():
            if player_color == color:
                return player
        return "unknown"
    
    def _get_current_player_color(self) -> chess.Color:
        """Get the current player's chess color."""
        return self.player_colors[self.current_player]
    
    def validate_and_apply_action(self, action: str) -> bool:
        """
        Validate and apply a chess move.
        
        Args:
            action: UCI move string (e.g., "e2e4")
            
        Returns:
            True if move was valid and applied
        """
        try:
            # Clean the action string
            action = action.strip().lower()
            
            # Parse UCI move
            move = chess.Move.from_uci(action)
            
            # Debug logging
            print(f"DEBUG: Attempting move {action} for {self.current_player}")
            print(f"DEBUG: Current turn: {'White' if self.board.turn == chess.WHITE else 'Black'}")
            print(f"DEBUG: Move legal: {move in self.board.legal_moves}")
            print(f"DEBUG: Legal moves: {[str(m) for m in list(self.board.legal_moves)[:10]]}...")
            
            try:
                from debug_console import debug_log
                debug_log(f"Chess: Attempting {action} for {self.current_player}")
                debug_log(f"Chess: Turn={'White' if self.board.turn == chess.WHITE else 'Black'}, Legal={move in self.board.legal_moves}")
            except:
                pass
            
            # Check if move is legal
            if move in self.board.legal_moves:
                # Store move in SAN notation for PGN
                san_move = self.board.san(move)
                self.moves_san.append(san_move)
                
                # Apply the move
                self.board.push(move)
                print(f"DEBUG: Move {action} applied successfully")
                return True
            else:
                print(f"DEBUG: Move {action} is not legal in current position")
                return False
                
        except (ValueError, chess.InvalidMoveError) as e:
            print(f"DEBUG: Invalid move format {action}: {e}")
            return False
    
    def get_prompt(self) -> str:
        """Generate a chess prompt for the current player."""
        current_color = self._get_current_player_color()
        color_name = "White" if current_color == chess.WHITE else "Black"
        
        # Verify player turn matches board turn
        board_turn = "White" if self.board.turn == chess.WHITE else "Black"
        print(f"DEBUG: Player {self.current_player} ({color_name}) requesting move")
        print(f"DEBUG: Board expects {board_turn} to move")
        
        if color_name != board_turn:
            print(f"ERROR: Turn mismatch! Player is {color_name} but board expects {board_turn}")
            # Try to sync by switching the current player
            self.next_player()
            current_color = self._get_current_player_color()
            color_name = "White" if current_color == chess.WHITE else "Black"
            print(f"DEBUG: Switched to player {self.current_player} ({color_name})")
        
        legal_moves = self.get_legal_actions()
        
        # Limit the number of legal moves shown to avoid very long prompts
        if len(legal_moves) > 15:
            shown_moves = legal_moves[:15] + [f"... and {len(legal_moves) - 15} more moves"]
        else:
            shown_moves = legal_moves
        
        # Get fresh board state
        current_fen = self.get_state_text()
        current_board_display = self.get_state_display()
        move_number = self.board.fullmove_number
        
        # Debug: Log what we're showing the AI
        print(f"DEBUG: Showing AI - FEN: {current_fen}")
        print(f"DEBUG: Showing AI - Move #{move_number}, {color_name} to move")
        print(f"DEBUG: Showing AI - Legal moves: {shown_moves[:5]}...")
        
        try:
            from debug_console import debug_log
            debug_log(f"Prompt: {color_name} move #{move_number}, {len(shown_moves)} legal moves")
            debug_log(f"Prompt: FEN={current_fen}")
        except:
            pass
        
        # Enhanced prompt with clearer instructions
        enhanced_prompt = f"""You are playing chess as {color_name}.

CRITICAL: This is move #{move_number}. You are {color_name}. 

CURRENT POSITION (FEN): {current_fen}

CURRENT BOARD:
{current_board_display}

YOUR LEGAL MOVES (UCI format): {", ".join(shown_moves)}

ABSOLUTELY CRITICAL RULES:
1. You MUST choose EXACTLY one move from the legal moves list above
2. Do NOT make up moves - only use moves from the legal moves list
3. You are {color_name} - only move {color_name} pieces
4. Respond ONLY with a move in UCI format (e.g., e2e4, g1f3, not e1e2 unless it's in the legal moves)
5. This is move #{move_number} - the board has changed since move 1

Format your response exactly like this:
MOVE: [choose EXACTLY one from legal moves above]
REASONING: [brief explanation of your choice]

Your move:"""
        
        return enhanced_prompt
    
    def parse_action_from_response(self, response: str) -> Optional[str]:
        """Parse a UCI move from the AI's response."""
        parsed_move = parse_chess_move(response)
        
        # Debug: Show what we parsed
        print(f"DEBUG: AI Response: {response[:200]}...")
        print(f"DEBUG: Parsed move: {parsed_move}")
        print(f"DEBUG: Current FEN: {self.board.fen()}")
        print(f"DEBUG: Legal moves: {[str(m) for m in list(self.board.legal_moves)[:10]]}...")
        
        try:
            from debug_console import debug_log
            debug_log(f"Chess Parse: AI said '{parsed_move}' from response starting: {response[:50]}...")
            debug_log(f"Chess Parse: Current FEN: {self.board.fen()}")
        except:
            pass
        
        # Critical validation: Check if parsed move is in legal moves
        if parsed_move:
            legal_moves = [str(move) for move in self.board.legal_moves]
            if parsed_move not in legal_moves:
                print(f"ERROR: AI suggested illegal move '{parsed_move}' not in legal moves!")
                print(f"ERROR: Legal moves are: {legal_moves[:10]}...")
                try:
                    from debug_console import debug_log
                    debug_log(f"ERROR: Illegal move '{parsed_move}' suggested by AI")
                    debug_log(f"ERROR: Legal moves: {legal_moves[:5]}...")
                except:
                    pass
                return None  # Force retry with different prompt
        
        return parsed_move
    
    def get_game_info(self) -> dict:
        """Get detailed information about the current game state."""
        return {
            "fen": self.board.fen(),
            "turn": "White" if self.board.turn == chess.WHITE else "Black",
            "move_count": self.board.fullmove_number,
            "halfmove_clock": self.board.halfmove_clock,
            "is_check": self.board.is_check(),
            "is_checkmate": self.board.is_checkmate(),
            "is_stalemate": self.board.is_stalemate(),
            "is_insufficient_material": self.board.is_insufficient_material(),
            "can_claim_draw": self.board.can_claim_draw(),
            "legal_moves_count": len(list(self.board.legal_moves))
        }
    
    def export_pgn(self, filename: Optional[str] = None) -> str:
        """
        Export the game to PGN format.
        
        Args:
            filename: Optional filename to save PGN
            
        Returns:
            PGN string
        """
        # Create a new game
        game = chess.pgn.Game()
        
        # Set headers
        game.headers["Event"] = "AI vs AI - Players of Games"
        game.headers["Site"] = "Local"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        game.headers["Round"] = "1"
        
        # Set player names
        white_player = self._get_player_by_color(chess.WHITE)
        black_player = self._get_player_by_color(chess.BLACK)
        game.headers["White"] = f"{white_player} ({self.players[white_player]})"
        game.headers["Black"] = f"{black_player} ({self.players[black_player]})"
        
        # Set result
        if self.board.is_game_over():
            game.headers["Result"] = self.board.result()
        else:
            game.headers["Result"] = "*"
        
        # Add moves
        node = game
        temp_board = chess.Board()
        
        for san_move in self.moves_san:
            try:
                move = temp_board.parse_san(san_move)
                node = node.add_variation(move)
                temp_board.push(move)
            except ValueError:
                # Skip invalid moves
                continue
        
        # Convert to string
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
        pgn_string = game.accept(exporter)
        
        # Save to file if requested
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(pgn_string)
                print(f"📋 Chess PGN saved to: {filename}")
            except Exception as e:
                print(f"Failed to save PGN: {e}")
        
        return pgn_string
    
    def get_position_analysis(self) -> dict:
        """Get basic position analysis (requires additional libraries for deep analysis)."""
        analysis = {
            "material_balance": self._calculate_material_balance(),
            "piece_activity": self._analyze_piece_activity(),
            "king_safety": self._analyze_king_safety(),
            "center_control": self._analyze_center_control()
        }
        return analysis
    
    def _calculate_material_balance(self) -> dict:
        """Calculate material balance."""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        
        white_material = 0
        black_material = 0
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                value = piece_values.get(piece.piece_type, 0)
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value
        
        return {
            "white": white_material,
            "black": black_material,
            "balance": white_material - black_material
        }
    
    def _analyze_piece_activity(self) -> dict:
        """Analyze piece activity (simplified)."""
        white_mobility = len([move for move in self.board.legal_moves])
        
        # Switch turns to calculate black mobility
        self.board.push(chess.Move.null())
        black_mobility = len([move for move in self.board.legal_moves])
        self.board.pop()
        
        return {
            "white_mobility": white_mobility,
            "black_mobility": black_mobility
        }
    
    def _analyze_king_safety(self) -> dict:
        """Analyze king safety (simplified)."""
        white_king_square = self.board.king(chess.WHITE)
        black_king_square = self.board.king(chess.BLACK)
        
        return {
            "white_king_square": chess.square_name(white_king_square) if white_king_square else None,
            "black_king_square": chess.square_name(black_king_square) if black_king_square else None,
            "white_in_check": self.board.is_check() and self.board.turn == chess.WHITE,
            "black_in_check": self.board.is_check() and self.board.turn == chess.BLACK
        }
    
    def _analyze_center_control(self) -> dict:
        """Analyze center control (simplified)."""
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        white_control = 0
        black_control = 0
        
        for square in center_squares:
            piece = self.board.piece_at(square)
            if piece:
                if piece.color == chess.WHITE:
                    white_control += 1
                else:
                    black_control += 1
        
        return {
            "white_center_control": white_control,
            "black_center_control": black_control
        }
