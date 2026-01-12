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
def euler_to_quaternion(z, x, y, order='zxy'):
    """
    Convert Euler Angles (in degrees) to Quaternion (x, y, z, w)
    BVH rotations are Euler angles.
    """
    z = np.radians(z)
    x = np.radians(x)
    y = np.radians(y)
    
    cx = np.cos(x * 0.5)
    sx = np.sin(x * 0.5)
    cy = np.cos(y * 0.5)
    sy = np.sin(y * 0.5)
    cz = np.cos(z * 0.5)
    sz = np.sin(z * 0.5)
    
    # ZXY order (Common in BVH for Unity)
    if order == 'zxy':
        # q = qz * qx * qy
        # qz = (0, 0, sz, cz)
        # qx = (sx, 0, 0, cx)
        # qy = (0, sy, 0, cy)
        
        # qzx = (sz*cx, -sz*sx, sz*cx + cz*0, cz*cx) ?? No, standard mult
        
        # Manual composition
        # Qz * Qx
        # w = cz*cx - sz*0 = cz*cx
        # x = cz*sx + sz*0 = cz*sx
        # y = cz*0 - sz*sx = -sz*sx
        # z = cz*0 + sz*cx = sz*cx
        
        # (QzQx) * Qy
        # w = (cz*cx)*cy - (cz*sx)*0 - (-sz*sx)*sy - (sz*cx)*0 
        #   = cz*cx*cy + sz*sx*sy
        
        qw = cz*cx*cy - sz*sx*sy 
        qx = cz*sx*cy - sz*cx*sy
        qy = cz*cx*sy + sz*sx*cy
        qz = sz*cx*cy + cz*sx*sy
        
        return qx, qy, qz, qw
        
    elif order == 'zyx':
        # Standard ZYX
        qw = cx*cy*cz + sx*sy*sz
        qx = sx*cy*cz - cx*sy*sz
        qy = cx*sy*cz + sx*cy*sz
        qz = cx*cy*sz - sx*sy*cz
        return qx, qy, qz, qw
    
    # Default fallback identity
    return 0, 0, 0, 1

# Unity HumanBodyBones Mapping
BONE_MAP = {
    "Hips": 0,
    "LeftUpLeg": 1, "LeftThigh": 1,
    "RightUpLeg": 2, "RightThigh": 2,
    "LeftLeg": 3, "LeftShin": 3,
    "RightLeg": 4, "RightShin": 4,
    "LeftFoot": 5,
    "RightFoot": 6,
    "Spine": 7, "Spine1": 7,
    "Chest": 8, "Spine2": 8,
    "UpperChest": 9, "Spine3": 9, "Neck": 9, # Approximation if Bone mapping is tight. Some BVH have Spine1,2,3.
    # Note: Neck is usually 9 in Unity HumanBodyBones? Verify index.
    # Unity: 0-Hips, 1-LLeg, 2-RLeg, 3-LKnee, 4-RKnee, 5-LFoot, 6-RFoot, 7-Spine, 8-Chest, 9-Neck, 10-Head
    # NOTE: Re-adjusted map based on Unity Enum standard.
    "Neck": 9,
    "Head": 10,
    "LeftShoulder": 11, "LeftCollar": 11,
    "RightShoulder": 12, "RightCollar": 12,
    "LeftArm": 13, "LeftUpArm": 13, "LeftUpperArm": 13,
    "RightArm": 14, "RightUpArm": 14, "RightUpperArm": 14,
    "LeftForeArm": 15, "LeftLowerArm": 15,
    "RightForeArm": 16, "RightLowerArm": 16,
    "LeftHand": 17,
    "RightHand": 18,
    "LeftToe": 19, "LeftToes": 19,
    "RightToe": 20, "RightToes": 20,
    "LeftEye": 21,
    "RightEye": 22,
    "Jaw": 23,
    
    # Fingers (Proximal)
    "LeftHandThumb1": 24, "LeftThumbProximal": 24,
    "LeftHandIndex1": 27, "LeftIndexProximal": 27,
    "LeftHandMiddle1": 30, "LeftMiddleProximal": 30,
    "LeftHandRing1": 33, "LeftRingProximal": 33,
    "LeftHandPinky1": 36, "LeftLittleProximal": 36,
    
    "RightHandThumb1": 39, "RightThumbProximal": 39,
    "RightHandIndex1": 42, "RightIndexProximal": 42,
    "RightHandMiddle1": 45, "RightMiddleProximal": 45,
    "RightHandRing1": 48, "RightRingProximal": 48,
    "RightHandPinky1": 51, "RightLittleProximal": 51,
    
    # UpperChest (Unity 5.6+)
    "UpperChest": 54
}

class BVHParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bones = [] # List of bone names in order of channel data
        self.hierarchy = {} # name -> {offset, channels, parent}
        self.frame_time = 0.033
        self.frames = [] # List of numpy arrays
        self.offsets = []
        
    def parse(self):
        with open(self.filepath, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
            
        iterator = iter(lines)
        current_bone = None
        parent_stack = []
        
        mode = "HIERARCHY"
        
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
                # We might need offsets for retargeting, but for simple rotation copying usually we interpret rotation only.
                # Storing just in case.
                pass
            elif line.startswith("CHANNELS"):
                parts = line.split()
                count = int(parts[1])
                channels = parts[2:]
                if current_bone and current_bone != "End Site":
                    self.hierarchy[current_bone]["channels"] = channels
                    # For data parsing order
                    self.bones.append({"name": current_bone, "channels": channels})
            elif line.startswith("MOTION"):
                mode = "MOTION"
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
                # Data line
                try:
                    values = [float(x) for x in line.split()]
                    self.frames.append(values)
                except ValueError:
                    pass
                    
        print(f"Parsed BVH: {len(self.frames)} frames, {self.frame_time}s per frame.")
        
    def get_frame_packet_json(self, frame_idx):
        if frame_idx >= len(self.frames):
            return None
            
        frame_data = self.frames[frame_idx]
        data_ptr = 0
        
        packet_bones = []
        
        # Hips Position (Special handling)
        hips_pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        
        for bone_info in self.bones:
            name = bone_info["name"]
            channels = bone_info["channels"]
            
            # Extract channel values
            val_x_pos, val_y_pos, val_z_pos = 0, 0, 0
            val_z_rot, val_x_rot, val_y_rot = 0, 0, 0
            
            # Identify channel indices
            for ch in channels:
                val = frame_data[data_ptr]
                data_ptr += 1
                
                if ch == "Xposition": val_x_pos = val
                elif ch == "Yposition": val_y_pos = val
                elif ch == "Zposition": val_z_pos = val
                elif ch == "Zrotation": val_z_rot = val
                elif ch == "Xrotation": val_x_rot = val
                elif ch == "Yrotation": val_y_rot = val
            
            # Map to Unity Bone ID
            # Simple fuzzy match or exact match from map
            unity_id = -1
            if name in BONE_MAP:
                unity_id = BONE_MAP[name]
            else:
                # Try stripping prefixes like "Mixamorig:"
                clean_name = name.split(":")[-1]
                if clean_name in BONE_MAP:
                    unity_id = BONE_MAP[clean_name]
            
            # Special handling for Hips (Root) position
            if unity_id == 0:
                # Scaling factor? BVH units are often cm or inches. Unity is meters.
                # Assuming cm -> meters: * 0.01
                # But sometimes it's arbitrary.
                # User's BVH seems like raw values.
                # Let's try sending as is, or with simple scale.
                # Unity assumes meters. If BVH is 90 (cm), sends 90m -> Huge.
                # Let's start with 0.01 scale.
                hips_pos = {"x": val_x_pos * -0.01, "y": val_y_pos * 0.01, "z": val_z_pos * 0.01} 
                # Negate X for coordinate system conversion (Right-hand to Left-hand)?
            
            if unity_id != -1:
                # Convert Euler (Deg) to Quaternion
                # Order is derived from channel order. "Zrotation Xrotation Yrotation" -> ZXY
                # For simplicity, assuming ZXY for now as per common BVH.
                qx, qy, qz, qw = euler_to_quaternion(val_z_rot, val_x_rot, val_y_rot, order='zxy')
                
                # Coordinate System Adjustment
                # Unity (Left-Handed Y-Up) vs BVH (Right-Handed Y-Up often)
                # Flip X and W usually corrects rotation? Or X and Y?
                # A robust retargeting is complex. 
                # Quick hack: Negate X and Z components of Euler or try different quaternion perm.
                # Let's try standard conversion first.
                
                packet_bones.append({
                    "type": unity_id,
                    "qt_x": -qx, # Try flipping X forhandedness
                    "qt_y": qy,
                    "qt_z": -qz, # Try flipping Z
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
