"""
Comprehensive logging configuration for Karma backend.
Provides structured logging with colors for console and JSON for files.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Icons for different log levels
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color and icon
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Format the message
        log_message = super().format(record)
        
        # Add color if terminal supports it
        if sys.stdout.isatty():
            return f"{color}{icon} {log_message}{self.RESET}"
        return f"{icon} {log_message}"


class JSONFormatter(logging.Formatter):
    """JSON formatter for file logging - easy to parse and analyze."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data
            
        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup comprehensive logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        log_file: Custom log file path (default: logs/karma_YYYY-MM-DD.log)
    
    Returns:
        Configured root logger
    """
    # Get the root logger for the app
    logger = logging.getLogger("karma")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = ColoredFormatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with JSON format
    if log_to_file:
        if log_file is None:
            log_file = LOGS_DIR / f"karma_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        # Also create a human-readable log
        readable_log = LOGS_DIR / f"karma_{datetime.now().strftime('%Y-%m-%d')}_readable.log"
        readable_handler = logging.FileHandler(readable_log, encoding='utf-8')
        readable_handler.setLevel(logging.DEBUG)
        readable_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
        ))
        logger.addHandler(readable_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Usage:
        from app.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(f"karma.{name}")


# Create module-specific loggers
def get_api_logger() -> logging.Logger:
    """Logger for API routes."""
    return get_logger("api")


def get_db_logger() -> logging.Logger:
    """Logger for database operations."""
    return get_logger("database")


def get_ai_logger() -> logging.Logger:
    """Logger for AI/agent operations."""
    return get_logger("ai")


def get_auth_logger() -> logging.Logger:
    """Logger for authentication."""
    return get_logger("auth")


# Helper function to log with extra data
def log_with_data(logger: logging.Logger, level: str, message: str, **data):
    """
    Log a message with additional structured data.
    
    Usage:
        log_with_data(logger, "info", "Task created", task_id="123", user="john")
    """
    record = logger.makeRecord(
        logger.name,
        getattr(logging, level.upper()),
        "",
        0,
        message,
        (),
        None
    )
    record.extra_data = data
    logger.handle(record)

