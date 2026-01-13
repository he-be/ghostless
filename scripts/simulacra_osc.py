"""
Simulacra OSC Controller
Generates procedural "life-like" motion (breathing, sway) and sends it to Unity via OSC.
"""

import time
import math
import random
from pythonosc import udp_client

# Configuration
OSC_IP = "127.0.0.1"
OSC_PORT = 9000
FPS = 30

def get_procedural_values(t):
    """
    Generates procedural values based on time `t`.
    """
    # Breathing: Slow sine wave (0.0 to 1.0)
    breath_cycle = (math.sin(t * 1.5) + 1.0) / 2.0
    
    # Body Sway: Very slow sine wave (-1.0 to 1.0)
    body_sway = math.sin(t * 0.5)
    
    # Head Idling: Perlin-like noise or composite sine waves
    # Combining two frequencies for more natural randomness
    head_yaw = math.sin(t * 0.7) * 0.3 + math.sin(t * 0.2) * 0.7
    head_pitch = math.cos(t * 1.1) * 0.5
    
    return {
        "Breath": breath_cycle,     # 0.0 ~ 1.0
        "BodySway": body_sway,      # -1.0 ~ 1.0
        "HeadYaw": head_yaw,        # -1.0 ~ 1.0 (will be scaled in Unity)
        "HeadPitch": head_pitch     # -1.0 ~ 1.0
    }

def main():
    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    print(f"--- Simulacra OSC Started ({OSC_IP}:{OSC_PORT}) ---")
    print("Press Ctrl+C to stop.")
    
    start_time = time.time()
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Calculate values
            values = get_procedural_values(elapsed)
            
            # Send OSC
            # Using bundles would be more efficient, but individual messages are fine for localhost
            for key, val in values.items():
                address = f"/avatar/parameters/{key}"
                client.send_message(address, val)
            
            # Control Logic for Random Gaze (Optional Micro-movements)
            # if random.random() < 0.01: ...
            
            # Wait for next frame
            time.sleep(1.0 / FPS)
            
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    main()
