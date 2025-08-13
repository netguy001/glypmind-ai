"""
Comprehensive logging system for GlyphMind AI
Handles system logging, error tracking, and audit trails
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json

class GlyphMindLogger:
    """Custom logger for GlyphMind AI with multiple handlers"""
    
    def __init__(self, log_dir: str = None):
        # Use data directory for persistent storage on Render
        if log_dir is None:
            log_dir = os.environ.get("DATA_DIR", "data")
            log_dir = os.path.join(log_dir, "logs")
        
        self.log_dir = Path(log_dir)
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Fallback to current directory if we can't create the data directory
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
        
        # Create different log files
        self.main_log = self.log_dir / "glyphmind.log"
        self.error_log = self.log_dir / "errors.log"
        self.evolution_log = self.log_dir / "evolution.log"
        self.search_log = self.log_dir / "search.log"
        self.api_log = self.log_dir / "api.log"
        
        self._setup_loggers()
        
    def _setup_loggers(self):
        """Setup different loggers for different purposes"""
        
        # Main logger
        self.main_logger = self._create_logger(
            "glyphmind.main",
            self.main_log,
            logging.INFO
        )
        
        # Error logger
        self.error_logger = self._create_logger(
            "glyphmind.error",
            self.error_log,
            logging.ERROR
        )
        
        # Evolution logger
        self.evolution_logger = self._create_logger(
            "glyphmind.evolution",
            self.evolution_log,
            logging.INFO
        )
        
        # Search logger
        self.search_logger = self._create_logger(
            "glyphmind.search",
            self.search_log,
            logging.INFO
        )
        
        # API logger
        self.api_logger = self._create_logger(
            "glyphmind.api",
            self.api_log,
            logging.INFO
        )
        
    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """Create a logger with file and console handlers (optimized for Render.com)"""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler (primary for Render.com - goes to stdout/stderr)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation (only if we can write to disk)
        try:
            # Ensure log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5*1024*1024,  # 5MB (reduced for Render)
                backupCount=2,  # Reduced backup count
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # If we can't write to file, just use console logging
            print(f"Warning: Could not create file handler for {log_file}: {e}")
            print("Using console logging only (suitable for Render.com)")
            
        return logger
        
    def log_info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, default=str)}"
        self.main_logger.info(message)
        
    def log_error(self, message: str, exception: Optional[Exception] = None, 
                  extra_data: Optional[Dict[str, Any]] = None):
        """Log error message"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, default=str)}"
        if exception:
            self.error_logger.error(f"{message} | Exception: {str(exception)}", exc_info=True)
        else:
            self.error_logger.error(message)
            
    def log_warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        if extra_data:
            message = f"{message} | Data: {json.dumps(extra_data, default=str)}"
        self.main_logger.warning(message)
        
    def log_evolution(self, message: str, learning_data: Optional[Dict[str, Any]] = None):
        """Log evolution/learning activity"""
        if learning_data:
            message = f"{message} | Learning Data: {json.dumps(learning_data, default=str)}"
        self.evolution_logger.info(message)
        
    def log_search(self, query: str, source: str, results_count: int, 
                   execution_time: float, extra_data: Optional[Dict[str, Any]] = None):
        """Log search activity"""
        search_data = {
            "query": query,
            "source": source,
            "results_count": results_count,
            "execution_time_ms": round(execution_time * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        if extra_data:
            search_data.update(extra_data)
            
        self.search_logger.info(f"Search executed | {json.dumps(search_data, default=str)}")
        
    def log_api_request(self, endpoint: str, method: str, status_code: int,
                       execution_time: float, user_agent: Optional[str] = None,
                       extra_data: Optional[Dict[str, Any]] = None):
        """Log API request"""
        api_data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "execution_time_ms": round(execution_time * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        if user_agent:
            api_data["user_agent"] = user_agent
        if extra_data:
            api_data.update(extra_data)
            
        self.api_logger.info(f"API Request | {json.dumps(api_data, default=str)}")
        
    def log_performance(self, operation: str, execution_time: float, 
                       memory_usage: Optional[float] = None,
                       extra_data: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        perf_data = {
            "operation": operation,
            "execution_time_ms": round(execution_time * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        if memory_usage:
            perf_data["memory_usage_mb"] = round(memory_usage / 1024 / 1024, 2)
        if extra_data:
            perf_data.update(extra_data)
            
        self.main_logger.info(f"Performance | {json.dumps(perf_data, default=str)}")

# Global logger instance
glyphmind_logger = GlyphMindLogger()

# Convenience functions
def log_info(message: str, extra_data: Optional[Dict[str, Any]] = None):
    """Log info message"""
    glyphmind_logger.log_info(message, extra_data)

def log_error(message: str, exception: Optional[Exception] = None, 
              extra_data: Optional[Dict[str, Any]] = None):
    """Log error message"""
    glyphmind_logger.log_error(message, exception, extra_data)

def log_warning(message: str, extra_data: Optional[Dict[str, Any]] = None):
    """Log warning message"""
    glyphmind_logger.log_warning(message, extra_data)

def log_evolution(message: str, learning_data: Optional[Dict[str, Any]] = None):
    """Log evolution activity"""
    glyphmind_logger.log_evolution(message, learning_data)

def log_search(query: str, source: str, results_count: int, 
               execution_time: float, extra_data: Optional[Dict[str, Any]] = None):
    """Log search activity"""
    glyphmind_logger.log_search(query, source, results_count, execution_time, extra_data)

def log_api_request(endpoint: str, method: str, status_code: int,
                   execution_time: float, user_agent: Optional[str] = None,
                   extra_data: Optional[Dict[str, Any]] = None):
    """Log API request"""
    glyphmind_logger.log_api_request(endpoint, method, status_code, execution_time, user_agent, extra_data)

def log_performance(operation: str, execution_time: float, 
                   memory_usage: Optional[float] = None,
                   extra_data: Optional[Dict[str, Any]] = None):
    """Log performance metrics"""
    glyphmind_logger.log_performance(operation, execution_time, memory_usage, extra_data)
