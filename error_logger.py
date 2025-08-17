"""Robust error and bug logging system for Players of Games."""
import os
import json
import traceback
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from collections import deque
from enum import Enum


class ErrorLevel(Enum):
    """Error severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories for better organization."""
    API_ERROR = "API_ERROR"
    GAME_LOGIC = "GAME_LOGIC"
    UI_ERROR = "UI_ERROR"
    VALIDATION = "VALIDATION"
    NETWORK = "NETWORK"
    PARSING = "PARSING"
    SYSTEM = "SYSTEM"
    USER_ACTION = "USER_ACTION"


class ErrorLogger:
    """Comprehensive error logging system with file output and memory storage."""
    
    def __init__(self, log_dir: str = "error_logs", max_memory_logs: int = 1000):
        """
        Initialize the error logger.
        
        Args:
            log_dir: Directory to store log files
            max_memory_logs: Maximum number of logs to keep in memory
        """
        self.log_dir = log_dir
        self.max_memory_logs = max_memory_logs
        self.memory_logs = deque(maxlen=max_memory_logs)
        self.error_counts = {}
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.lock = threading.Lock()
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize session log file
        self.session_log_file = os.path.join(log_dir, f"session_{self.session_id}.json")
        self.daily_log_file = os.path.join(log_dir, f"daily_{datetime.now().strftime('%Y%m%d')}.json")
        
        # Log session start
        self.log(ErrorLevel.INFO, ErrorCategory.SYSTEM, "Error logging system initialized", 
                {"session_id": self.session_id, "log_dir": log_dir})
    
    def log(self, level: ErrorLevel, category: ErrorCategory, message: str, 
            context: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None):
        """
        Log an error or event.
        
        Args:
            level: Error severity level
            category: Error category
            message: Error message
            context: Additional context information
            exception: Exception object if available
        """
        with self.lock:
            timestamp = datetime.now()
            
            # Create log entry
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "session_id": self.session_id,
                "level": level.value,
                "category": category.value,
                "message": message,
                "context": context or {},
                "exception_info": None
            }
            
            # Add exception information if provided
            if exception:
                log_entry["exception_info"] = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "traceback": traceback.format_exc()
                }
            
            # Add to memory logs
            self.memory_logs.append(log_entry)
            
            # Update error counts
            count_key = f"{level.value}_{category.value}"
            self.error_counts[count_key] = self.error_counts.get(count_key, 0) + 1
            
            # Write to files
            self._write_to_file(log_entry)
            
            # Print to console for immediate visibility
            self._print_log(log_entry)
    
    def _write_to_file(self, log_entry: Dict[str, Any]):
        """Write log entry to files."""
        try:
            # Write to session log
            with open(self.session_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            # Write to daily log
            with open(self.daily_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"ERROR: Failed to write log to file: {e}")
    
    def _print_log(self, log_entry: Dict[str, Any]):
        """Print log entry to console with formatting."""
        timestamp = log_entry["timestamp"][:19]  # Remove microseconds
        level = log_entry["level"]
        category = log_entry["category"]
        message = log_entry["message"]
        
        # Color coding for different levels
        colors = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "CRITICAL": "\033[35m"  # Magenta
        }
        reset_color = "\033[0m"
        
        color = colors.get(level, "")
        print(f"{color}[{timestamp}] {level} | {category} | {message}{reset_color}")
        
        # Print exception info if available
        if log_entry.get("exception_info"):
            print(f"  Exception: {log_entry['exception_info']['type']}: {log_entry['exception_info']['message']}")
        
        # Print context if available
        if log_entry.get("context"):
            print(f"  Context: {log_entry['context']}")
    
    def get_logs(self, level_filter: Optional[ErrorLevel] = None, 
                 category_filter: Optional[ErrorCategory] = None,
                 last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get logs with optional filtering.
        
        Args:
            level_filter: Filter by error level
            category_filter: Filter by error category
            last_n: Return only last N logs
        
        Returns:
            List of log entries
        """
        with self.lock:
            logs = list(self.memory_logs)
            
            # Apply filters
            if level_filter:
                logs = [log for log in logs if log["level"] == level_filter.value]
            
            if category_filter:
                logs = [log for log in logs if log["category"] == category_filter.value]
            
            # Return last N logs
            if last_n:
                logs = logs[-last_n:]
            
            return logs
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors and statistics."""
        with self.lock:
            total_logs = len(self.memory_logs)
            
            # Count by level
            level_counts = {}
            category_counts = {}
            
            for log in self.memory_logs:
                level = log["level"]
                category = log["category"]
                
                level_counts[level] = level_counts.get(level, 0) + 1
                category_counts[category] = category_counts.get(category, 0) + 1
            
            return {
                "session_id": self.session_id,
                "total_logs": total_logs,
                "level_counts": level_counts,
                "category_counts": category_counts,
                "error_counts": self.error_counts.copy(),
                "session_duration": (datetime.now() - datetime.fromisoformat(self.session_id.replace('_', 'T').replace('T', ' ', 1))).total_seconds() if self.session_id else 0
            }
    
    def export_logs(self, filename: Optional[str] = None, 
                   level_filter: Optional[ErrorLevel] = None,
                   category_filter: Optional[ErrorCategory] = None) -> str:
        """
        Export logs to a JSON file.
        
        Args:
            filename: Output filename (optional)
            level_filter: Filter by error level
            category_filter: Filter by error category
        
        Returns:
            Path to the exported file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_export_{timestamp}.json"
        
        filepath = os.path.join(self.log_dir, filename)
        
        # Get filtered logs
        logs = self.get_logs(level_filter, category_filter)
        
        # Add summary information
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "summary": self.get_error_summary(),
            "logs": logs
        }
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def clear_logs(self):
        """Clear all logs from memory."""
        with self.lock:
            self.memory_logs.clear()
            self.error_counts.clear()
            self.log(ErrorLevel.INFO, ErrorCategory.SYSTEM, "Logs cleared")


# Global error logger instance
error_logger = ErrorLogger()


# Convenience functions
def log_error(message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
              context: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None):
    """Log an error."""
    error_logger.log(ErrorLevel.ERROR, category, message, context, exception)


def log_warning(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
                context: Optional[Dict[str, Any]] = None):
    """Log a warning."""
    error_logger.log(ErrorLevel.WARNING, category, message, context)


def log_info(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
             context: Optional[Dict[str, Any]] = None):
    """Log an info message."""
    error_logger.log(ErrorLevel.INFO, category, message, context)


def log_debug(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
              context: Optional[Dict[str, Any]] = None):
    """Log a debug message."""
    error_logger.log(ErrorLevel.DEBUG, category, message, context)


def log_critical(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
                 context: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None):
    """Log a critical error."""
    error_logger.log(ErrorLevel.CRITICAL, category, message, context, exception)


# Decorator for automatic error logging
def log_exceptions(category: ErrorCategory = ErrorCategory.SYSTEM):
    """Decorator to automatically log exceptions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(
                    f"Exception in {func.__name__}: {str(e)}",
                    category,
                    {"function": func.__name__, "args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                    e
                )
                raise
        return wrapper
    return decorator
