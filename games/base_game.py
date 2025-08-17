"""Abstract base class for game implementations."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import random
from logger import GameLogger
from api_utils import get_api_function, extract_reasoning
import config


class BaseGame(ABC):
    """Abstract base class for all game implementations."""
    
    def __init__(self, players: Dict[str, str], log_to_file: bool = True):
        """
        Initialize the game.
        
        Args:
            players: Dictionary mapping player names to model types
                    e.g., {'player1': 'grok', 'player2': 'claude'}
            log_to_file: Whether to log game to file
        """
        self.players = players
        self.player_list = list(players.keys())
        self.current_player_index = 0
        self.move_count = 0
        self.game_over = False
        self.winner = None
        self.result = None
        
        # Set up API keys for each player
        self.player_configs = {}
        for player_name, model_type in players.items():
            api_key = config.GROK_API_KEY if model_type.lower() == 'grok' else config.CLAUDE_API_KEY
            # Use the actual model names from config, not the player type
            actual_model = config.GROK_MODEL if model_type.lower() == 'grok' else config.CLAUDE_MODEL
            self.player_configs[player_name] = {
                'model': actual_model,  # Use actual model name like "grok-2-1212"
                'api_key': api_key,
                'api_function': get_api_function(model_type)
            }
        
        # Initialize logger
        self.logger = GameLogger(self.get_game_name(), log_to_file)
        
        # Track failed moves to prevent AI from repeating the same mistakes
        self.failed_moves = {player: set() for player in players.keys()}
        
        # Add termination flag for clean shutdown
        self._terminated = False
        
        # Add game instance ID for collision detection
        import uuid
        self.instance_id = str(uuid.uuid4())[:8]
        
    @property
    def current_player(self) -> str:
        """Get the current player name."""
        return self.player_list[self.current_player_index]
    
    def next_player(self):
        """Switch to the next player."""
        self.current_player_index = (self.current_player_index + 1) % len(self.player_list)
    
    @abstractmethod
    def get_game_name(self) -> str:
        """Return the name of the game."""
        pass
    
    @abstractmethod
    def get_state_text(self) -> str:
        """Return a text representation of the current game state."""
        pass
    
    @abstractmethod
    def get_state_display(self) -> str:
        """Return a human-readable display of the current game state."""
        pass
    
    @abstractmethod
    def get_legal_actions(self) -> List[str]:
        """Return a list of legal actions in the current state."""
        pass
    
    @abstractmethod
    def is_game_over(self) -> bool:
        """Check if the game is over."""
        pass
    
    @abstractmethod
    def get_game_result(self) -> Tuple[str, Optional[str]]:
        """
        Get the game result.
        
        Returns:
            Tuple of (result_type, winner) where result_type is 'win', 'draw', etc.
        """
        pass
    
    @abstractmethod
    def validate_and_apply_action(self, action: str) -> bool:
        """
        Validate and apply an action to the game state.
        
        Args:
            action: The action to validate and apply
            
        Returns:
            True if action was valid and applied, False otherwise
        """
        pass
    
    @abstractmethod
    def get_prompt(self) -> str:
        """Generate a prompt for the current player."""
        pass
    
    @abstractmethod
    def parse_action_from_response(self, response: str) -> Optional[str]:
        """
        Parse an action from the AI's response.
        
        Args:
            response: The AI's response text
            
        Returns:
            Parsed action or None if parsing failed
        """
        pass
    
    def prompt_player(self) -> Tuple[Optional[str], str]:
        """
        Prompt the current player for their move.
        
        Returns:
            Tuple of (action, reasoning) or (None, error_message) if failed
        """
        player_name = self.current_player
        config = self.player_configs[player_name]
        
        prompt = self.get_prompt()
        
        try:
            from debug_console import debug_log, DebugLevel
            
            # 🔍 STEP 1: API Call Setup
            debug_log(f"🌐 API CALL START: {player_name} using {config['model']}", 
                     DebugLevel.API, "API_START", player_name, self.move_count + 1)
            debug_log(f"🌐 Prompt length: {len(prompt)} chars", 
                     DebugLevel.API, "API_START", player_name, self.move_count + 1)
            debug_log(f"🌐 Prompt preview: {prompt[:150]}...", 
                     DebugLevel.API, "API_START", player_name, self.move_count + 1)
            
            # 🔍 STEP 2: Make API Call
            import time
            start_time = time.time()
            
            response = config['api_function'](
                prompt, 
                config['api_key'],
                config['model']
            )
            
            call_duration = time.time() - start_time
            
            # 🔍 STEP 3: API Response Analysis
            if response:
                debug_log(f"✅ API SUCCESS: Response received in {call_duration:.2f}s", 
                         DebugLevel.API, "API_SUCCESS", player_name, self.move_count + 1)
                debug_log(f"✅ Response length: {len(response)} chars", 
                         DebugLevel.API, "API_SUCCESS", player_name, self.move_count + 1)
                debug_log(f"✅ Response preview: {response[:200]}...", 
                         DebugLevel.API, "API_SUCCESS", player_name, self.move_count + 1)
                
                # Check if response contains expected patterns
                has_move_prefix = "MOVE:" in response.upper()
                has_reasoning_prefix = "REASONING:" in response.upper()
                debug_log(f"✅ Response patterns: MOVE={has_move_prefix}, REASONING={has_reasoning_prefix}", 
                         DebugLevel.API, "API_SUCCESS", player_name, self.move_count + 1)
                
            else:
                debug_log(f"❌ API FAILURE: No response after {call_duration:.2f}s", 
                         DebugLevel.ERROR, "API_FAILURE", player_name, self.move_count + 1)
                return None, f"No response received from {config['model']} API after {call_duration:.2f}s"
            
            # 🔍 STEP 4: Parse Action from Response
            debug_log(f"🔍 PARSING START: Extracting move from response", 
                     DebugLevel.API, "PARSE_START", player_name, self.move_count + 1)
            
            action = self.parse_action_from_response(response)
            
            # Import extract_reasoning function
            from api_utils import extract_reasoning
            reasoning = extract_reasoning(response)
            
            # 🔍 STEP 5: Parsing Results Analysis
            if action:
                debug_log(f"✅ PARSING SUCCESS: Extracted move '{action}'", 
                         DebugLevel.API, "PARSE_SUCCESS", player_name, self.move_count + 1)
                debug_log(f"✅ Reasoning extracted: {len(reasoning)} chars", 
                         DebugLevel.API, "PARSE_SUCCESS", player_name, self.move_count + 1)
                return action, reasoning
            else:
                # 🔍 DETAILED PARSING FAILURE ANALYSIS
                debug_log(f"❌ PARSING FAILURE: Could not extract move", 
                         DebugLevel.ERROR, "PARSE_FAILURE", player_name, self.move_count + 1)
                debug_log(f"❌ FULL RESPONSE FOR ANALYSIS: {response}", 
                         DebugLevel.ERROR, "PARSE_FAILURE", player_name, self.move_count + 1)
                
                # Check for common parsing issues
                response_upper = response.upper()
                if "MOVE:" not in response_upper:
                    debug_log(f"❌ MISSING MOVE PREFIX: Response lacks 'MOVE:' prefix", 
                             DebugLevel.ERROR, "PARSE_FAILURE", player_name, self.move_count + 1)
                
                if len(response.strip()) < 10:
                    debug_log(f"❌ RESPONSE TOO SHORT: Only {len(response.strip())} chars", 
                             DebugLevel.ERROR, "PARSE_FAILURE", player_name, self.move_count + 1)
                
                # Look for potential moves in the response
                import re
                potential_moves = re.findall(r'\b[a-h][1-8][a-h][1-8]\b', response.lower())
                if potential_moves:
                    debug_log(f"❌ FOUND POTENTIAL UCI MOVES: {potential_moves} but parser missed them", 
                             DebugLevel.WARNING, "PARSE_FAILURE", player_name, self.move_count + 1)
                
                potential_san = re.findall(r'\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][=QRBN]?[+#]?\b', response)
                if potential_san:
                    debug_log(f"❌ FOUND POTENTIAL SAN MOVES: {potential_san} but parser missed them", 
                             DebugLevel.WARNING, "PARSE_FAILURE", player_name, self.move_count + 1)
                
                return None, f"Could not parse action from {config['model']} response (see debug log for full response)"
            
        except Exception as e:
            try:
                from debug_console import debug_log, DebugLevel
                debug_log(f"❌ API EXCEPTION: {str(e)}", 
                         DebugLevel.ERROR, "API_EXCEPTION", player_name, self.move_count + 1)
                debug_log(f"❌ Exception type: {type(e).__name__}", 
                         DebugLevel.ERROR, "API_EXCEPTION", player_name, self.move_count + 1)
            except:
                pass
            return None, f"Error calling {config['model']} API: {str(e)}"
    
    def terminate(self):
        """Terminate this game instance cleanly."""
        self._terminated = True
        try:
            from debug_console import debug_log, DebugLevel
            debug_log(f"🛑 GAME TERMINATED: Instance {self.instance_id}", 
                     DebugLevel.SESSION, "TERMINATION")
        except:
            pass
    
    def is_terminated(self) -> bool:
        """Check if this game instance has been terminated."""
        return self._terminated
    
    def make_move(self) -> bool:
        """
        Make a move for the current player.
        
        Returns:
            True if move was successful, False if game should end
        """
        # Check for termination before making moves
        if self._terminated:
            try:
                from debug_console import debug_log, DebugLevel
                debug_log(f"🛑 MOVE BLOCKED: Game {self.instance_id} is terminated", 
                         DebugLevel.WARNING, "TERMINATION")
            except:
                pass
            return False
            
        player_name = self.current_player
        max_attempts = 3
        
        # Check if we have legal moves before starting
        legal_actions = self.get_legal_actions()
        if not legal_actions:
            self.logger.log_error("no_legal_moves", "No legal moves available - game should end")
            return False
        
        print(f"DEBUG: Making move for {player_name}, {len(legal_actions)} legal moves available")
        try:
            from debug_console import debug_log
            debug_log(f"Making move for {player_name}, {len(legal_actions)} legal moves available")
        except:
            pass
        
        for attempt in range(max_attempts):
            # Log move attempt
            try:
                from debug_console import debug_log, DebugLevel
                debug_log(f"Move attempt {attempt + 1}/{max_attempts} for {player_name}", 
                         DebugLevel.MOVE, "ATTEMPT", player_name, self.move_count + 1)
            except:
                pass
                
            # Get move from AI
            action, reasoning = self.prompt_player()
            
            if action is None:
                self.logger.log_error(
                    "api_error", 
                    reasoning,
                    {"player": player_name, "attempt": attempt + 1}
                )
                
                if attempt == max_attempts - 1:
                    # Final attempt failed, use random move
                    legal_actions = self.get_legal_actions()
                    if legal_actions:
                        action = random.choice(legal_actions)
                        reasoning = f"Random fallback move after {max_attempts} failed attempts"
                        self.logger.log_error(
                            "fallback_move",
                            f"Using random move: {action}",
                            {"player": player_name}
                        )
                    else:
                        self.logger.log_error("no_legal_moves", "No legal moves available")
                        return False
                else:
                    continue
            
            # Validate and apply the action
            self.move_count += 1
            is_valid = self.validate_and_apply_action(action)
            
            # Log the move
            self.logger.log_move(
                player=player_name,
                move=action,
                reasoning=reasoning,
                game_state=self.get_state_text(),
                move_number=self.move_count,
                is_valid=is_valid
            )
            
            if is_valid:
                # Move was successful - clear failed moves for this player
                self.failed_moves[player_name].clear()
                self.next_player()
                print(f"DEBUG: Move {action} successful, switched to {self.current_player}")
                
                try:
                    from debug_console import debug_log, DebugLevel
                    debug_log(f"✅ MOVE SUCCESS: {action} by {player_name}", 
                             DebugLevel.MOVE, "SUCCESS", player_name, self.move_count)
                    debug_log(f"Reasoning: {reasoning[:100]}...", 
                             DebugLevel.MOVE, "REASONING", player_name, self.move_count)
                    debug_log(f"Next player: {self.current_player}", 
                             DebugLevel.MOVE, "TURN_SWITCH", player_name, self.move_count)
                except:
                    pass
                return True
            else:
                # Invalid move, track it and try again
                self.failed_moves[player_name].add(action)
                print(f"DEBUG: Move {action} invalid, attempt {attempt + 1}/{max_attempts}")
                print(f"DEBUG: Failed moves for {player_name}: {list(self.failed_moves[player_name])}")
                
                try:
                    from debug_console import debug_log, DebugLevel
                    debug_log(f"❌ MOVE FAILED: {action} by {player_name} (attempt {attempt + 1})", 
                             DebugLevel.ERROR, "MOVE_ERROR", player_name, self.move_count + 1)
                    debug_log(f"Failed moves history: {list(self.failed_moves[player_name])}", 
                             DebugLevel.WARNING, "FAILED_HISTORY", player_name, self.move_count + 1)
                except:
                    pass
                if attempt == max_attempts - 1:
                    # All attempts failed - this shouldn't happen with our fixes
                    self.logger.log_error(
                        "invalid_moves",
                        f"Player {player_name} made {max_attempts} invalid moves",
                        {"last_move": action, "legal_moves": legal_actions[:5]}
                    )
                    # Try one random move as absolute fallback
                    random_move = random.choice(legal_actions)
                    print(f"DEBUG: Forcing random legal move: {random_move}")
                    if self.validate_and_apply_action(random_move):
                        self.logger.log_move(
                            player=player_name,
                            move=random_move,
                            reasoning="Emergency fallback: random legal move",
                            game_state=self.get_state_text(),
                            move_number=self.move_count,
                            is_valid=True
                        )
                        self.next_player()
                        return True
                    return False
        
        return False
    
    def play(self) -> Dict[str, Any]:
        """
        Play the complete game.
        
        Returns:
            Dictionary containing game results
        """
        # Log game start
        self.logger.log_game_start(
            players=self.players,
            initial_state=self.get_state_display()
        )
        
        # Main game loop
        while not self.is_game_over():
            success = self.make_move()
            if not success:
                # Game ended due to error
                self.logger.log_game_end(
                    result="error",
                    final_state=self.get_state_display(),
                    total_moves=self.move_count
                )
                return {
                    "result": "error",
                    "winner": None,
                    "total_moves": self.move_count,
                    "game_history": self.logger.game_history
                }
        
        # Game ended normally
        result_type, winner = self.get_game_result()
        
        self.logger.log_game_end(
            result=result_type,
            winner=winner,
            final_state=self.get_state_display(),
            total_moves=self.move_count
        )
        
        return {
            "result": result_type,
            "winner": winner,
            "total_moves": self.move_count,
            "game_history": self.logger.game_history,
            "final_state": self.get_state_display()
        }
