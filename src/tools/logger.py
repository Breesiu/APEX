import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from ..schema import AgentState
def setup_logger(state: AgentState, instruction_index: int = 0) -> logging.Logger:
    """
    Setup logger for each user instruction execution.
    
    Args:
        output_dir: Directory to save log files
        instruction_index: Index of the user instruction
        
    Returns:
        Configured logger instance
    """
    # Create output directory if it doesn't exist
    output_dir = state.output_dir
    iterate_version = state.iterate_version
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger name based on instruction
    logger_name = str(output_dir.absolute())
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create file handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"execution_{iterate_version}_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"Logger initialized. Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get existing logger by name"""
    return logging.getLogger(name)