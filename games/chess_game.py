"""Chess game implementation using python-chess library."""
import chess
import chess.pgn
from typing import List, Optional, Tuple
import re
import json
import time
import uuid
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
        # Cache threats for prompt injection
        self._cached_threats_text: Optional[str] = None
        # Per-turn veto tracking to avoid repetition loops
        self._vetoed_moves_this_turn: dict[str, int] = {}
    
    def _log_block(self, title: str, lines: list[str]) -> None:
        """Utility to emit a single multi-line debug block to the debug console."""
        try:
            from debug_console import debug_log
            header = f"\n{'='*80}\n{title}\n{'='*80}"
            body = "\n".join(lines)
            debug_log(f"{header}\n{body}")
        except Exception:
            pass

    def _log_turn_context(self, *, player_name: str, color_name: str, move_number: int,
                           opening_name: str, current_fen: str, current_board_display: str,
                           game_phase: str, phase_info: dict, shown_moves: list[str],
                           previous_feedback_text: str, veto_text: str) -> None:
        try:
            model_params = self.get_model_params()
        except Exception:
            model_params = {}
        lines: list[str] = []
        # Pre-move flags and legal move breakdown
        in_check = self.board.is_check()
        try:
            checkers = self._get_checking_pieces() if in_check else []
        except Exception:
            checkers = []
        castling_before = f"W:K{int(self.board.has_kingside_castling_rights(chess.WHITE))}Q{int(self.board.has_queenside_castling_rights(chess.WHITE))} | B:K{int(self.board.has_kingside_castling_rights(chess.BLACK))}Q{int(self.board.has_queenside_castling_rights(chess.BLACK))}"
        repetition = self.board.can_claim_threefold_repetition()
        halfmove = self.board.halfmove_clock
        legal_objs = list(self.board.legal_moves)
        total_legal = len(legal_objs)
        count_captures = sum(1 for m in legal_objs if self.board.is_capture(m))
        count_checks = 0
        count_promos = 0
        count_castles = 0
        for m in legal_objs[:100]:
            try:
                if m.promotion:
                    count_promos += 1
                if self.board.is_castling(m):
                    count_castles += 1
                self.board.push(m)
                if self.board.is_check():
                    count_checks += 1
                self.board.pop()
            except Exception:
                pass
        lines.append(f"Turn: {move_number}, Player: {player_name} ({color_name}), Turn ID: {getattr(self, '_turn_id', '')}")
        lines.append(f"Phase: {game_phase.upper()}, Opening: {opening_name}")
        lines.append(f"FEN: {current_fen}")
        lines.append("Board:\n" + current_board_display)
        shown_ct = min(len(shown_moves), 20)
        lines.append(f"Legal moves shown: {shown_ct} of {total_legal} | breakdown: captures={count_captures}, checks={count_checks}, promos={count_promos}, castles={count_castles}")
        if previous_feedback_text.strip():
            lines.append("Feedback: " + previous_feedback_text.strip())
        if veto_text.strip():
            lines.append("Vetoed: " + veto_text.strip())
        if phase_info:
            try:
                lines.append(f"Phase stats: pieces={phase_info.get('piece_count')}, material_total={phase_info.get('total_material')}, material_balance={phase_info.get('material_balance'):+d}")
            except Exception:
                pass
        lines.append(f"Pre-move flags: in_check={in_check}, checkers={'; '.join(checkers) if checkers else 'none'}, castling_rights={castling_before}, repetition_claim={repetition}, halfmove_clock={halfmove}")
        if model_params:
            lines.append(f"Model params: temperature={model_params.get('temperature')}, max_tokens={model_params.get('max_tokens')}")
        self._log_block("TURN CONTEXT", lines)

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
            # Clean the action string (preserve case for algebraic notation)
            action = action.strip()
            
            # Try to parse as UCI move first (UCI should be lowercase)
            move = None
            try:
                move = chess.Move.from_uci(action.lower())
                print(f"DEBUG: Successfully parsed UCI move: {action.lower()} -> {move}")
            except (ValueError, chess.InvalidMoveError):
                # If UCI parsing fails, try algebraic notation (preserve case)
                try:
                    print(f"DEBUG: Trying to parse algebraic notation: {action}")
                    # Convert algebraic to move object (case-sensitive)
                    move = self.board.parse_san(action)
                    print(f"DEBUG: Successfully parsed algebraic move: {action} -> {move}")
                except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError) as e:
                    print(f"DEBUG: Failed to parse algebraic notation {action}: {e}")
                    try:
                        self._last_failure_reason[self.current_player] = f"Could not parse move '{action}'"
                    except Exception:
                        pass
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
            
            # Optional lightweight blunder check before applying
            if move in self.board.legal_moves:
                if self._would_be_gross_blunder(move):
                    print("DEBUG: Potential blunder detected; rejecting move for retry")
                    try:
                        self._last_failure_reason[self.current_player] = "Previous attempt likely blundered material (>threshold)"
                        # Mark to skip tracking as failed repetition; this is a veto, not illegal
                        setattr(self, '_skip_track_failed', True)
                        # Track per-turn veto count
                        uci = move.uci()
                        self._vetoed_moves_this_turn[uci] = self._vetoed_moves_this_turn.get(uci, 0) + 1
                    except Exception:
                        pass
                    return False
                # Store move in SAN notation for PGN
                san_move = self.board.san(move)
                self.moves_san.append(san_move)
                # Pre-move context for logging
                prev_fullmove = self.board.fullmove_number
                mover_color = 'White' if self.board.turn == chess.WHITE else 'Black'
                uci_move = move.uci()
                was_capture = self.board.is_capture(move)
                baseline_eval = self._evaluate_material(self.board, self.board.turn)
                moved_piece = self.board.piece_at(move.from_square).symbol() if self.board.piece_at(move.from_square) else '?'
                captured_piece = None
                # Apply the move
                self.board.push(move)
                try:
                    # If capture, the captured piece type can be inferred by SAN or prior board state; using SAN marker 'x'
                    if 'x' in san_move:
                        captured_piece = 'captured'  # detailed type requires deeper diff; keep simple label
                except Exception:
                    pass
                apply_start = time.time()
                after_check = self.board.is_check()
                after_eval = self._evaluate_material(self.board, not self.board.turn)  # same perspective as mover
                material_delta = after_eval - baseline_eval
                after_fen = self.board.fen()
                reply_count = len(list(self.board.legal_moves))
                is_mate = self.board.is_checkmate()
                is_stalemate = self.board.is_stalemate()
                castling_after = f"W:K{int(self.board.has_kingside_castling_rights(chess.WHITE))}Q{int(self.board.has_queenside_castling_rights(chess.WHITE))} | B:K{int(self.board.has_kingside_castling_rights(chess.BLACK))}Q{int(self.board.has_queenside_castling_rights(chess.BLACK))}"
                apply_ms = int((time.time() - apply_start) * 1000)
                print(f"DEBUG: Move {action} applied successfully")
                # Emit structured post-move block
                try:
                    self._log_block("MOVE APPLIED", [
                        f"Turn: {prev_fullmove}, Player: {self.current_player} ({mover_color})",
                        f"Move: {san_move} ({uci_move})",
                        f"Piece moved: {moved_piece}",
                        f"Captured: {captured_piece if captured_piece else 'False'}",
                        f"Capture: {was_capture}",
                        f"Gave check: {after_check}",
                        f"Material delta (self POV): {material_delta:+d}",
                        f"Opponent replies available: {reply_count}",
                        f"Checkmate: {is_mate}, Stalemate: {is_stalemate}",
                        f"Castling rights after: {castling_after}",
                        f"Apply ms: {apply_ms}",
                        f"FEN: {after_fen}",
                    ])
                except Exception:
                    pass
                return True
            else:
                print(f"DEBUG: Move {action} is not legal in current position")
                try:
                    self._last_failure_reason[self.current_player] = f"Move '{action}' is not legal in this position"
                except Exception:
                    pass
                return False
                
        except (ValueError, chess.InvalidMoveError) as e:
            print(f"DEBUG: Invalid move format {action}: {e}")
            return False
    
    def get_prompt(self) -> str:
        """Generate a chess prompt for the current player."""
        current_color = self._get_current_player_color()
        color_name = "White" if current_color == chess.WHITE else "Black"
        
        # Log player and board turn, but do NOT auto-switch here
        board_turn = "White" if self.board.turn == chess.WHITE else "Black"
        print(f"DEBUG: Player {self.current_player} ({color_name}) requesting move")
        print(f"DEBUG: Board expects {board_turn} to move")
        if color_name != board_turn:
            print(f"WARNING: Turn mismatch detected (player vs board). Will rely on reconcile_turn() before move.")
        
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
        
        # Prefer to show captures first and expand if few total moves
        captures = []
        non_captures = []
        for uci in legal_moves_uci:
            mv = chess.Move.from_uci(uci)
            (captures if self.board.is_capture(mv) else non_captures).append(uci)
        shown_pairs = []
        for uci in captures + non_captures:
            san = self.board.san(chess.Move.from_uci(uci))
            shown_pairs.append(f"{san} ({uci})")
        if len(shown_pairs) <= 20:
            shown_moves = shown_pairs
        else:
            shown_moves = shown_pairs[:20] + [f"... and {len(shown_pairs) - 20} more moves"]
        
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
        # Include last failure reason if any
        previous_feedback_text = ""
        try:
            last_reason = self._last_failure_reason.get(self.current_player) if hasattr(self, '_last_failure_reason') else ""
            if last_reason:
                previous_feedback_text = f"Previous attempt failed because: {last_reason}. Choose differently.\n\n"
        except Exception:
            previous_feedback_text = ""
        # Include per-turn vetoed moves (to avoid repeated blunders) - cap to 5 entries for brevity
        veto_text = ""
        try:
            if getattr(self, '_vetoed_moves_this_turn', None):
                veto_items = [(mv, cnt) for mv, cnt in self._vetoed_moves_this_turn.items() if cnt >= 1]
                veto_items.sort(key=lambda x: -x[1])
                if veto_items:
                    limited = [f"{mv} (vetoed {cnt}x)" for mv, cnt in veto_items[:5]]
                    veto_text = f"Do NOT play these moves this turn: {', '.join(limited)}.\n\n"
        except Exception:
            pass
        
        # Get PGN history and opening recognition
        pgn_history = self.get_pgn_history(include_headers=True, max_moves=30)  # Last 30 moves for context
        opening_name = self.recognize_opening()
        
        # PHASE-AWARE SYSTEM: Detect current game phase
        game_phase, phase_info = self.detect_game_phase()
        # Threat analysis injection
        threats_text = self.get_threats()
        self._cached_threats_text = threats_text
        
        # Debug: Log what we're showing the AI
        print(f"DEBUG: Showing AI - FEN: {current_fen}")
        print(f"DEBUG: Showing AI - Move #{move_number}, {color_name} to move")
        print(f"DEBUG: Showing AI - Game Phase: {game_phase.upper()}")
        print(f"DEBUG: Showing AI - Opening: {opening_name}")
        print(f"DEBUG: Showing AI - Legal moves: {shown_moves[:5]}...")
        print(f"DEBUG: PGN length: {len(pgn_history)} characters")
        print(f"DEBUG: Phase Info - Pieces: {phase_info['piece_count']}, Material: {phase_info['total_material']}")
        
        try:
            from debug_console import debug_log
            debug_log(f"Enhanced Prompt: {color_name} move #{move_number}, {len(shown_moves)} legal moves")
            debug_log(f"Enhanced Prompt: PHASE={game_phase.upper()}, Opening={opening_name}, FEN={current_fen}")
            debug_log(f"Enhanced Prompt: PGN history length={len(pgn_history)} chars")
            debug_log(f"Phase Analysis: {phase_info['piece_count']} pieces, {phase_info['total_material']} material")
        except:
            pass
        
        # DYNAMIC PROMPT GENERATION based on game phase
        if game_phase == 'opening':
            enhanced_prompt = self.get_opening_prompt_template(
                color_name, phase_info, shown_moves, failed_moves_text + previous_feedback_text + veto_text, 
                pgn_history, opening_name, current_fen, current_board_display, move_number
            )
        elif game_phase == 'middlegame':
            enhanced_prompt = self.get_middlegame_prompt_template(
                color_name, phase_info, shown_moves, failed_moves_text + previous_feedback_text + veto_text,
                pgn_history, opening_name, current_fen, current_board_display, move_number
            )
        else:  # endgame
            enhanced_prompt = self.get_endgame_prompt_template(
                color_name, phase_info, shown_moves, failed_moves_text + previous_feedback_text + veto_text,
                pgn_history, opening_name, current_fen, current_board_display, move_number
            )

        # Emit a consolidated turn context block to the debug console
        try:
            self._log_turn_context(
                player_name=self.current_player,
                color_name=color_name,
                move_number=move_number,
                opening_name=opening_name,
                current_fen=current_fen,
                current_board_display=current_board_display,
                game_phase=game_phase,
                phase_info=phase_info,
                shown_moves=shown_moves,
                previous_feedback_text=previous_feedback_text,
                veto_text=veto_text,
            )
        except Exception:
            pass

        # Prepend board verification and immediate threats
        verification = (
            "=== BOARD VERIFICATION ===\n"
            "Step 1: Confirm the position from FEN/ASCII. List your pieces explicitly. Use full phrases (e.g., 'White Queen at h5'); avoid bare coordinates like 'h5' alone. Do not assume extra pieces.\n\n"
            "=== IMMEDIATE THREATS ===\n"
            f"{threats_text if threats_text else 'No immediate threats.'}\n\n"
            "Address all threats before planning.\n\n"
            "OUTPUT CONTRACT (STRICT): On the FIRST line, output exactly one of the following forms: MOVE: <SAN or UCI>  OR  {\"move\":\"<SAN or UCI>\"}. After that, you may write REASONING and CANDIDATES.\n"
        )
        enhanced_prompt = verification + enhanced_prompt
        
        # Log final prompt details for monitoring
        try:
            from debug_console import debug_log
            debug_log(f"Enhanced Prompt: Total length={len(enhanced_prompt)} chars")
            print(f"DEBUG: Enhanced prompt total length: {len(enhanced_prompt)} characters")
        except:
            pass
        
        return enhanced_prompt

    def reconcile_turn(self) -> None:
        """Ensure current_player matches board.turn. Do not modify board; only sync current_player_index."""
        try:
            board_color = chess.WHITE if self.board.turn == chess.WHITE else chess.BLACK
            # Identify which player has this color
            for idx, name in enumerate(self.player_list):
                if self.player_colors.get(name) == board_color:
                    if self.current_player_index != idx:
                        print(f"DEBUG: Reconciling turn: switching current player from {self.current_player} to {name}")
                        self.current_player_index = idx
                    break
        except Exception as e:
            print(f"DEBUG: reconcile_turn failed: {e}")
    
    def start_turn_setup(self) -> None:
        """Reset per-turn state before prompting the model."""
        try:
            self._vetoed_moves_this_turn = {}
            # Per-turn identifiers and timers
            self._turn_id = str(uuid.uuid4())
            self._turn_start_ts = time.time()
        except Exception:
            pass
    
    def parse_action_from_response(self, response: str) -> Optional[str]:
        """Parse a move from the AI's response with a strict MOVE/JSON contract and extensive debugging."""
        print("\n" + "="*80)
        print("🔍 MOVE VALIDATION DEBUG - DETAILED ANALYSIS")
        print("="*80)
        
        # Soft-check for candidates: don't reject outright if a legal move is provided
        try:
            has_candidates = bool(re.search(r"CANDIDATES\s*:|Candidates\s*:|candidates\s*:", response))
        except Exception:
            has_candidates = True
        
        # Step 1: Strict extraction from JSON or MOVE: line
        parsed_move: Optional[str] = None
        raw_move: Optional[str] = None
        print(f"📝 AI Response (first 200 chars): {response[:200]}...")
        parse_start = time.time()
        
        # 1a) Try to extract JSON {"move":"..."}
        try:
            json_match = re.search(r"\{\s*\"?move\"?\s*:\s*\"([^\"]+)\"\s*\}", response, re.IGNORECASE)
            if json_match:
                raw_move = json_match.group(1)
        except Exception:
            raw_move = None
        
        # 1b) If not found, look for the last MOVE: occurrence, accepting optional brackets
        if not raw_move:
            try:
                move_matches = list(re.finditer(r"(?is)MOVE\s*:\s*(?:\[\s*)?(.+?)(?:\s*\]|\s*REASONING\s*:|\n|\r|$)", response, re.IGNORECASE))
                if move_matches:
                    raw_move = move_matches[-1].group(1)
            except Exception:
                raw_move = None
        
        if raw_move:
            # Normalize: strip wrappers, markdown, stars, trailing punctuation
            candidate = raw_move.strip()
            candidate = candidate.strip('`* ').strip()
            # Remove trailing punctuation that sometimes appears
            candidate = re.sub(r"[\.;,:]+$", "", candidate)
            # Collapse extra spaces
            candidate = re.sub(r"\s+", " ", candidate)
            # Some authors put the move in brackets like [Qxc5+]
            candidate = candidate.strip('[]')
            raw_move = candidate
            print(f"🎯 Extracted raw move from contract: '{raw_move}'")
        else:
            print("❌ No MOVE or JSON move found in response")
        
        # Step 1c: Reject bare-square tokens like "h5" / "e1"
        if raw_move and re.fullmatch(r"[a-h][1-8]", raw_move.strip(), flags=re.IGNORECASE):
            print(f"❌ Rejected bare-square token as move: '{raw_move}'")
            raw_move = None
        
        # Step 1d: If still None, attempt a conservative fallback by scanning for any legal token later
        parsed_move = raw_move
        
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
            # Conservative tertiary fallback: try to find any legal SAN/UCI token inside the response
            try:
                # prefer SAN tokens with symbols like +/# which are less ambiguous
                san_tokens = sorted(legal_moves_san, key=lambda s: (0 if ('+' in s or '#' in s) else 1, -len(s)))
                for tok in san_tokens:
                    if re.search(rf"(?<![A-Za-z0-9_]){re.escape(tok)}(?![A-Za-z0-9_])", response):
                        parsed_move = tok
                        print(f"✅ Fallback found SAN token in response: '{parsed_move}'")
                        break
                if not parsed_move:
                    for tok in legal_moves_uci:
                        if tok in response:
                            parsed_move = tok
                            print(f"✅ Fallback found UCI token in response: '{parsed_move}'")
                            break
            except Exception:
                pass
        if not parsed_move:
            print(f"❌ VALIDATION FAILED: No move could be parsed from AI response")
            try:
                if not hasattr(self, '_last_failure_reason'):
                    self._last_failure_reason = {}
                self._last_failure_reason[self.current_player] = (
                    "Could not parse move from response. Respond with first line only: "
                    "MOVE: <SAN or UCI>."
                )
            except Exception:
                pass
            # Emit structured block for easier post-mortem
            self._log_block("MOVE PARSE FAILURE", [
                f"Player: {self.current_player}",
                f"Turn: {self.board.fullmove_number}",
                "Reason: Could not extract a valid MOVE from the response",
            ])
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
        
        # Try SAN first (accepts symbols like +/# and castling notation)
        try:
            move_obj = self.board.parse_san(parsed_move)
            parsing_method = "SAN"
            print(f"   ✅ SAN parsing successful: {move_obj}")
        except Exception as e:
            print(f"   ❌ SAN parsing failed: {e}")
        
        # Try UCI parsing if SAN failed, but only if format looks like UCI
        if move_obj is None:
            looks_like_uci = bool(re.fullmatch(r"[a-h][1-8][a-h][1-8][nbrqNBRQ]?", parsed_move))
            if looks_like_uci:
                try:
                    move_obj = chess.Move.from_uci(parsed_move.lower())
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
                parse_ms = int((time.time() - parse_start) * 1000)
                if not has_candidates:
                    print("⚠️ FORMAT WARNING: No CANDIDATES section present; accepting legal move but will warn in next prompt.")
                    try:
                        self._last_failure_reason[self.current_player] = "Missing CANDIDATES: include 2-3 lines next time"
                    except Exception:
                        pass
                print(f"🎉 VALIDATION SUCCESS: Move '{parsed_move}' is valid!")
                try:
                    from debug_console import debug_log
                    debug_log(f"VALIDATION SUCCESS: {parsed_move} -> {move_obj}; parse_ms={parse_ms}")
                except:
                    pass
                # Emit a compact summary block for this validation
                self._log_block("MOVE VALIDATION DETAILS", [
                    f"Turn: {self.board.fullmove_number}",
                    f"Player: {self.current_player}",
                    f"Proposed: {parsed_move} (parsed via {parsing_method})",
                    f"Legal: True",
                    f"Parse ms: {parse_ms}",
                ])
                return parsed_move
            else:
                print(f"❌ VALIDATION FAILED: Move object exists but is not in legal moves")
                print(f"   Legal move objects: {legal_moves_objects[:10]}...")
                self._log_block("MOVE INVALID (NOT LEGAL)", [
                    f"Turn: {self.board.fullmove_number}",
                    f"Player: {self.current_player}",
                    f"Proposed: {parsed_move}",
                    "Legal: False",
                ])
        else:
            print(f"❌ VALIDATION FAILED: Could not create move object from '{parsed_move}'")
            try:
                if not hasattr(self, '_last_failure_reason'):
                    self._last_failure_reason = {}
                self._last_failure_reason[self.current_player] = (
                    f"Could not parse move '{parsed_move}'. Use exact format: MOVE: <SAN or UCI>."
                )
            except Exception:
                pass
        
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

    def _evaluate_material(self, board: chess.Board, perspective: Optional[bool] = None) -> int:
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
        }
        score = 0
        if perspective is None:
            perspective = self.board.turn
        for sq in chess.SQUARES:
            p = board.piece_at(sq)
            if not p:
                continue
            val = piece_values.get(p.piece_type, 0)
            score += val if p.color == perspective else -val
        return score

    def _compute_tactical_density(self) -> int:
        # Simple proxy: number of captures available + checks available
        captures = sum(1 for m in self.board.legal_moves if self.board.is_capture(m))
        checks = 0
        for m in list(self.board.legal_moves)[:50]:
            self.board.push(m)
            if self.board.is_check():
                checks += 1
            self.board.pop()
        return captures + checks

    def _blunder_threshold(self) -> int:
        phase, _ = self.detect_game_phase()
        density = self._compute_tactical_density()
        # Relax in sharp positions, stricter in quiet endgames
        if phase == 'endgame' and density <= 2:
            return 3
        if density >= 6:
            return 5
        return 4

    def _would_be_gross_blunder(self, move: chess.Move) -> bool:
        # Phase/tactical-aware threshold (adjust if side is already behind)
        threshold = self._blunder_threshold()
        perspective = self.board.turn
        baseline = self._evaluate_material(self.board, perspective)
        if baseline < -2:
            # If already worse materially, allow more risk-taking
            threshold += 1
        temp = self.board.copy()
        hanging_before = self._get_hanging_squares_for_current()
        temp.push(move)
        worst_drop = 0
        # Prioritize forcing replies first
        replies = list(temp.legal_moves)
        forcing = [m for m in replies if temp.is_capture(m)]
        replies = forcing + [m for m in replies if m not in forcing]
        for idx, opp_move in enumerate(replies[:12]):
            temp.push(opp_move)
            delta = baseline - self._evaluate_material(temp, perspective)
            worst_drop = max(worst_drop, delta)
            temp.pop()
        # If the move evacuates a hanging piece to safety, be more permissive
        try:
            if move.from_square in hanging_before:
                new_sq = move.to_square
                attackers_new = len(temp.attackers(not self.board.turn, new_sq))
                defenders_new = len(temp.attackers(self.board.turn, new_sq))
                if attackers_new <= defenders_new:
                    threshold += 1
        except Exception:
            pass

        # Explicit queen-sac hard rule: if queen is captured next move without compensation, veto
        queen_sac = False
        try:
            # If our queen is en prise after our move and can be taken immediately with net <= -7
            qsq = None
            for sq in chess.SQUARES:
                p = temp.piece_at(sq)
                if p and p.piece_type == chess.QUEEN and p.color == perspective:
                    qsq = sq
                    break
            if qsq is not None:
                opp_attackers = list(temp.attackers(not perspective, qsq))
                if opp_attackers:
                    # Take queen and evaluate delta
                    cap_move = chess.Move(opp_attackers[0], qsq)
                    if cap_move in temp.legal_moves:
                        temp.push(cap_move)
                        delta_q = baseline - self._evaluate_material(temp, perspective)
                        queen_sac = delta_q >= 7
                        temp.pop()
        except Exception:
            pass
        return queen_sac or (worst_drop >= threshold)

    def _get_checking_pieces(self) -> List[str]:
        if not self.board.is_check():
            return []
        checkers = []
        king_sq = self.board.king(self.board.turn)
        for sq in self.board.attackers(not self.board.turn, king_sq):
            piece = self.board.piece_at(sq)
            if piece:
                checkers.append(f"{piece.symbol()} on {chess.square_name(sq)}")
        return checkers

    def _find_hanging_pieces(self) -> List[str]:
        hanging: List[str] = []
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                attackers = len(self.board.attackers(not self.board.turn, sq))
                defenders = len(self.board.attackers(self.board.turn, sq))
                if attackers > defenders:
                    hanging.append(f"{piece.symbol()} on {chess.square_name(sq)} (attacked {attackers}, defended {defenders})")
        return hanging

    def _get_hanging_squares_for_current(self) -> List[int]:
        squares: List[int] = []
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                attackers = len(self.board.attackers(not self.board.turn, sq))
                defenders = len(self.board.attackers(self.board.turn, sq))
                if attackers > defenders:
                    squares.append(sq)
        return squares

    def _find_protected_attacks(self) -> List[str]:
        traps: List[str] = []
        # Look for opponent pieces attacked that are insufficiently defended
        for sq in chess.SQUARES:
            piece = self.board.piece_at(sq)
            if piece and piece.color != self.board.turn:
                attackers = list(self.board.attackers(self.board.turn, sq))
                if not attackers:
                    continue
                defenders = list(self.board.attackers(not self.board.turn, sq))
                if len(attackers) > len(defenders):
                    traps.append(f"Attack on {piece.symbol()} at {chess.square_name(sq)} may win material")
        return traps

    def get_threats(self) -> str:
        threats: List[str] = []
        if self.board.is_check():
            threats.append(f"You are in check from {', '.join(self._get_checking_pieces())}.")
        hanging = self._find_hanging_pieces()
        if hanging:
            threats.append(f"Hanging pieces: {', '.join(hanging)}.")
        protected_attacks = self._find_protected_attacks()
        if protected_attacks:
            threats.append(f"Potential traps: {', '.join(protected_attacks)}.")
        return "\n".join(threats) if threats else "No immediate threats."

    def get_model_params(self) -> dict:
        # Lower temperature in endgame for determinism; allow more tokens
        phase, _ = self.detect_game_phase()
        if phase == 'endgame':
            return {"temperature": 0.3, "max_tokens": 800}
        return {"temperature": 0.7, "max_tokens": 500}

    def get_max_attempts(self) -> int:
        phase, _ = self.detect_game_phase()
        return 5 if phase == 'endgame' else 3

    def get_safe_fallback_action(self) -> str:
        # Rank legal moves by worst-case eval vs forcing replies; skip per-turn vetoed moves
        legal = list(self.board.legal_moves)
        if not legal:
            return ""
        candidates: list[tuple[float, chess.Move]] = []
        hanging_before = self._get_hanging_squares_for_current()
        for mv in legal:
            try:
                uci = mv.uci()
                if self._vetoed_moves_this_turn.get(uci, 0) >= 1:
                    continue
            except Exception:
                pass
            temp = self.board.copy()
            temp.push(mv)
            perspective = self.board.turn
            baseline = self._evaluate_material(self.board, perspective)
            replies = list(temp.legal_moves)
            forcing = [m for m in replies if temp.is_capture(m)]
            replies = forcing + [m for m in replies if m not in forcing]
            worst = 0
            for opp in replies[:10]:
                temp.push(opp)
                delta = baseline - self._evaluate_material(temp, perspective)
                if delta > worst:
                    worst = delta
                temp.pop()
            # Bonus if move evacuates a hanging piece to safety
            bonus = 0.0
            try:
                if mv.from_square in hanging_before:
                    new_sq = mv.to_square
                    attackers_new = len(temp.attackers(not self.board.turn, new_sq))
                    defenders_new = len(temp.attackers(self.board.turn, new_sq))
                    if attackers_new <= defenders_new:
                        bonus += 0.5
            except Exception:
                pass
            candidates.append((-(worst - bonus), mv))  # higher is better (less worst-case loss)
        if not candidates:
            # fallback to any legal move if all vetoed
            return legal[0].uci()
        # Select the candidate with the highest score (best worst-case outcome)
        best = max(candidates, key=lambda x: x[0])
        return best[1].uci()
    
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
    
    def detect_game_phase(self) -> tuple[str, dict]:
        """
        Intelligently detect the current game phase based on multiple factors.
        
        Returns:
            tuple: (phase_name, phase_info) where phase_name is 'opening', 'middlegame', or 'endgame'
                   and phase_info contains relevant statistics and characteristics
        """
        # Count pieces and material
        piece_count = 0
        material_count = {'white': 0, 'black': 0}
        piece_types = {'white': {'queens': 0, 'rooks': 0, 'bishops': 0, 'knights': 0, 'pawns': 0},
                      'black': {'queens': 0, 'rooks': 0, 'bishops': 0, 'knights': 0, 'pawns': 0}}
        
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                       chess.ROOK: 5, chess.QUEEN: 9}
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                piece_count += 1
                color = 'white' if piece.color == chess.WHITE else 'black'
                material_count[color] += piece_values.get(piece.piece_type, 0)
                
                if piece.piece_type == chess.QUEEN:
                    piece_types[color]['queens'] += 1
                elif piece.piece_type == chess.ROOK:
                    piece_types[color]['rooks'] += 1
                elif piece.piece_type == chess.BISHOP:
                    piece_types[color]['bishops'] += 1
                elif piece.piece_type == chess.KNIGHT:
                    piece_types[color]['knights'] += 1
                elif piece.piece_type == chess.PAWN:
                    piece_types[color]['pawns'] += 1
        
        move_number = self.board.fullmove_number
        total_material = material_count['white'] + material_count['black']
        
        # Check for castling rights (indicates opening/early middlegame)
        castling_rights = self.board.has_kingside_castling_rights(chess.WHITE) or \
                         self.board.has_queenside_castling_rights(chess.WHITE) or \
                         self.board.has_kingside_castling_rights(chess.BLACK) or \
                         self.board.has_queenside_castling_rights(chess.BLACK)
        
        # Check for developed pieces (knights and bishops off starting squares)
        developed_pieces = 0
        starting_knight_squares = [chess.B1, chess.G1, chess.B8, chess.G8]
        starting_bishop_squares = [chess.C1, chess.F1, chess.C8, chess.F8]
        
        for square in starting_knight_squares + starting_bishop_squares:
            piece = self.board.piece_at(square)
            if not piece or piece.piece_type not in [chess.KNIGHT, chess.BISHOP]:
                developed_pieces += 1
        
        # Phase detection logic
        phase_info = {
            'move_number': move_number,
            'piece_count': piece_count,
            'total_material': total_material,
            'material_balance': material_count['white'] - material_count['black'],
            'queens_on_board': piece_types['white']['queens'] + piece_types['black']['queens'],
            'major_pieces': (piece_types['white']['queens'] + piece_types['white']['rooks'] + 
                           piece_types['black']['queens'] + piece_types['black']['rooks']),
            'minor_pieces': (piece_types['white']['bishops'] + piece_types['white']['knights'] + 
                           piece_types['black']['bishops'] + piece_types['black']['knights']),
            'castling_available': castling_rights,
            'developed_pieces': developed_pieces,
            'piece_breakdown': piece_types
        }
        
        # ENDGAME: Very few pieces left or specific endgame patterns
        if (piece_count <= 10 or  # 10 or fewer pieces total
            total_material <= 20 or  # Low total material
            (piece_types['white']['queens'] == 0 and piece_types['black']['queens'] == 0 and 
             phase_info['major_pieces'] <= 2)):  # No queens and few major pieces
            return 'endgame', phase_info
        
        # OPENING: Early moves with undeveloped pieces
        if (move_number <= 12 and  # First 12 moves
            (developed_pieces <= 4 or castling_rights) and  # Few developed pieces or castling available
            piece_count >= 28):  # Most pieces still on board
            return 'opening', phase_info
        
        # MIDDLEGAME: Everything else
        return 'middlegame', phase_info
    
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
    
    def get_opening_prompt_template(self, color_name: str, phase_info: dict, shown_moves: list, 
                                   failed_moves_text: str, pgn_history: str, opening_name: str,
                                   current_fen: str, current_board_display: str, move_number: int) -> str:
        """Generate opening-specific prompt focusing on development, center control, and king safety."""
        
        development_advice = ""
        if phase_info['developed_pieces'] < 4:
            development_advice = """
🚀 DEVELOPMENT PRIORITIES:
- Knights before bishops (Nf3, Nc3 for White; Nf6, Nc6 for Black)
- Control the center with pawns (e4, d4 for White; e5, d5 for Black)
- Castle early (within first 10-12 moves) for king safety
- Don't move the same piece twice without good reason
- Don't bring queen out too early (target for opponent's pieces)"""
        
        return f"""🚀 PHASE-AWARE AI SYSTEM ACTIVE 🚀
You are a GRANDMASTER chess player (2600+ ELO) playing as {color_name} in the OPENING phase. Your mission: rapid development, center control, and king safety.

{failed_moves_text}
=== GAME HISTORY & CONTEXT ===
{pgn_history}

=== CURRENT POSITION ===
Opening: {opening_name}
Position (FEN): {current_fen}
Move #{move_number}: {color_name} to move

{current_board_display}

=== OPENING PHASE ANALYSIS ===
📊 Position Statistics:
- Pieces developed: {phase_info['developed_pieces']}/8 minor pieces
- Material balance: {phase_info['material_balance']:+d} (positive favors White)
- Castling available: {'Yes' if phase_info['castling_available'] else 'No'}
- Total pieces: {phase_info['piece_count']}/32

{development_advice}

=== MIDDLEGAME PRINCIPLES FOR THIS POSITION ===

DEVELOP YOUR QUEEN:

Bring your queen into the game early but safely—use it to support attacks or control key squares, avoiding exposure to threats.


TO TAKE IS A MISTAKE:

Don't automatically capture if it weakens your position; evaluate if the recapture helps your opponent (e.g., opening files for their rooks).


ACTIVATE YOUR ROOKS:

Get rooks on open files or the 7th rank to pressure the opponent; double them if possible for maximum power.


BREAK OPEN YOUR OPPONENT’S CASTLING:

Use pawn advances or sacrifices to shatter their kingside pawns, exposing the king to attacks.


OPEN A POSITION BY TRADING PAWNS:

Exchange central pawns to create open lines for your pieces, especially if you have better development.


ATTACKERS NEED TO OUTNUMBER DEFENDERS:

When launching an attack on a square or piece, ensure you have more pieces targeting it than they have defending.


TAKE A VICTORY LAP (LEAST ACTIVE PIECE):

Improve your worst-placed piece first—activate it to contribute to the fight (LAP = Least Active Piece).


NEUTRALIZE YOUR OPPONENT’S PIECES ON YOUR TERRITORY:

Trade or drive away enemy pieces that have invaded your side, regaining control of your position.


IF YOU FOUND A BRILLIANT MOVE, THINK TWICE:

Double-check flashy tactics; they might be traps or overlook counterplay—calculate deeper.


USE FORCING MOVES: CHECKS, CAPTURES, AND ATTACKING MOVES:

Prioritize moves that force responses (checks, captures, threats) to dictate the game's pace and create opportunities.

**=== PIECE VALUES & TRADE EVALUATION ===
Standard values: Pawn=1, Knight/Bishop=3, Rook=5, Queen=9, King=infinite (prioritize safety).
- For any potential capture/trade: Calculate net material (your captured value - opponent's). Only trade if net >=0 (e.g., no rook for pawn) or positional compensation (e.g., opens center, attacks king).
- Avoid aggressive trades early; prioritize development over material grabs unless free.**

=== YOUR LEGAL MOVES ===
Available moves: {", ".join(shown_moves)}

=== CANDIDATE MOVE EVALUATION ===
Consider these questions for your top 3 candidate moves:
1. Does this move develop a piece to an active square?
2. Does this move help control the center?
3. Does this move improve king safety or prepare castling?
4. Does this move create any tactical threats?
5. What is opponent's best response to this move?

=== ANTI-BLUNDER CHECK ===
Before deciding: "Am I leaving any pieces undefended? Is my king safe? Am I falling behind in development?"

CRITICAL: Choose a legal move that follows opening principles!

Format your response:
MOVE: [your move in UCI format (e2e4) or algebraic notation (e4, Nf3, O-O)]
REASONING: [75-125 words: Explain your choice based on development, center control, and king safety. Mention your top 2-3 candidate moves and why you chose this one.]

Your move:"""

    def get_middlegame_prompt_template(self, color_name: str, phase_info: dict, shown_moves: list,
                                      failed_moves_text: str, pgn_history: str, opening_name: str,
                                      current_fen: str, current_board_display: str, move_number: int) -> str:
        """Generate middlegame-specific prompt focusing on tactics, strategy, and piece coordination."""
        
        tactical_themes = []
        if phase_info['queens_on_board'] >= 2:
            tactical_themes.append("Queen activity and safety")
        if phase_info['major_pieces'] >= 4:
            tactical_themes.append("Rook coordination and open files")
        if phase_info['minor_pieces'] >= 4:
            tactical_themes.append("Bishop pairs and knight outposts")
            
        return f"""⚔️  PHASE-AWARE AI SYSTEM ACTIVE ⚔️ 
You are a GRANDMASTER chess player (2600+ ELO) playing as {color_name} in the MIDDLEGAME phase. Your mission: tactical execution, strategic planning, and piece coordination.

{failed_moves_text}
=== GAME HISTORY & CONTEXT ===
{pgn_history}

=== CURRENT POSITION ===
Opening: {opening_name}
Position (FEN): {current_fen}
Move #{move_number}: {color_name} to move

{current_board_display}

=== MIDDLEGAME PHASE ANALYSIS ===
📊 Position Statistics:
- Material balance: {phase_info['material_balance']:+d} (positive favors White)
- Queens on board: {phase_info['queens_on_board']}/2
- Major pieces (Q+R): {phase_info['major_pieces']}
- Minor pieces (B+N): {phase_info['minor_pieces']}
- Total pieces: {phase_info['piece_count']}/32

🎯 Key Tactical Themes: {', '.join(tactical_themes) if tactical_themes else 'Piece coordination and pawn structure'}

=== MIDDLEGAME PRINCIPLES FOR THIS POSITION ===
1. **DEVELOP YOUR QUEEN**:
   - Bring your queen into the game early but safely—use it to support attacks or control key squares, avoiding exposure to threats.

2. **TO TAKE IS A MISTAKE**:
   - Don't automatically capture if it weakens your position; evaluate if the recapture helps your opponent (e.g., opening files for their rooks).

3. **ACTIVATE YOUR ROOKS**:
   - Get rooks on open files or the 7th rank to pressure the opponent; double them if possible for maximum power.

4. **BREAK OPEN YOUR OPPONENT’S CASTLING**:
   - Use pawn advances or sacrifices to shatter their kingside pawns, exposing the king to attacks.

5. **OPEN A POSITION BY TRADING PAWNS**:
   - Exchange central pawns to create open lines for your pieces, especially if you have better development.

6. **ATTACKERS NEED TO OUTNUMBER DEFENDERS**:
   - When launching an attack on a square or piece, ensure you have more pieces targeting it than they have defending.

7. **TAKE A VICTORY LAP (LEAST ACTIVE PIECE)**:
   - Improve your worst-placed piece first—activate it to contribute to the fight (LAP = Least Active Piece).

8. **NEUTRALIZE YOUR OPPONENT’S PIECES ON YOUR TERRITORY**:
   - Trade or drive away enemy pieces that have invaded your side, regaining control of your position.

9. **IF YOU FOUND A BRILLIANT MOVE, THINK TWICE**:
   - Double-check flashy tactics; they might be traps or overlook counterplay—calculate deeper.

10. **USE FORCING MOVES: CHECKS, CAPTURES, AND ATTACKING MOVES**:
    - Prioritize moves that force responses (checks, captures, threats) to dictate the game's pace and create opportunities.

**=== PIECE VALUES & TRADE EVALUATION ===
Standard values: Pawn=1, Knight/Bishop=3, Rook=5, Queen=9, King=infinite.
- Before any trade/capture: Compute net material (opponent's value - yours if recaptured). Favor trades only if net >0 (e.g., bishop for pawn bad) or compensation (e.g., weakens king, opens file).
- Avoid aggressive unequal trades; calculate 2-3 moves ahead for recaptures.**

=== YOUR LEGAL MOVES ===
Available moves: {", ".join(shown_moves)}

Your move:"""

    def get_endgame_prompt_template(self, color_name: str, phase_info: dict, shown_moves: list,
                                   failed_moves_text: str, pgn_history: str, opening_name: str,
                                   current_fen: str, current_board_display: str, move_number: int) -> str:
        """Generate endgame-specific prompt focusing on king activity, pawn technique, and precise calculation."""
        
        endgame_type = "Unknown"
        if phase_info['piece_count'] <= 6:
            if phase_info['major_pieces'] == 0 and phase_info['minor_pieces'] == 0:
                endgame_type = "King and Pawn"
            elif phase_info['queens_on_board'] == 0 and phase_info['major_pieces'] <= 2:
                endgame_type = "Rook and Pawn" 
            elif phase_info['major_pieces'] == 0:
                endgame_type = "Minor Piece"
        
        king_activity_advice = """
👑 KING ACTIVITY IS CRUCIAL:
- In endgame, the king becomes a powerful piece
- Centralize your king to control key squares
- Use king to support pawn advances
- King and pawn vs king requires precise technique"""

        return f"""👑 PHASE-AWARE AI SYSTEM ACTIVE 👑
You are a GRANDMASTER chess player (2600+ ELO) playing as {color_name} in the ENDGAME phase. Your mission: precise calculation, king activity, and pawn technique.

{failed_moves_text}
=== GAME HISTORY & CONTEXT ===
{pgn_history}

=== CURRENT POSITION ===
Endgame Type: {endgame_type}
Position (FEN): {current_fen}
Move #{move_number}: {color_name} to move

{current_board_display}

=== ENDGAME PHASE ANALYSIS ===
📊 Position Statistics:
- Material balance: {phase_info['material_balance']:+d} (positive favors White)
- Total pieces remaining: {phase_info['piece_count']}/32
- Queens: {phase_info['queens_on_board']}, Rooks: {phase_info['major_pieces'] - phase_info['queens_on_board']}
- Bishops + Knights: {phase_info['minor_pieces']}
- Pawns: {phase_info['piece_breakdown']['white']['pawns'] + phase_info['piece_breakdown']['black']['pawns']}

{king_activity_advice}

=== MIDDLEGAME PRINCIPLES FOR THIS POSITION ===
1. **DEVELOP YOUR QUEEN**:
   - Bring your queen into the game early but safely—use it to support attacks or control key squares, avoiding exposure to threats.

2. **TO TAKE IS A MISTAKE**:
   - Don't automatically capture if it weakens your position; evaluate if the recapture helps your opponent (e.g., opening files for their rooks).

3. **ACTIVATE YOUR ROOKS**:
   - Get rooks on open files or the 7th rank to pressure the opponent; double them if possible for maximum power.

4. **BREAK OPEN YOUR OPPONENT’S CASTLING**:
   - Use pawn advances or sacrifices to shatter their kingside pawns, exposing the king to attacks.

5. **OPEN A POSITION BY TRADING PAWNS**:
   - Exchange central pawns to create open lines for your pieces, especially if you have better development.

6. **ATTACKERS NEED TO OUTNUMBER DEFENDERS**:
   - When launching an attack on a square or piece, ensure you have more pieces targeting it than they have defending.

7. **TAKE A VICTORY LAP (LEAST ACTIVE PIECE)**:
   - Improve your worst-placed piece first—activate it to contribute to the fight (LAP = Least Active Piece).

8. **NEUTRALIZE YOUR OPPONENT’S PIECES ON YOUR TERRITORY**:
   - Trade or drive away enemy pieces that have invaded your side, regaining control of your position.

9. **IF YOU FOUND A BRILLIANT MOVE, THINK TWICE**:
   - Double-check flashy tactics; they might be traps or overlook counterplay—calculate deeper.

10. **USE FORCING MOVES: CHECKS, CAPTURES, AND ATTACKING MOVES**:
    - Prioritize moves that force responses (checks, captures, threats) to dictate the game's pace and create opportunities.

**=== PIECE VALUES & TRADE EVALUATION ===
Standard values: Pawn=1, Knight/Bishop=3, Rook=5, Queen=9, King=infinite.
- Before any trade/capture: Compute net material (opponent's value - yours if recaptured). Favor trades only if net >0 (e.g., bishop for pawn bad) or compensation (e.g., weakens king, opens file).
- Avoid aggressive unequal trades; calculate 2-3 moves ahead for recaptures.**

**=== PIECE VALUES & TRADE EVALUATION ===
Standard values: Pawn=1 (add +1-3 if passed/near promotion), Knight/Bishop=3, Rook=5, Queen=9, King=infinite.
- For trades/captures: Calculate net material, factoring pawn potential. Avoid down-trades (e.g., rook for pawn) unless it creates a winning passer.
- Attack Safety: Ensure moves to new squares are protected; count king as extra defender in endgames.**

=== YOUR LEGAL MOVES ===
Available moves: {", ".join(shown_moves)}

Format your response:
MOVE: [your move in UCI format (e2e4) or algebraic notation (e4, Nf3, O-O)]
REASONING: [75-125 words: Explain your choice based on king activity, pawn technique, and concrete calculation. Mention your top 2-3 candidate moves and why you chose this one.]

Your move:"""
