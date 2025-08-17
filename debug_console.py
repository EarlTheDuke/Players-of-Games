"""Debug console for capturing and displaying debug messages."""
import threading
from collections import deque
from datetime import datetime

class DebugConsole:
    """Thread-safe debug console for capturing debug messages."""
    
    def __init__(self, max_messages=50):
        self.messages = deque(maxlen=max_messages)
        self.lock = threading.Lock()
    
    def log(self, message: str, level: str = "DEBUG"):
        """Add a debug message to the console."""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.messages.append({
                'timestamp': timestamp,
                'level': level,
                'message': message
            })
    
    def get_messages(self, last_n: int = 20):
        """Get the last N debug messages."""
        with self.lock:
            return list(self.messages)[-last_n:]
    
    def clear(self):
        """Clear all debug messages."""
        with self.lock:
            self.messages.clear()

# Global debug console instance
debug_console = DebugConsole()

def debug_log(message: str, level: str = "DEBUG"):
    """Log a debug message to the global console."""
    debug_console.log(message, level)
    print(f"{level}: {message}")  # Also print to server logs
