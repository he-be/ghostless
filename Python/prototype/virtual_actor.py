"""
Virtual Actor Control Module
Handles OSC communication with Unity to control the avatar's expressions and motions.
"""

import time
import random
from pythonosc import udp_client

from motion_config import MOTION_DB

class VirtualActor:
    def __init__(self, osc_ip="127.0.0.1", osc_port=9000):
        """
        Initialize the VirtualActor with OSC connection.
        
        Args:
            osc_ip (str): IP address of the Unity OSC receiver.
            osc_port (int): Port of the Unity OSC receiver.
        """
        self.client = udp_client.SimpleUDPClient(osc_ip, osc_port)
        print(f"[VirtualActor] OSC Client initialized at {osc_ip}:{osc_port}")

    def _send_osc(self, address, value):
        """Sends an OSC message."""
        try:
            self.client.send_message(address, value)
            print(f"[OSC] Sent {address}: {value}")
        except Exception as e:
            print(f"[OSC] Error sending message: {e}")

    def perform_motion(self, tag, intensity="normal"):
        """
        Executes a motion based on a semantic tag.
        
        Args:
            tag (str): The semantic motion tag (e.g., "agree", "greeting").
        """
        if tag not in MOTION_DB:
            print(f"[Actor] Unknown motion tag: {tag}")
            return

        candidates = MOTION_DB[tag]
        if not candidates:
            return

        # Randomly select a motion from the candidates
        action = random.choice(candidates)
        
        address = action.get("address")
        value = action.get("value")
        
        if address:
            self._send_osc(address, value)
            
            # If there's a duration or reset logic needed, it could go here.
            # For now, we assume stateful triggers or Unity handles the transition.

    def perform_pre_motion(self):
        """
        Executes a 'pre-motion' (e.g., inhale) before speaking.
        """
        # Look for a specific pre-talk config or default to something
        if "pre_talk" in MOTION_DB:
            self.perform_motion("pre_talk")
        else:
            print("[Actor] *Inhales* (Pre-motion - No OSC mapping)")

    def set_speaking(self, is_speaking):
        """
        Sets the speaking state of the avatar.
        
        Args:
            is_speaking (bool): True if speaking, False otherwise.
        """
        val = 1.0 if is_speaking else 0.0
        self._send_osc("/ghostless/control/speech", val)

    def perform_micro_movement(self):
        """
        Executes a subtle micro-movement (blink, gaze shift) during idle times.
        """
        # In the new architecture, Unity handles micro-movements autonomously.
        # This method can be used for higher-level 'Look At' shifts if needed.
        pass

    def cleanup(self):
        """Cleanup resources."""
        pass
