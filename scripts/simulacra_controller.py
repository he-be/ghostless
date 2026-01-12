"""
TCP Spoofer for 3tene PRO (Port 3910) - Bone Scanner
Scans bones 0-23 to help identify the Head Bone ID.
"""

import socket
import json
import time
import math
import sys

BIND_IP = "127.0.0.1"
BIND_PORT = 3910

def get_rotation(axis, angle):
    rad = math.radians(angle)
    s = math.sin(rad/2)
    c = math.cos(rad/2)
    if axis == 'x': return s, 0, 0, c
    if axis == 'y': return 0, s, 0, c
    if axis == 'z': return 0, 0, s, c
    return 0, 0, 0, 1

def make_json_packet(seq, elapsed):
    # BONE SCANNER MODE
    # Cycle through bones 0-23 every 2 seconds
    current_bone_id = int(elapsed / 2.0) % 24
    
    bones = []
    
    # Wiggle the current test bone efficiently
    angle = math.sin(elapsed * 10.0) * 45.0 # Fast large wiggle
    qx, qy, qz, qw = get_rotation('z', angle) # Default Z rotation
    
    # Heuristic: Spine/Head often rotate around X or Y
    if current_bone_id in [0, 1, 2, 3, 4, 5, 6]: 
        qx, qy, qz, qw = get_rotation('x', angle)
        
    for i in range(24):
        bx, by, bz, bw = 0, 0, 0, 1
        if i == current_bone_id:
            bx, by, bz, bw = qx, qy, qz, qw
            
        bones.append({
            "type": i,
            "qt_x": bx, "qt_y": by, "qt_z": bz, "qt_w": bw
        })

    packet = {
        "Version": 2, "DeviceID": 9, "DeviceType": 2, "Slot": 0,
        "Position": { "x": 0.0, "y": 0.0, "z": 0.0 },
        "Bones": bones,
        "Command": { "Number": -1 }
    }
    return json.dumps(packet), current_bone_id

def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((BIND_IP, BIND_PORT))
        server.listen(1)
        print(f"--- 3tene TCP Bone Scanner Listening on {BIND_IP}:{BIND_PORT} ---")
        print("Scans Bones 0-23. Watch the avatar and note which ID moves the HEAD.")
        
        while True:
            print("Waiting for 3tene PRO to connect...")
            conn, addr = server.accept()
            print(f"Connected by {addr}")
            
            start_time = time.time()
            seq = 0
            current_id = -1
            
            try:
                while True:
                    elapsed = time.time() - start_time
                    json_str, active_bone = make_json_packet(seq, elapsed)
                    
                    conn.sendall((json_str + "\n").encode('utf-8'))
                    
                    if active_bone != current_id:
                        current_id = active_bone
                        print(f"Testing Bone ID: {current_id}   ", end='\r')
                        sys.stdout.flush()
                        
                    time.sleep(1/50.0)
                    seq += 1
                    
            except (BrokenPipeError, ConnectionResetError):
                print("\nClient disconnected. Resetting...")
            finally:
                conn.close()
                
    except KeyboardInterrupt:
        print("\nServer stopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        server.close()
    
if __name__ == "__main__":
    run_server()
