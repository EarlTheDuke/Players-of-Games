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
            action: UCI move string (e.g., "e2e4") or algebraic notation (e.g., "nf3")
            
        Returns:
            True if move was valid and applied
        """
        try:
            # Clean the action string
            action = action.strip().lower()
            
            # Try to parse as UCI move first
            move = None
            try:
                move = chess.Move.from_uci(action)
            except (ValueError, chess.InvalidMoveError):
                # If UCI parsing fails, try algebraic notation
                try:
                    print(f"DEBUG: Trying to parse algebraic notation: {action}")
                    # Convert algebraic to move object
                    move = self.board.parse_san(action)
                    print(f"DEBUG: Successfully parsed algebraic move: {action} -> {move}")
                except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError) as e:
                    print(f"DEBUG: Failed to parse algebraic notation {action}: {e}")
                    return False
            
            if move is None:
                print(f"DEBUG: Could not parse move: {action}")
                return False
            
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
        
        # Show legal moves in a clear, comprehensive format for AI understanding
        legal_moves_uci = legal_moves  # These are already UCI from get_legal_actions()
        legal_moves_san = [self.board.san(chess.Move.from_uci(move)) for move in legal_moves_uci]
        
        # Group moves by type for better AI understanding
        piece_moves = []
        pawn_moves = []
        
        for uci, san in zip(legal_moves_uci, legal_moves_san):
            if san[0].isupper() and san[0] in 'NBRQK':
                # Piece moves (Knight, Bishop, Rook, Queen, King)
                piece_moves.append(f"{san} ({uci})")
            else:
                # Pawn moves and castling
                pawn_moves.append(f"{san} ({uci})")
        
        # Limit display to avoid overwhelming the AI
        max_moves = 10
        if len(legal_moves_uci) > max_moves:
            # Show most important moves first (piece moves, then pawn moves)
            shown_moves = piece_moves[:6] + pawn_moves[:4]
            if len(legal_moves_uci) > max_moves:
                shown_moves.append(f"... and {len(legal_moves_uci) - max_moves} more moves")
        else:
            shown_moves = piece_moves + pawn_moves
        
        # Get fresh board state
        current_fen = self.get_state_text()
        current_board_display = self.get_state_display()
        move_number = self.board.fullmove_number
        
        # Check for failed moves to provide feedback to AI
        failed_moves_text = ""
        if hasattr(self, 'failed_moves') and self.current_player in self.failed_moves:
            failed_moves_list = list(self.failed_moves[self.current_player])
            if failed_moves_list:
                failed_moves_text = f"\n⚠️  IMPORTANT: You previously tried these moves which failed validation: {', '.join(failed_moves_list)}. Please choose a DIFFERENT move from the legal moves list.\n"
        
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
            debug_log(f"Enhanced Prompt: {color_name} move #{move_number}, {len(shown_moves)} legal moves")
            debug_log(f"Enhanced Prompt: Opening={opening_name}, FEN={current_fen}")
            debug_log(f"Enhanced Prompt: PGN history length={len(pgn_history)} chars")
        except:
            pass
        
        # Enhanced prompt with strategic guidance and PGN context
        enhanced_prompt = f"""You are an expert chess player (2000+ ELO) playing as {color_name}. Your priorities: king safety, piece development, center control, and tactical awareness.
{failed_moves_text}
=== GAME HISTORY (PGN) - ANALYZE FOR STRATEGIC CONTEXT ===
{pgn_history}

=== POSITION ANALYSIS ===
Opening: {opening_name}
Current Position (FEN): {current_fen}
Move #{move_number}: {color_name} to move

Current Board:
{current_board_display}

=== STRATEGIC ASSESSMENT FROM PGN ===
1. OPENING PATTERN: What opening is this? How should you continue based on typical plans?
2. OPPONENT STYLE: From the PGN, is your opponent playing aggressively, defensively, or making errors?
3. GAME PHASE: Opening (develop & castle), Middlegame (tactics & attack), or Endgame (king activity & pawns)?
4. KEY WEAKNESSES: Any exposed kings, weak squares, or material imbalances to exploit?

=== YOUR LEGAL MOVES ===
Available moves: {", ".join(shown_moves)}

=== CHESS PRINCIPLES FOR THIS POSITION ===
- OPENING (moves 1-10): Develop knights before bishops, control center (e4/d4/e5/d5), castle early
- NEVER move king early unless forced by check or immediate mate threat
- Look for tactics: checks, captures, threats (forks, pins, skewers)
- Evaluate candidate moves: Does this improve my position? Does it create threats? Is it safe?
- Consider opponent's likely response to your top 2-3 candidate moves

=== ANTI-BLUNDER CHECK ===
Before finalizing your move, ask: "If I play this move, what is my opponent's best response? Am I hanging any pieces?"

CRITICAL: You MUST choose a legal move. You can use either:
- UCI format (e.g., e2e4, g1f3, e1g1)
- Algebraic notation (e.g., e4, Nf3, O-O)

Format your response:
MOVE: [your move in UCI format (e2e4) or algebraic notation (e4, Nf3, O-O)]
REASONING: [75-125 words: Explain your choice based on opening principles, PGN context, and tactical considerations. Mention your top 2-3 candidate moves and why you chose this one.]

