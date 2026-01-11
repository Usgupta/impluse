
import logging
import sys
from pathlib import Path
from .config import LOG_DIR

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
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
