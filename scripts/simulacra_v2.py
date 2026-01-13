"""
Simulacra V2: Full Body & Face Controller
Generates "Life-like" noise for Body (Sway/Breath) and Face (Blink/Brows/Mouth).
"""

import time
import math
import random
from pythonosc import udp_client

# Config
OSC_IP = "127.0.0.1"
OSC_PORT = 9000
FPS = 60

# Blink State Machine
BLINK_STATE_OPEN = 0
BLINK_STATE_CLOSING = 1
BLINK_STATE_CLOSED = 2
BLINK_STATE_OPENING = 3

class BlinkController:
    def __init__(self):
        self.state = BLINK_STATE_OPEN
        self.value = 0.0
        self.timer = 0.0
        self.next_blink_time = time.time() + random.uniform(1.0, 4.0)
        self.duration_close = 0.1
        self.duration_closed = 0.05
        self.duration_open = 0.15

    def update(self, dt):
        now = time.time()
        
        if self.state == BLINK_STATE_OPEN:
            self.value = 0.0
            if now >= self.next_blink_time:
                self.state = BLINK_STATE_CLOSING
                self.timer = 0.0
                
        elif self.state == BLINK_STATE_CLOSING:
            self.timer += dt
            t = min(1.0, self.timer / self.duration_close)
            self.value = t
            if t >= 1.0:
                self.state = BLINK_STATE_CLOSED
                self.timer = 0.0
                
        elif self.state == BLINK_STATE_CLOSED:
            self.timer += dt
            self.value = 1.0
            if self.timer >= self.duration_closed:
                self.state = BLINK_STATE_OPENING
                self.timer = 0.0
                
        elif self.state == BLINK_STATE_OPENING:
            self.timer += dt
            t = min(1.0, self.timer / self.duration_open)
            self.value = 1.0 - t
            if t >= 1.0:
                self.state = BLINK_STATE_OPEN
                # Schedule next blink
                self.next_blink_time = now + random.uniform(2.0, 6.0)
                # Chance for double blink
                if random.random() < 0.2:
                    self.next_blink_time = now + 0.1
        
        return self.value

class NoiseGen:
    def __init__(self, speed=1.0, min_v=0.0, max_v=1.0):
        self.val = random.uniform(min_v, max_v)
        self.target = random.uniform(min_v, max_v)
        self.speed = speed
        self.min_v = min_v
        self.max_v = max_v
        self.hold_timer = 0.0
    
    def update(self, dt):
        if self.hold_timer > 0:
            self.hold_timer -= dt
            return self.val
            
        # Move towards target
        diff = self.target - self.val
        step = self.speed * dt
        
        if abs(diff) < step:
            self.val = self.target
            # Pick new target
            self.target = random.uniform(self.min_v, self.max_v)
            self.hold_timer = random.uniform(0.5, 2.0) # Hold expression for a bit
        else:
            self.val += math.copysign(step, diff)
            
        return self.val

def main():
    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    print(f"--- Simulacra V2 (Face+Body) ({OSC_IP}:{OSC_PORT}) ---")
    
    start_time = time.time()
    
    # Controllers
    blink_ctrl = BlinkController()
    brows_ctrl = NoiseGen(speed=0.2, min_v=0.0, max_v=0.4) # Subtle brows
    mouth_ctrl = NoiseGen(speed=0.1, min_v=0.0, max_v=0.3) # Subtle smile
    head_sway = NoiseGen(speed=0.3, min_v=-0.5, max_v=0.5)
    
    last_loop = time.time()
    
    try:
        while True:
            now = time.time()
            dt = now - last_loop
            last_loop = now
            elapsed = now - start_time
            
            # 1. Body Logic (Sine Waves)
            breath = (math.sin(elapsed * 1.5) + 1.0) / 2.0
            body_sway = math.sin(elapsed * 0.5)
            
            # 2. Face Logic
            blink_val = blink_ctrl.update(dt)
            brows_val = brows_ctrl.update(dt)
            
            # Exaggerate for debugging
            # brows_val = brows_val * 2.0 
            
            mouth_val = mouth_ctrl.update(dt)
            head_yaw_val = head_sway.update(dt)
            
            # print(f"Blink: {blink_val:.2f} | Brows: {brows_val:.2f} | Mouth: {mouth_val:.2f} | Sway: {body_sway:.2f}", end="\r")

            # 3. Send Bundle

            # Body
            client.send_message("/avatar/parameters/HeadYaw", head_yaw_val)
            client.send_message("/avatar/parameters/HeadPitch", math.cos(elapsed*0.3)*0.1)
            client.send_message("/avatar/parameters/BodySway", body_sway)
            client.send_message("/avatar/parameters/Breath", breath)
            
            # Face
            client.send_message("/avatar/parameters/EyeBlink", blink_val)
            client.send_message("/avatar/parameters/BrowsUp", brows_val)
            client.send_message("/avatar/parameters/MouthSmile", mouth_val)
            
            time.sleep(1.0 / FPS)
            
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    main()
