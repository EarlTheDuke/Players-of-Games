"""Chess game implementation using python-chess library."""
import chess
import chess.pgn
from typing import List, Optional, Tuple
from .base_game import BaseGame
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_utils import parse_chess_move
from config import CHESS_PROMPT_TEMPLATE
import io


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
        
        # Get PGN history and opening recognition
        pgn_history = self.get_pgn_history(include_headers=True, max_moves=30)  # Last 30 moves for context
        opening_name = self.recognize_opening()
        
        # Debug: Log what we're showing the AI
        print(f"DEBUG: Showing AI - FEN: {current_fen}")
        print(f"DEBUG: Showing AI - Move #{move_number}, {color_name} to move")
        print(f"DEBUG: Showing AI - Opening: {opening_name}")
        print(f"DEBUG: Showing AI - Legal moves: {shown_moves[:5]}...")
        print(f"DEBUG: PGN length: {len(pgn_history)} characters")
        
        try:
            from debug_console import debug_log
            debug_log(f"Prompt: {color_name} move #{move_number}, {len(shown_moves)} legal moves")
            debug_log(f"Prompt: Opening={opening_name}, FEN={current_fen}")
            debug_log(f"Prompt: PGN history length={len(pgn_history)} chars")
        except:
            pass
        
        # Enhanced prompt with PGN history and strategic context
        enhanced_prompt = f"""You are an expert chess player playing as {color_name} in move #{move_number}.

=== GAME HISTORY (PGN) - STUDY THIS FOR FULL CONTEXT ===
{pgn_history}

=== POSITION ANALYSIS ===
Opening: {opening_name}
Current Position (FEN): {current_fen}
Move #{move_number}: {color_name} to move

Current Board:
{current_board_display}

=== STRATEGIC CONTEXT FROM PGN HISTORY ===
1. OPENING ANALYSIS: What opening pattern is this? How should you continue?
2. OPPONENT PATTERNS: What has your opponent been doing? (aggressive/defensive/mistakes?)
3. GAME FLOW: Are there repeated positions to avoid? Any tactical themes emerging?
4. KING SAFETY: Have either king moved early? Is castling still possible?

=== YOUR LEGAL MOVES ===
Available moves (UCI format): {", ".join(shown_moves)}

=== CHESS PRINCIPLES FOR THIS POSITION ===
- In opening (moves 1-10): Develop pieces (knights before bishops), control center, castle early
- NEVER move your king early unless forced by check or mate threat
- Don't move the same piece twice without a strong reason
- Look for tactics: forks, pins, skewers, discovered attacks
- Consider your opponent's threats and plans based on the PGN history

=== DECISION PROCESS ===
1. Review the PGN above - what's the story of this game so far?
2. What opening principles apply to this position?
3. What are your opponent's likely plans based on their recent moves?
4. Choose the move that best continues your strategic plan

CRITICAL RULES:
- You MUST choose EXACTLY one move from the legal moves list above
- Base your decision on the FULL PGN CONTEXT, not just the current position
- Consider the opening pattern and what typical moves are good here

Format your response exactly like this:
MOVE: [choose EXACTLY one from legal moves above]
REASONING: [explain based on PGN history, opening principles, and position analysis]

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
    
    def get_pgn_history(self, include_headers: bool = True, max_moves: Optional[int] = None) -> str:
        """
        Generate PGN history of the current game.
        
        Args:
            include_headers: Whether to include PGN headers
            max_moves: Maximum number of moves to include (None for all)
            
        Returns:
            PGN string representation of the game
        """
        try:
            # Create a game from the current board
            game = chess.pgn.Game.from_board(self.board)
            
            if include_headers:
                # Get player names
                player_names = list(self.players.keys())
                white_player = player_names[0] if len(player_names) > 0 else "White"
                black_player = player_names[1] if len(player_names) > 1 else "Black"
                
                # Set PGN headers
                game.headers["Event"] = "AI vs AI Chess Battle"
                game.headers["Site"] = "Players of Games App"
                game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
                game.headers["Round"] = "1"
                game.headers["White"] = white_player
                game.headers["Black"] = black_player
                game.headers["Result"] = "*"  # Ongoing game
                
                # Add additional metadata
                if hasattr(self, 'move_count'):
                    game.headers["PlyCount"] = str(len(self.board.move_stack))
            
            # Convert to PGN string
            exporter = chess.pgn.StringExporter(headers=include_headers, variations=False, comments=False)
            pgn_str = game.accept(exporter)
            
            # Handle move truncation if requested
            if max_moves and self.board.fullmove_number > max_moves:
                lines = pgn_str.split('\n')
                header_lines = []
                move_lines = []
                
                # Separate headers from moves
                in_headers = True
                for line in lines:
                    if line.strip() == "":
                        in_headers = False
                        continue
                    if in_headers and line.startswith('['):
                        header_lines.append(line)
                    elif not in_headers:
                        move_lines.append(line)
                
                # Reconstruct with truncated moves
                if move_lines:
                    move_text = ' '.join(move_lines)
                    # Simple truncation - keep last portion
                    moves = move_text.split()
                    if len(moves) > max_moves * 2:  # Approximate move pairs
                        truncated_moves = moves[-(max_moves * 2):]
                        move_text = "... " + ' '.join(truncated_moves)
                    
                    if include_headers:
                        pgn_str = '\n'.join(header_lines) + '\n\n' + move_text
                    else:
                        pgn_str = move_text
            
            return pgn_str.strip()
            
        except Exception as e:
            print(f"ERROR: Failed to generate PGN: {e}")
            return f"[PGN generation failed: {str(e)}]"
    
    def recognize_opening(self) -> str:
        """
        Improved opening recognition: More patterns, deeper check, handles variants/transpositions.
        
        Returns:
            Opening name or "Unknown Opening"
        """
        if len(self.board.move_stack) < 1:
            return "Opening"
        
        # Get first few moves in UCI format - increased to 10 plies for better detection
        moves = [move.uci() for move in self.board.move_stack[:10]]  # Up to 10 plies (5 moves) for variants
        
        # Expanded patterns (top common from Lichess/Chess.com data; UCI format; sorted longest first for specificity)
        opening_patterns = [
            (["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"], "Ruy Lopez"),  # Very common vs. e5
            (["e2e4", "e7e5", "g1f3", "b8c6", "d2d4"], "Scotch Game"),
            (["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"], "Italian Game"),
            (["e2e4", "e7e5", "g1f3", "g8f6"], "Petroff Defense"),
            (["e2e4", "e7e5", "b1c3"], "Vienna Game"),
            (["e2e4", "e7e5", "d1h5"], "Scholar's Mate Attempt"),  # Common beginner trap
            (["e2e4", "e7e5"], "King's Pawn Game"),
            (["e2e4", "c7c5"], "Sicilian Defense"),  # Most popular Black response to e4
            (["e2e4", "e7e6"], "French Defense"),
            (["e2e4", "c7c6"], "Caro-Kann Defense"),
            (["e2e4", "g8f6"], "Alekhine Defense"),
            (["e2e4", "d7d6"], "Pirc Defense"),
            (["e2e4", "d7d5"], "Scandinavian Defense"),
            (["d2d4", "d7d5", "c2c4"], "Queen's Gambit"),
            (["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"], "Nimzo-Indian Defense"),
            (["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"], "Grünfeld Defense"),
            (["d2d4", "g8f6", "c2c4", "g7g6"], "King's Indian Defense"),
            (["d2d4", "g8f6", "c2c4", "c7c5"], "Benoni Defense"),
            (["d2d4", "g8f6"], "Indian Defenses (General)"),
            (["d2d4", "d7d5"], "Queen's Pawn Game"),
            (["c2c4"], "English Opening"),
            (["g1f3"], "Réti Opening"),
            (["d2d4", "f7f5"], "Dutch Defense"),
            (["f2f4"], "Bird's Opening"),
            (["b2b4"], "Polish Opening (Sokolsky)"),
            (["g2g4"], "Grob's Attack"),
        ]
        
        # Sort by descending pattern length to match specifics first
        opening_patterns.sort(key=lambda x: len(x[0]), reverse=True)
        
        for pattern, name in opening_patterns:
            if moves[:len(pattern)] == pattern:
                return name
            # Fallback for close matches (e.g., transposition variants)
            if len(moves) >= len(pattern) and set(moves[:len(pattern)]) == set(pattern):
                return f"Variant of {name}"
        
        return "Unknown Opening or Custom Position"
    
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
