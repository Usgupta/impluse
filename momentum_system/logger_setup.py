import time
import functools
import logging
import sys
from pathlib import Path
from .config import LOG_DIR

def measure_latency(func):
    """
    Decorator to measure and log the execution time of a function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            # Get logger for the module where the function is defined
            # If unable to get specific logger, fall back to root or named logger
            logger = logging.getLogger(func.__module__)
            logger.info(f"Performance: {func.__qualname__} took {duration_ms:.2f} ms")
    return wrapper

def setup_logger(name: str = "momentum_system", log_file: str = "system.log", level=logging.INFO):
    """
    Configures a professional logger with console (INFO) and file (DEBUG) handlers.
    
    Args:
        name (str): Logger name.
        log_file (str): Filename for the log in LOG_DIR.
        level (int): Base logging level.
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG) # Capture all at source

    # Prevent duplicate handlers if function is called multiple times
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler (DEBUG and above)
    file_path = LOG_DIR / log_file
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console Handler (INFO and above - Clean output for user)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
