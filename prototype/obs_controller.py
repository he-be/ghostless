"""
OBS Controller Module
Handles communication with OBS Studio via obs-websocket-py.
"""

import time
import obsws_python as obs

class ObsController:
    def __init__(self, host='localhost', port=4455, password=''):
        """
        Initialize the OBS Controller.
        
        Args:
            host (str): OBS WebSocket host.
            port (int): OBS WebSocket port (default 4455).
            password (str): OBS WebSocket text password (if set).
        """
        self.host = host
        self.port = port
        self.password = password
        self.client = None
        self._connect()

    def _connect(self):
        """Connects to OBS WebSocket."""
        try:
            self.client = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            print(f"[OBS] Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"[OBS] Connection failed: {e}")
            self.client = None

    def start_recording(self):
        """Starts recording."""
        if self.client:
            try:
                self.client.start_record()
                print("[OBS] Recording Started.")
            except Exception as e:
                print(f"[OBS] Failed to start recording: {e}")
        else:
            print("[OBS] Client not connected. Skipping Start Recording.")

    def stop_recording(self):
        """Stops recording and returns the path if available."""
        if self.client:
            try:
                resp = self.client.stop_record()
                print(f"[OBS] Recording Stopped. Output: {resp.output_path}")
                return resp.output_path
            except Exception as e:
                print(f"[OBS] Failed to stop recording: {e}")
        else:
            print("[OBS] Client not connected. Skipping Stop Recording.")

    def disconnect(self):
        """Disconnects the client (if applicable)."""
        # obs-websocket-py handles cleanup usually, but we can explicit close if needed
        pass
