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
            # Call the appropriate API
            print(f"DEBUG: Game calling API for {player_name} with model {config['model']}")
            print(f"DEBUG: Prompt length: {len(prompt)} characters")
            print(f"DEBUG: First 100 chars of prompt: {prompt[:100]}...")
            
            response = config['api_function'](
                prompt, 
                config['api_key'],
                config['model']
            )
            
            print(f"DEBUG: API response length: {len(response) if response else 0}")
            if response:
                print(f"DEBUG: First 100 chars of response: {response[:100]}...")
            else:
                print("DEBUG: No response received from API")
            
            if not response:
                return None, "No response received from API"
            
            # Parse the action from response
            action = self.parse_action_from_response(response)
            reasoning = extract_reasoning(response)
            
            if not action:
                return None, f"Could not parse action from response: {response[:100]}..."
            
            return action, reasoning
            
        except Exception as e:
            return None, f"Error calling API: {str(e)}"
    
    def make_move(self) -> bool:
        """
        Make a move for the current player.
        
        Returns:
            True if move was successful, False if game should end
        """
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
                # Move was successful
                self.next_player()
                print(f"DEBUG: Move {action} successful, switched to {self.current_player}")
                try:
                    from debug_console import debug_log
                    debug_log(f"SUCCESS: Move {action} applied, switched to {self.current_player}")
                except:
                    pass
                return True
            else:
                # Invalid move, try again
                print(f"DEBUG: Move {action} invalid, attempt {attempt + 1}/{max_attempts}")
                try:
                    from debug_console import debug_log
                    debug_log(f"FAILED: Move {action} invalid, attempt {attempt + 1}/{max_attempts}")
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