Your move:"""
        
        # Log final prompt details for monitoring
        try:
            from debug_console import debug_log
            debug_log(f"Enhanced Prompt: Total length={len(enhanced_prompt)} chars")
            print(f"DEBUG: Enhanced prompt total length: {len(enhanced_prompt)} characters")
        except:
            pass
        
        return enhanced_prompt
    
    def parse_action_from_response(self, response: str) -> Optional[str]:
        """Parse a UCI move from the AI's response with extensive debugging."""
        print("\n" + "="*80)
        print("🔍 MOVE VALIDATION DEBUG - DETAILED ANALYSIS")
        print("="*80)
        
        # Step 1: Parse the move from AI response
        parsed_move = parse_chess_move(response)
        print(f"📝 AI Response (first 200 chars): {response[:200]}...")
        print(f"🎯 Parsed move from AI: '{parsed_move}'")
        
        # Step 2: Get current board state
        current_fen = self.board.fen()
        current_turn = "White" if self.board.turn else "Black"
        print(f"♟️  Current board FEN: {current_fen}")
        print(f"🔄 Current turn: {current_turn}")
        
        # Step 3: Get ALL legal moves in multiple formats
        legal_moves_objects = list(self.board.legal_moves)
        legal_moves_uci = [str(move) for move in legal_moves_objects]
        legal_moves_san = []
        
        print(f"\n📋 LEGAL MOVES ANALYSIS:")
        print(f"   Total legal moves: {len(legal_moves_objects)}")
        print(f"   UCI format: {legal_moves_uci}")
        
        # Generate SAN (algebraic) for each legal move
        for move_obj in legal_moves_objects:
            try:
                san = self.board.san(move_obj)
                legal_moves_san.append(san)
            except Exception as e:
                print(f"   ⚠️  Error converting {move_obj} to SAN: {e}")
        
        print(f"   SAN format: {legal_moves_san}")
        print(f"   SAN lowercase: {[san.lower() for san in legal_moves_san]}")
        
        # Step 4: Test the parsed move against legal moves
        if not parsed_move:
            print(f"❌ VALIDATION FAILED: No move could be parsed from AI response")
            return None
            
        print(f"\n🔍 TESTING PARSED MOVE: '{parsed_move}'")
        
        # Test exact matches
        uci_match = parsed_move in legal_moves_uci
        san_exact_match = parsed_move in legal_moves_san
        san_lower_match = parsed_move.lower() in [san.lower() for san in legal_moves_san]
        
        print(f"   ✓ UCI exact match: {uci_match}")
        print(f"   ✓ SAN exact match: {san_exact_match}")
        print(f"   ✓ SAN lowercase match: {san_lower_match}")
        
        # Step 5: Try to parse the move with python-chess
        move_obj = None
        parsing_method = None
        
        # Try UCI parsing
        try:
            move_obj = chess.Move.from_uci(parsed_move)
            parsing_method = "UCI"
            print(f"   ✅ UCI parsing successful: {move_obj}")
        except Exception as e:
            print(f"   ❌ UCI parsing failed: {e}")
        
        # Try SAN parsing if UCI failed
        if move_obj is None:
            try:
                move_obj = self.board.parse_san(parsed_move)
                parsing_method = "SAN"
                print(f"   ✅ SAN parsing successful: {move_obj}")
            except Exception as e:
                print(f"   ❌ SAN parsing failed: {e}")
        
        # Try SAN parsing with capitalization fixes
        if move_obj is None:
            for variation in [parsed_move.capitalize(), parsed_move.upper()]:
                try:
                    move_obj = self.board.parse_san(variation)
                    parsing_method = f"SAN ({variation})"
                    print(f"   ✅ SAN parsing successful with '{variation}': {move_obj}")
                    break
                except Exception as e:
                    print(f"   ❌ SAN parsing with '{variation}' failed: {e}")
        
        # Step 6: Check if parsed move is actually legal
        if move_obj:
            is_legal = move_obj in self.board.legal_moves
            print(f"   ✅ Move object created via {parsing_method}: {move_obj}")
            print(f"   ✅ Move is legal on board: {is_legal}")
            
            if is_legal:
                print(f"🎉 VALIDATION SUCCESS: Move '{parsed_move}' is valid!")
                try:
                    from debug_console import debug_log
                    debug_log(f"VALIDATION SUCCESS: {parsed_move} -> {move_obj}")
                except:
                    pass
                return parsed_move
            else:
                print(f"❌ VALIDATION FAILED: Move object exists but is not in legal moves")
                print(f"   Legal move objects: {legal_moves_objects[:10]}...")
        else:
            print(f"❌ VALIDATION FAILED: Could not create move object from '{parsed_move}'")
        
        # Step 7: Final failure logging
        print(f"\n💥 FINAL RESULT: MOVE REJECTED")
        print(f"   AI wanted: '{parsed_move}'")
        print(f"   Available UCI: {legal_moves_uci[:5]}...")
        print(f"   Available SAN: {legal_moves_san[:5]}...")
        print("="*80)
        
        try:
            from debug_console import debug_log
            debug_log(f"VALIDATION FAILED: {parsed_move} not in legal moves")
            debug_log(f"Legal UCI: {legal_moves_uci[:5]}")
            debug_log(f"Legal SAN: {legal_moves_san[:5]}")
        except:
            pass
            
        return None
    
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
