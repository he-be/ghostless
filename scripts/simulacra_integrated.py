import cv2
import numpy as np
import socket
import json
import time
import math
import sys
import select
import pyvirtualcam
from pyvirtualcam import PixelFormat

# Configuration
BIND_IP = "127.0.0.1"
BIND_PORT = 3910
WINDOW_NAME = "Simulacra Anime 2.5D Spoofer"
WIDTH, HEIGHT = 1280, 720

# --------------------------
# TCP / Body Control Logic
# --------------------------

def get_rotation(axis, angle):
    rad = math.radians(angle)
    s = math.sin(rad/2)
    c = math.cos(rad/2)
    if axis == 'x': return s, 0, 0, c
    if axis == 'y': return 0, s, 0, c
    if axis == 'z': return 0, 0, s, c
    return 0, 0, 0, 1

def mul_quat(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    )

class BodyServer:
    def __init__(self, ip, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((ip, port))
        self.server.listen(1)
        self.server.setblocking(False)
        self.conn = None
        self.addr = None
        print(f"TCP Body Server listening on {ip}:{port}")

    def update(self, elapsed_time):
        if self.conn is None:
            try:
                readable, _, _ = select.select([self.server], [], [], 0)
                if readable:
                    self.conn, self.addr = self.server.accept()
                    self.conn.setblocking(False)
                    print(f"3tene Connected: {self.addr}")
            except Exception as e:
                pass

        if self.conn:
            try:
                packet = self.generate_packet(elapsed_time)
                json_str = json.dumps(packet) + "\n"
                self.conn.sendall(json_str.encode('utf-8'))
            except BlockingIOError:
                pass
            except (BrokenPipeError, ConnectionResetError):
                print("3tene Disconnected")
                self.conn.close()
                self.conn = None
            except Exception as e:
                print(f"Send Error: {e}")
                self.conn.close()
                self.conn = None

    def generate_packet(self, t):
        # Procedural Idle Animation
        breath_val = math.sin(t * 1.0) * 3.0
        sway_val = math.sin(t * 0.5) * 1.5
        
        bones = []
        
        # Hips (0)
        q_hips = get_rotation('y', sway_val * 0.5)
        bones.append({"type": 0, "qt_x": q_hips[0], "qt_y": q_hips[1], "qt_z": q_hips[2], "qt_w": q_hips[3]})
        
        # Spine (7)
        q_spine_x = get_rotation('x', breath_val)
        q_spine_z = get_rotation('z', sway_val * 0.5)
        q_spine = mul_quat(q_spine_x, q_spine_z)
        bones.append({"type": 7, "qt_x": q_spine[0], "qt_y": q_spine[1], "qt_z": q_spine[2], "qt_w": q_spine[3]})
        
        # Head (10) - Sync with Anime Face rotation
        # The Anime face rotates roughly +/- 15 degrees
        head_yaw = math.sin(t * 0.8) * 15.0 
        head_pitch = math.cos(t * 0.3) * 2.0
        q_head_y = get_rotation('y', head_yaw)
        q_head_x = get_rotation('x', head_pitch)
        q_head = mul_quat(q_head_y, q_head_x)
        bones.append({"type": 10, "qt_x": q_head[0], "qt_y": q_head[1], "qt_z": q_head[2], "qt_w": q_head[3]})

        packet = {
            "Version": 2, "DeviceID": 9, "DeviceType": 2, "Slot": 0,
            "Position": { "x": 0.0, "y": 0.0, "z": 0.0 },
            "Bones": bones,
            "Command": { "Number": -1 }
        }
        return packet

    def close(self):
        if self.conn: self.conn.close()
        self.server.close()

# --------------------------
# Anime Face Rendering Logic
# --------------------------

class AnimeFaceRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # Load Assets
        self.imgs = {}
        try:
            self.imgs['center'] = self._load("scripts/anime_face_center.png")
            self.imgs['right'] = self._load("scripts/anime_face_right.png")
            self.imgs['left'] = cv2.flip(self.imgs['right'], 1)
            self.imgs['open'] = self._load("scripts/anime_face_open.png")
        except Exception as e:
            print(f"Error loading assets: {e}")
            sys.exit(1)

    def _load(self, path):
        img = cv2.imread(path)
        if img is None: raise FileNotFoundError(path)
        # Use INTER_AREA or INTER_LINEAR for resizing to avoid artifacts
        return cv2.resize(img, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

    def draw(self, t):
        # Determine State
        head_yaw = math.sin(t * 0.2) # -1.0 to 1.0 (approx -15 to +15 deg)
        mouth_cycle = math.sin(t * 4.0) # Fast cycle for talking
        
        # Select base image
        current_img = self.imgs['center']
        
        if head_yaw < -0.3:
            current_img = self.imgs['right'] # Assuming 'right' means looking right (screen right)
        elif head_yaw > 0.3:
            current_img = self.imgs['left'] # Assuming 'left' means looking left
        else:
            # Center - check mouth
             if mouth_cycle > 0.0:
                 current_img = self.imgs['open']
             else:
                 current_img = self.imgs['center']
        
        return current_img.copy()

def main():
    print("--- Simulacra Anime 2.5D Spoofer ---")
    print("1. Direct Virtual Camera Mode Initializing...")
    print("2. In 3tene: Set Webcam to 'OBS Virtual Camera' (or Python Virtual Device).")
    print(f"3. In 3tene: Enable Body Tracking (Port {BIND_PORT}).")
    print("Press Ctrl+C to quit.")
    
    body_server = BodyServer(BIND_IP, BIND_PORT)
    renderer = AnimeFaceRenderer(WIDTH, HEIGHT)
    
    start_time = time.time()
    
    try:
        # Initialize Virtual Camera
        # fmt=PixelFormat.BGR because OpenCV uses BGR
        # fallback=True allows pyvirtualcam to find available backends (e.g. OBS DAL)
        with pyvirtualcam.Camera(width=WIDTH, height=HEIGHT, fps=30, fmt=PixelFormat.BGR) as cam:
            print(f'Virtual camera device: {cam.device}')
            
            while True:
                t = time.time() - start_time
                
                # Update Body
                body_server.update(t)
                
                # Render Face
                frame = renderer.draw(t)
                
                # Send to Virtual Camera
                cam.send(frame)
                
                # Sleep to maintain FPS
                cam.sleep_until_next_frame()
                
    except KeyboardInterrupt:
        print("Interrupted.")
    except Exception as e:
        print(f"Error: {e}")
        print("Ensure you have a virtual camera driver installed (e.g., OBS Studio).")
    finally:
        print("Shutting down...")
        body_server.close()

if __name__ == "__main__":
    main()
