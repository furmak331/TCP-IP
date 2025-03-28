"""
Logging configuration for the TCP/IP Network Simulator.
"""

import logging
import os

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def setup_logger(name, log_file=None):
    """Setup a logger for a component"""
    logger = logging.getLogger(name)
    
    if log_file:
        file_handler = logging.FileHandler(f"logs/{log_file}.log")
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    return logger 