"""Enhanced debug console for comprehensive real-time debugging and game history tracking."""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import os
import threading
from collections import deque

# Message categories for filtering and analysis
class DebugLevel:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    VALIDATION = "VALIDATION"
    API = "API"
    GAME = "GAME"
    SESSION = "SESSION"
    MOVE = "MOVE"

class EnhancedDebugConsole:
    """Thread-safe enhanced debug console with categorization and persistent logging."""
    
    def __init__(self, max_messages=500):  # Increased capacity
        self.messages = deque(maxlen=max_messages)
        self.error_counts = {}
        self.session_id = None
        self.game_id = None
        self.lock = threading.Lock()
    
    def set_session_info(self, session_id: str, game_id: str = None):
        """Set session and game identifiers."""
        with self.lock:
            self.session_id = session_id
            self.game_id = game_id
    
    def log(self, message: str, level: str = DebugLevel.INFO, category: str = "GENERAL", 
            player: str = None, move_number: int = None):
        """Add a comprehensive debug message."""
        with self.lock:
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
            
            # Create structured message
            structured_msg = {
                "timestamp": timestamp.isoformat(),
                "timestamp_display": timestamp_str,
                "level": level,
                "category": category,
                "message": message,
                "session_id": self.session_id,
                "game_id": self.game_id,
                "player": player,
                "move_number": move_number
            }
            
            # Format for display with emojis
            level_emoji = {
                DebugLevel.INFO: "ℹ️",
                DebugLevel.WARNING: "⚠️", 
                DebugLevel.ERROR: "❌",
                DebugLevel.VALIDATION: "🔍",
                DebugLevel.API: "🌐",
                DebugLevel.GAME: "♟️",
                DebugLevel.SESSION: "🔄",
                DebugLevel.MOVE: "🎯"
            }
            
            emoji = level_emoji.get(level, "📝")
            category_prefix = f"[{category}]" if category != "GENERAL" else ""
            player_prefix = f"P{player[-1]}" if player else ""
            move_prefix = f"M{move_number}" if move_number else ""
            
            prefixes = " ".join(filter(None, [player_prefix, move_prefix, category_prefix]))
            prefix_str = f" {prefixes}" if prefixes else ""
            
            formatted_message = f"[{timestamp_str}] {emoji}{prefix_str} {message}"
            
            self.messages.append({
                "formatted": formatted_message,
                "structured": structured_msg
            })
            
            # Track error counts
            if level == DebugLevel.ERROR:
                error_key = f"{category}_{player}" if player else category
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Also print to server logs for debugging
            print(formatted_message)
    
    def get_messages(self, level_filter: Optional[str] = None, 
                    category_filter: Optional[str] = None,
                    player_filter: Optional[str] = None,
                    last_n: int = None) -> List[str]:
        """Get debug messages with comprehensive filtering."""
        with self.lock:
            messages = []
            for msg_data in self.messages:
                structured = msg_data["structured"]
                
                # Apply filters
                if level_filter and structured["level"] != level_filter:
                    continue
                if category_filter and structured["category"] != category_filter:
                    continue
                if player_filter and structured.get("player") != player_filter:
                    continue
                if self.session_id and structured.get("session_id") != self.session_id:
                    continue
                    
                messages.append(msg_data["formatted"])
            
            # Return last N messages if specified
            if last_n:
                return messages[-last_n:]
            return messages
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts by category."""
        with self.lock:
            return self.error_counts.copy()
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """Get comprehensive game statistics."""
        with self.lock:
            stats = {
                "total_messages": len(self.messages),
                "session_id": self.session_id,
                "game_id": self.game_id,
                "error_counts": self.error_counts.copy(),
                "message_counts_by_level": {},
                "message_counts_by_category": {},
                "last_10_errors": []
            }
            
            # Count messages by level and category
            for msg_data in self.messages:
                structured = msg_data["structured"]
                level = structured["level"]
                category = structured["category"]
                
                stats["message_counts_by_level"][level] = stats["message_counts_by_level"].get(level, 0) + 1
                stats["message_counts_by_category"][category] = stats["message_counts_by_category"].get(category, 0) + 1
                
                # Collect recent errors
                if level == DebugLevel.ERROR and len(stats["last_10_errors"]) < 10:
                    stats["last_10_errors"].append({
                        "timestamp": structured["timestamp_display"],
                        "category": category,
                        "message": structured["message"],
                        "player": structured.get("player")
                    })
            
            return stats
    
    def clear(self):
        """Clear all debug messages and reset counters."""
        with self.lock:
            self.messages.clear()
            self.error_counts.clear()
    
    def export_session_log(self) -> str:
        """Export complete session log as JSON string."""
        with self.lock:
            export_data = {
                "session_id": self.session_id,
                "game_id": self.game_id,
                "export_time": datetime.now().isoformat(),
                "messages": [msg["structured"] for msg in self.messages],
                "statistics": self.get_game_statistics(),
                "total_messages": len(self.messages)
            }
            
            return json.dumps(export_data, indent=2)
    
    def save_game_log(self, filename: str = None) -> str:
        """Save complete game log to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            game_suffix = f"_{self.game_id}" if self.game_id else ""
            filename = f"game_log_{timestamp}{game_suffix}.json"
        
        log_data = self.export_session_log()
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        filepath = os.path.join("logs", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(log_data)
        
        return filepath

# Global debug console instance
debug_console = EnhancedDebugConsole()

# Convenience functions for backward compatibility and ease of use
def debug_log(message: str, level: str = DebugLevel.INFO, category: str = "GENERAL", 
              player: str = None, move_number: int = None):
    """Log a debug message to the global console."""
    debug_console.log(message, level, category, player, move_number)

def get_messages(level_filter: str = None, category_filter: str = None, 
                player_filter: str = None, last_n: int = 50) -> List[str]:
    """Get filtered debug messages."""
    return debug_console.get_messages(level_filter, category_filter, player_filter, last_n)

def clear():
    """Clear all debug messages."""
    debug_console.clear()

def set_session_info(session_id: str, game_id: str = None):
    """Set session and game identifiers."""
    debug_console.set_session_info(session_id, game_id)

def get_error_summary() -> Dict[str, int]:
    """Get error summary."""
    return debug_console.get_error_summary()

def get_game_statistics() -> Dict[str, Any]:
    """Get comprehensive game statistics."""
    return debug_console.get_game_statistics()

def export_session_log() -> str:
    """Export session log as JSON."""
    return debug_console.export_session_log()

def save_game_log(filename: str = None) -> str:
    """Save game log to file."""
    return debug_console.save_game_log(filename)