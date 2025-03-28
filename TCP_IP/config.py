"""
Configuration settings for the TCP/IP Network Simulator.
"""

# Constants
MAX_FRAME_SIZE = 1024  # Maximum size of a frame in bytes
TRANSMISSION_DELAY = 0.01  # Simulated delay for transmission in seconds
BIT_ERROR_RATE = 0.01  # Probability of bit error in transmission
CSMA_CD_MAX_ATTEMPTS = 16  # Maximum attempts before giving up
CSMA_CD_SLOT_TIME = 0.02  # Time slot for backoff in seconds
MEDIUM_BUSY_PROBABILITY = 0.3  # Probability that medium is initially busy
MEDIUM_BUSY_DURATION = 0.1  # How long the medium stays busy in seconds
ERROR_INJECTION_RATE = 0.2  # 20% chance of introducing an error in a frame
BUSY_TIME_RANGE = (0.05, 0.2)  # Range of time (in seconds) that the medium stays busy 