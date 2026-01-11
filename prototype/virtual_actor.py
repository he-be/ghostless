"""
Virtual Actor Control Module
Handles MIDI communication with 3tene to control the avatar's expressions and motions.
"""

import time
import random
import mido

from motion_config import MOTION_DB

class VirtualActor:
    def __init__(self, midi_port_name="IAC"):
        """
        Initialize the VirtualActor.
        
        Args:
            midi_port_name (str): The partial name of the MIDI output port to use.
                                  Defaults to "IAC" to catch "IAC Driver" or localized versions.
        """
        self.midi_port_name = midi_port_name
        self.output_port = None
        self._connect_midi()

    def _connect_midi(self):
        """Attempts to open the specified MIDI output port."""
        try:
            available_ports = mido.get_output_names()
            print(f"Available MIDI ports: {available_ports}")
            
            # Simple matching logic
            target_port = next((p for p in available_ports if self.midi_port_name in p), None)
            
            if target_port:
                self.output_port = mido.open_output(target_port)
                print(f"Connected to MIDI port: {target_port}")
            else:
                print(f"Warning: MIDI port '{self.midi_port_name}' not found. MIDI commands will be skipped.")
                # We don't raise error to allow dry-run without MIDI setup
                self.output_port = None
        except Exception as e:
            print(f"Error connecting to MIDI: {e}")
            self.output_port = None

    def _send_note_on(self, note, velocity=100):
        """Sends a Note On message."""
        if self.output_port and note is not None:
            msg = mido.Message('note_on', note=note, velocity=velocity)
            self.output_port.send(msg)
            print(f"[MIDI] Sent Note On: {note}")

    def perform_motion(self, tag, intensity="normal"):
        """
        Executes a motion based on a semantic tag.
        
        Args:
            tag (str): The semantic motion tag (e.g., "agree", "greeting").
            intensity (str): The intensity level (currently unused logic, but reserved).
        """
        if tag not in MOTION_DB:
            print(f"[Actor] Unknown motion tag: {tag}")
            return

        candidates = MOTION_DB[tag]
        if not candidates:
            return

        # Randomly select a motion from the candidates
        note = random.choice(candidates)
        
        if note is not None:
            self._send_note_on(note)
        else:
            print(f"[Actor] Motion '{tag}' selected None (Neutral).")

    def perform_pre_motion(self):
        """
        Executes a 'pre-motion' (e.g., strict inhale or slight movement) before speaking.
        For now, we simulate this with a specific 'breath' motion if mapped, 
        or just a debug print.
        """
        # Example: Assume Note 100 is assigned to 'Inhale' expression/motion in 3tene
        # self._send_note_on(100) 
        print("[Actor] *Inerhales* (Pre-motion)")

    def perform_micro_movement(self):
        """
        Executes a subtle micro-movement (blink, gaze shift) during idle times.
        """
        # Logic to send minor MIDI CC or specific notes for blinks/eyes
        # print("[Actor] *Micro movement*")
        pass

    def cleanup(self):
        """Close MIDI port."""
        if self.output_port:
            self.output_port.close()
