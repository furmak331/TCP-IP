"""
Main entry point for the TCP/IP Network Simulator.
"""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from TCP_IP.ui.cli import interactive_cli

def main():
    """Start the TCP/IP Network Simulator."""
    interactive_cli()

if __name__ == "__main__":
    main()
