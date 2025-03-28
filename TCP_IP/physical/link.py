"""
Link implementation for the TCP/IP Network Simulator.
"""

import time
import random
import threading
from TCP_IP.utils.logging_config import setup_logger
from TCP_IP.datalink.frame import Frame, FrameType
from TCP_IP.config import ERROR_INJECTION_RATE, BUSY_TIME_RANGE

class Link:
    """Represents a connection between network devices."""
    
    def __init__(self, name, endpoint1=None, endpoint2=None):
        self.name = name
        self.endpoint1 = endpoint1
        self.endpoint2 = endpoint2
        self.logger = setup_logger(f"Link_{name}", f"link_{name}")
        
        # CSMA/CD properties
        self.medium_busy = False
        self.busy_until = 0  # Time when medium will become free
        self.collision_detected = False
        self.transmitting_devices = set()  # Track devices currently transmitting
        self.transmission_lock = threading.Lock()  # Lock for synchronizing access to medium
        
        # Randomly make the medium busy initially (only 10% chance)
        if random.random() < 0.1:
            busy_duration = random.uniform(0.05, 0.15)
            self.medium_busy = True
            self.busy_until = time.time() + busy_duration
            self.logger.info(f"Medium initially busy for {busy_duration:.3f} seconds")
        
        if endpoint1:
            endpoint1.connect(self)
        if endpoint2:
            endpoint2.connect(self)
    
    def is_medium_busy(self):
        """Check if the medium is busy (carrier sense)"""
        with self.transmission_lock:
            current_time = time.time()
            # Check if the busy time has expired
            if self.medium_busy and current_time > self.busy_until:
                self.medium_busy = False
                self.logger.info(f"Medium is now free (busy time expired)")
            return self.medium_busy
    
    def start_transmission(self, device):
        """Start transmission from a device (returns True if successful, False if collision)"""
        with self.transmission_lock:
            # Check if medium is busy (carrier sense)
            if self.is_medium_busy():
                busy_for = max(0, self.busy_until - time.time())
                self.logger.info(f"{device.name} sensed medium busy, will be busy for {busy_for:.3f} more seconds")
                return False
            
            # Medium is free, start transmitting
            # Set medium busy for a short duration (just for this transmission)
            transmission_duration = random.uniform(0.02, 0.05)  # Shorter duration to avoid getting stuck
            self.medium_busy = True
            self.busy_until = time.time() + transmission_duration
            self.transmitting_devices.add(device)
            self.logger.info(f"{device.name} started transmission, medium is busy for {transmission_duration:.3f} seconds")
            
            # Check for collision (if another device is already transmitting)
            if len(self.transmitting_devices) > 1:
                self.collision_detected = True
                self.logger.warning(f"Collision detected! {len(self.transmitting_devices)} devices transmitting")
                return False
            
            return True
    
    def end_transmission(self, device):
        """End transmission from a device"""
        with self.transmission_lock:
            if device in self.transmitting_devices:
                self.transmitting_devices.remove(device)
                self.logger.info(f"{device.name} ended transmission")
            
            # Reset collision flag if no devices are transmitting
            if len(self.transmitting_devices) == 0:
                self.collision_detected = False
                
                # Set a very short cooldown period
                cooldown = 0.005  # Very short cooldown to avoid getting stuck
                self.busy_until = time.time() + cooldown
                self.logger.info(f"Medium will be free in {cooldown:.3f} seconds")
    
    def connect_endpoint(self, endpoint, position=None):
        """Connect an endpoint (device or hub) to this link."""
        if position == 1 or (position is None and self.endpoint1 is None):
            self.endpoint1 = endpoint
            endpoint.connect(self)
            self.logger.info(f"Connected {endpoint.name} as endpoint1")
        elif position == 2 or (position is None and self.endpoint2 is None):
            self.endpoint2 = endpoint
            endpoint.connect(self)
            self.logger.info(f"Connected {endpoint.name} as endpoint2")
        else:
            raise ValueError("Link already has two endpoints connected")
    
    def disconnect_endpoint(self, endpoint):
        """Disconnect an endpoint from this link."""
        if self.endpoint1 == endpoint:
            self.endpoint1.disconnect(self)
            self.endpoint1 = None
            self.logger.info(f"Disconnected {endpoint.name} from endpoint1")
        elif self.endpoint2 == endpoint:
            self.endpoint2.disconnect(self)
            self.endpoint2 = None
            self.logger.info(f"Disconnected {endpoint.name} from endpoint2")
    
    def transmit(self, frame, source):
        """Transmit a frame from source to the other endpoint with CSMA/CD."""
        if source not in [self.endpoint1, self.endpoint2]:
            self.logger.error(f"Error: Source {source.name} not connected to this link")
            return False
        
        # Determine the destination
        destination = self.endpoint2 if source == self.endpoint1 else self.endpoint1
        
        if destination is None:
            self.logger.error(f"Error: No destination connected")
            return False
        
        # Create a copy of the frame to avoid modifying the original
        transmitted_frame = Frame(
            frame.source_mac,
            frame.destination_mac,
            frame.data,
            frame.sequence_number,
            frame.frame_type
        )
        
        # Simplified CSMA/CD implementation to avoid getting stuck
        attempts = 0
        max_attempts = 5  # Reduced to avoid long waits
        
        while attempts < max_attempts:
            # Randomly make the medium busy to demonstrate CSMA/CD (only 20% chance)
            if random.random() < 0.2:
                self.logger.info(f"Medium is busy when {source.name} tries to send frame {frame.sequence_number}")
                # Wait a short time and try again
                time.sleep(0.05)
                attempts += 1
                continue
            
            # Medium is free, proceed with transmission
            self.logger.info(f"{source.name} transmitting frame {frame.sequence_number} to {destination.name}")
            
            # Simulate transmission delay
            time.sleep(0.02)
            
            # Small chance of collision (10%)
            if random.random() < 0.1:
                self.logger.warning(f"Collision detected during {source.name}'s transmission of frame {frame.sequence_number}")
                # Apply backoff
                backoff_time = random.uniform(0.01, 0.05) * (attempts + 1)
                self.logger.info(f"{source.name} backing off for {backoff_time:.3f}s after collision")
                time.sleep(backoff_time)
                attempts += 1
                continue
            
            # Small chance of corruption (based on ERROR_INJECTION_RATE)
            if random.random() < ERROR_INJECTION_RATE and frame.frame_type == FrameType.DATA:
                self.logger.warning(f"Error introduced in frame {frame.sequence_number}")
                # Introduce error
                transmitted_frame.introduce_error()
            
            # Successful transmission
            self.logger.info(f"Frame {frame.sequence_number} successfully transmitted from {source.name} to {destination.name}")
            
            # Deliver the frame to the destination
            destination.receive_message(transmitted_frame, source)
            return True
        
        # Max attempts reached
        self.logger.error(f"{source.name} exceeded maximum transmission attempts ({max_attempts}) for frame {frame.sequence_number}")
        return False
    
    def detect_collision(self, device):
        """Check if a collision has occurred during transmission"""
        with self.transmission_lock:
            # A collision occurs if more than one device is transmitting
            collision = len(self.transmitting_devices) > 1
            if collision and not self.collision_detected:
                self.collision_detected = True
                self.logger.warning(f"Collision detected during {device.name}'s transmission!")
            return collision
    
    def __str__(self):
        endpoint1_name = self.endpoint1.name if self.endpoint1 else "None"
        endpoint2_name = self.endpoint2.name if self.endpoint2 else "None"
        return f"Link({self.name}, {endpoint1_name} <-> {endpoint2_name})"
