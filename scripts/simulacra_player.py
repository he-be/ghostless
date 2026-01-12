import socket
import json
import time
import math
import sys
import numpy as np
import argparse
import re

# 3tene TCP Protocol
BIND_IP = "127.0.0.1"
BIND_PORT = 3910

# Helper: Quaternion and Rotation logic
def euler_to_quaternion(x, y, z, order='zxy'):
    """
    Convert Euler Angles (in degrees) to Quaternion (x, y, z, w)
    """
    inputs = {'x': np.radians(x), 'y': np.radians(y), 'z': np.radians(z)}
    
    # Calculate all sin/cos
    cx = np.cos(inputs['x'] * 0.5)
    sx = np.sin(inputs['x'] * 0.5)
    cy = np.cos(inputs['y'] * 0.5)
    sy = np.sin(inputs['y'] * 0.5)
    cz = np.cos(inputs['z'] * 0.5)
    sz = np.sin(inputs['z'] * 0.5)
    
    qs = {}
    qs['x'] = (sx, 0, 0, cx)
    qs['y'] = (0, sy, 0, cy)
    qs['z'] = (0, 0, sz, cz)
    
    # Composition based on order (e.g. "zxy" -> Z * X * Y)
    # q_combined = q1 * q2 * q3
    # Function to multiply quats
    def mul(q1, q2):
        x1, y1, z1, w1 = q1
        x2, y2, z2, w2 = q2
        return (
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2,
            w1*w2 - x1*x2 - y1*y2 - z1*z2
        )
    
    # Parse order string, e.g. "zxy"
    parts = list(order.lower()) # ['z', 'x', 'y']
    
    q_accum = qs[parts[0]]
    q_accum = mul(q_accum, qs[parts[1]])
    q_accum = mul(q_accum, qs[parts[2]])
    
    return q_accum[0], q_accum[1], q_accum[2], q_accum[3]

# Unity HumanBodyBones Mapping
# https://docs.unity3d.com/ScriptReference/HumanBodyBones.html
BONE_MAP = {
    # Core
    "Hips": 0, "hip": 0,
    "Spine": 7, "Spine1": 7, "abdomen": 7,
    "Chest": 8, "Spine2": 8, "chest": 8,
    "UpperChest": 54, "Spine3": 54,
    "Neck": 9, "neck": 9,
    "Head": 10, "head": 10, 
    
    # Legs (Unity names vs BVH)
    "LeftUpLeg": 1, "LeftThigh": 1, "lThigh": 1, 
    "RightUpLeg": 2, "RightThigh": 2, "rThigh": 2,
    "LeftLeg": 3, "LeftShin": 3, "lShin": 3,
    "RightLeg": 4, "RightShin": 4, "rShin": 4,
    "LeftFoot": 5, "lFoot": 5,
    "RightFoot": 6, "rFoot": 6,
    "LeftToe": 19, "LeftToes": 19,
    "RightToe": 20, "RightToes": 20,
    
    # Arms
    "LeftShoulder": 11, "LeftCollar": 11, "lCollar": 11,
    "RightShoulder": 12, "RightCollar": 12, "rCollar": 12,
    "LeftArm": 13, "LeftUpArm": 13, "LeftUpperArm": 13, "lShldr": 13,
    "RightArm": 14, "RightUpArm": 14, "RightUpperArm": 14, "rShldr": 14,
    "LeftForeArm": 15, "LeftLowerArm": 15, "lForeArm": 15,
    "RightForeArm": 16, "RightLowerArm": 16, "rForeArm": 16,
    "LeftHand": 17, "lHand": 17,
    "RightHand": 18, "rHand": 18,
    
    # Fingers
    "LeftHandThumb1": 24, "LeftThumbProximal": 24, "lThumb1": 24,
    "LeftHandIndex1": 27, "LeftIndexProximal": 27, "lIndex1": 27,
    "LeftHandMiddle1": 30, "LeftMiddleProximal": 30, "lMid1": 30,
    "LeftHandRing1": 33, "LeftRingProximal": 33, "lRing1": 33,
    "LeftHandPinky1": 36, "LeftLittleProximal": 36, "lPinky1": 36,
    
    "RightHandThumb1": 39, "RightThumbProximal": 39, "rThumb1": 39,
    "RightHandIndex1": 42, "RightIndexProximal": 42, "rIndex1": 42,
    "RightHandMiddle1": 45, "RightMiddleProximal": 45, "rMid1": 45,
    "RightHandRing1": 48, "RightRingProximal": 48, "rRing1": 48,
    "RightHandPinky1": 51, "RightLittleProximal": 51, "rPinky1": 51,
    
    # Eyes
    "LeftEye": 21, "leftEye": 21,
    "RightEye": 22, "rightEye": 22,
    "Jaw": 23,
}

class BVHParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bones = [] # List of {name, channels, order}
        self.hierarchy = {} 
        self.frame_time = 0.033
        self.frames = [] 
        self.scale_factor = 1.0
        
    def parse(self):
        with open(self.filepath, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
            
        iterator = iter(lines)
        current_bone = None
        parent_stack = []
        
        for line in iterator:
            if line.startswith("HIERARCHY"):
                continue
            elif line.startswith("ROOT") or line.startswith("JOINT"):
                parts = line.split()
                name = parts[1]
                self.hierarchy[name] = {"parent": parent_stack[-1] if parent_stack else None, "channels": []}
                current_bone = name
                parent_stack.append(name)
            elif line.startswith("End Site"):
                current_bone = "End Site"
                parent_stack.append(current_bone)
            elif line.startswith("{"):
                continue
            elif line.startswith("}"):
                parent_stack.pop()
                if parent_stack:
                    current_bone = parent_stack[-1]
            elif line.startswith("OFFSET"):
                pass
            elif line.startswith("CHANNELS"):
                parts = line.split()
                # Ex: CHANNELS 3 Zrotation Xrotation Yrotation
                # Or: CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
                count = int(parts[1])
                channels = parts[2:]
                
                # Detect rotation order string, e.g. "zxy"
                rot_order = ""
                for c in channels:
                    if "rotation" in c:
                        rot_order += c[0].lower() # 'Zrotation' -> 'z'
                
                if current_bone and current_bone != "End Site":
                    self.hierarchy[current_bone]["channels"] = channels
                    self.bones.append({
                        "name": current_bone, 
                        "channels": channels,
                        "rot_order": rot_order
                    })
            elif line.startswith("MOTION"):
                break
                
        # Parse Motion Section
        for line in iterator:
            if line.startswith("Frames:"):
                pass
            elif line.startswith("Frame Time:"):
                try:
                    self.frame_time = float(line.split()[2])
                except:
                    pass
            else:
                try:
                    values = [float(x) for x in line.split()]
                    self.frames.append(values)
                except ValueError:
                    pass
                    
        print(f"Parsed BVH: {len(self.frames)} frames, {self.frame_time}s per frame.")
        
        # Auto-detect scale (Meters vs Cm) based on Hips position in first frame
        if len(self.frames) > 0 and len(self.bones) > 0:
            # Assuming first bone is Hips/Root with 6 channels
            root_vals = self.frames[0][0:3] # X, Y, Z pos
            magnitude = math.sqrt(sum(v*v for v in root_vals))
            if magnitude > 10.0:
                print(f"Large root position ({magnitude:.2f}), assuming CM. Scaling by 0.01.")
                self.scale_factor = 0.01
            else:
                print(f"Small root position ({magnitude:.2f}), assuming Meters. Scale 1.0.")
                self.scale_factor = 1.0
        
    def get_frame_packet_json(self, frame_idx):
        if frame_idx >= len(self.frames):
            return None
            
        frame_data = self.frames[frame_idx]
        data_ptr = 0
        
        packet_bones = []
        hips_pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        
        for bone_info in self.bones:
            name = bone_info["name"]
            channels = bone_info["channels"]
            rot_order = bone_info["rot_order"]
            
            # Extract channel values
            val_x_pos, val_y_pos, val_z_pos = 0, 0, 0
            val_x_rot, val_y_rot, val_z_rot = 0, 0, 0
            
            for ch in channels:
                val = frame_data[data_ptr]
                data_ptr += 1
                
                if ch == "Xposition": val_x_pos = val
                elif ch == "Yposition": val_y_pos = val
                elif ch == "Zposition": val_z_pos = val
                elif ch == "Xrotation": val_x_rot = val
                elif ch == "Yrotation": val_y_rot = val
                elif ch == "Zrotation": val_z_rot = val
            
            # Map to Unity ID
            unity_id = -1
            if name in BONE_MAP:
                unity_id = BONE_MAP[name]
            else:
                clean_name = name.split(":")[-1]
                if clean_name in BONE_MAP:
                    unity_id = BONE_MAP[clean_name]
            
            # Hips Position
            if unity_id == 0:
                # Apply scale and coordinate flip if necessary
                # Unity: +Y Up, +Z Forward, +X Right (Left-Handed)
                # BVH: Often +Y Up, +Z Forward, +X Right (Right-Handed?) -> usually involves X axis flip
                hips_pos = {
                    "x": val_x_pos * -self.scale_factor, # Flip X
                    "y": val_y_pos * self.scale_factor,
                    "z": val_z_pos * self.scale_factor
                }
            
            if unity_id != -1:
                # Euler to Quaternion with dynamic order
                qx, qy, qz, qw = euler_to_quaternion(val_x_rot, val_y_rot, val_z_rot, order=rot_order)
                
                # Coordinate adjustment for Unity
                # Attempt 2: Fix reversed front/back (X-axis).
                # Previous: (-x, y, -z, w) -> Inverted X.
                # New: (x, -y, -z, w) -> Kept X, Inverted Y and Z.
                packet_bones.append({
                    "type": unity_id,
                    "qt_x": qx,
                    "qt_y": -qy,
                    "qt_z": -qz,
                    "qt_w": qw
                })

        packet = {
            "Version": 2, "DeviceID": 9, "DeviceType": 2, "Slot": 0,
            "Position": hips_pos,
            "Bones": packet_bones,
            "Command": { "Number": -1 }
        }
        return json.dumps(packet)

def main():
    parser = argparse.ArgumentParser(description="Simulacra BVH Player")
    parser.add_argument("--bvh", required=True, help="Path to BVH file")
    parser.add_argument("--loop", action="store_true", help="Loop playback")
    args = parser.parse_args()
    
    bvh = BVHParser(args.bvh)
    bvh.parse()
    
    # TCP Server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((BIND_IP, BIND_PORT))
        server.listen(1)
        print(f"--- Simulacra BVH Player Listening on {BIND_IP}:{BIND_PORT} ---")
        print("Waiting for 3tene PRO to connect...")
        
        while True:
            conn, addr = server.accept()
            print(f"Connected by {addr}")
            
            try:
                # Playback loop
                while True:
                    for i in range(len(bvh.frames)):
                        loop_start = time.time()
                        
                        json_str = bvh.get_frame_packet_json(i)
                        if json_str:
                            conn.sendall((json_str + "\n").encode('utf-8'))
                        
                        # Wait for frame time
                        elapsed = time.time() - loop_start
                        wait = bvh.frame_time - elapsed
                        if wait > 0:
                            time.sleep(wait)
                    
                    if not args.loop:
                        print("Playback finished.")
                        break
                
                # If loop finishes (non-loop mode), close connection and wait for next? 
                # Or just exit? Usually player script exits.
                if not args.loop:
                    conn.close()
                    break
                    
            except (BrokenPipeError, ConnectionResetError):
                print("\nClient disconnected. Waiting for reconnection...")
                conn.close()
                # Loop back to accept()
                
    except KeyboardInterrupt:
        print("\nServer stopping...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    main()
