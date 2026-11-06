"""Structured logging configuration for the pipeline."""
import logging
import os
import sys

def setup_logger(name: str = "pipeline", log_file: str = "pipeline.log", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Format: [2026-08-14 23:00:00] [INFO] [module] message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass
        
    return logger

log = setup_logger()
