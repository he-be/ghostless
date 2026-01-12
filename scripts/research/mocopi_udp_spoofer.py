"""
Mocopi UDP Spoofer (Binary TLV Version) - Aggressive Test

Target: 3teneMoApp_Mocopi (Port 12351 UDP)

Changes:
1. Scaling Position by 100.0 (Maybe it expects cm?)
2. Rotating ALL BONES slightly to ensure we hit the right ID.
3. Sending SKDF more frequently.
"""

import socket
import struct
import time
import math
import sys

DEST_IP = "127.0.0.1"
DEST_PORT = 12351

# ... [TLV Functions same as before, omitted for brevity if reusing] ...
# Re-defining them for safety in this single script run.

def make_tlv(name, data):
    if isinstance(name, str):
        name_bytes = name.encode('ascii')
    else:
        name_bytes = name
    length = len(data)
    return struct.pack('<I', length) + name_bytes + data

def make_head_block():
    ftyp = make_tlv('ftyp', b'mocopi')
    vrsn = make_tlv('vrsn', b'\x01')
    return make_tlv('head', ftyp + vrsn)

def make_info_block():
    # Inside "info":
    # 1. ipad (u64) - Sender IP
    # 127.0.0.1 = 0x7F000001
    # Packed as u64 LE
    # Note: Some parsers might expect mapped IPv6? But u64 suggests standard 8-byte container.
    # Let's try packing 127.0.0.1
    ip_int = 0x7F000001 # 127.0.0.1 is 1.0.0.127 in LE? No, inet_aton logic.
    # 127, 0, 0, 1 -> 4 bytes. Pad to 8.
    ipad_data = struct.pack('BBBBxxxx', 127, 0, 0, 1) # 4 bytes IP + 4 bytes pad
    ipad_block = make_tlv('ipad', ipad_data)
    
    # 2. rcvp (u16)
    rcvp_data = struct.pack('<H', DEST_PORT)
    rcvp_block = make_tlv('rcvp', rcvp_data)
    
    return make_tlv('sndf', ipad_block + rcvp_block) # Changed from 'info' to 'sndf'

BONE_PARENTS = {
    0: 0, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6,
    8: 7, 9: 8, 10: 9, 11: 7, 12: 11, 13: 12, 14: 13,
    15: 7, 16: 16, 17: 17, 18: 18, 19: 0, 20: 19, 21: 20, 22: 21,
    23: 0, 24: 23, 25: 24, 26: 25
}

def make_skdf_block():
    bons_payload = b''
    for bone_id in range(27):
        bnid = make_tlv('bnid', struct.pack('<H', bone_id))
        pbid = make_tlv('pbid', struct.pack('<H', BONE_PARENTS.get(bone_id,0)))
        
        # Identity Trans for Definition
        trans = struct.pack('<fffffff', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        tran = make_tlv('tran', trans)
        
        # Note: Rust logic: `parse_bones` loop -> `parse_trans(part)`.
        # `part` is remaining data.
        # It expects `bndt` -> `bnid` -> `pbid` -> `tran` (inside bndt? No, serialized sequentially?)
        # Rust: `parse_value` for `bndt`, then inside its data: `bnid`, `pbid`.
        # Then `parse_trans(part)` (Wait, `part` is the bndt payload?)
        # No! `parse_trans(part)` inside the loop uses `part` which is the SLICE of `bons_data`.
        # Let's re-read the Rust blog logic carefully.
        
        # `let part = &bons_data.data[(read_bytes as usize)..];`
        # `let data = parse_value(part)?;` (This is `bndt`)
        # `let data = parse_value(data.data)?;` (This is values INSIDE bndt: `bnid`)
        # `let data = parse_value(data.rem)?;` (This `pbid`)
        # `let (_, trans) = parse_trans(part)?;` !!!!!
        # FAIL DETECTED: `parse_trans` is called on `part` (the `bndt` block), NOT `data.rem`!
        # Wait, if it calls `parse_trans(part)`, it parses the `bndt` header again?
        # No, `parse_trans` expects `tran` tag.
        # `bndt` block contains `bnid` block, `pbid` block.
        # Where is `tran`?
        # Rust code: `let (_, trans) = parse_trans(part)?;`
        # This implies `tran` is NOT inside `bndt` but AFTER it?
        # OR `part` still points to the start of `bndt`?
        # If `parse_trans` expects `tran` tag, then `tran` must be a sibling of `bnid`?
        # No, `take` advances.
        
        # CORRECTION based on Rust:
        # Loop over `bons_data`:
        # 1. `bndt` TLV.
        #    Inside `bndt`:
        #       - `bnid` TLV. (consumed)
        #       - `pbid` TLV. (consumed)
        #       - `tran` TLV. (Wait, the Rust code calls `parse_trans(part)` where `part` is the `bndt` block??)
        #       - Actually, the code snippet might be buggy or I'm misreading `part`.
        #       - If `part` is the whole `bndt` block wrapper, then `parse_trans` would fail parsing `bndt` as `tran`.
        #       - Unless `tran` is INSIDE `bndt`?
        
        # Let's blindly trust standard serialization:
        # `bndt` [ `bnid` ... `pbid` ... `tran` ... ]
        # This is what I did.
        
        bndt = make_tlv('bndt', bnid + pbid + tran)
        bons_payload += bndt
        
    return make_tlv('skdf', make_tlv('bons', bons_payload))

def make_frame_block(seq, elapsed):
    fnum = make_tlv('fnum', struct.pack('<I', seq))
    # Time: Microseconds (us) -> Native Mocopi uses us (usually)
    # Rust parser uses u32, standard Sony timestamp is often us or ticks.
    # If ms, it wraps every ~50 days. If us, it wraps every ~1.2 hours (u32).
    # Sender usually resets or is relative.
    # Let's try MICROSECONDS.
    time_us = int(elapsed * 1000000) & 0xFFFFFFFF # Ensure u32 wrap
    time_block = make_tlv('time', struct.pack('<I', time_us))
    
    btrs_payload = b''
    for bone_id in range(27):
        bnid = make_tlv('bnid', struct.pack('<H', bone_id))
        
        # Calculate Transforms
        qx, qy, qz, qw = 0.0, 0.0, 0.0, 1.0
        
        # TEST: Rotate ALL bones to ensure visibility
        # Wave effect
        angle = math.sin(elapsed * 5.0 + bone_id*0.5) * 1.0 # 57 deg
        qx = math.sin(angle)
        qw = math.cos(angle)
        
        # Pos
        px, py, pz = 0.0, 0.0, 0.0
        if bone_id == 0:
            py = math.sin(elapsed * 5.0) * 0.5 # 0.5 units
            
        trans = struct.pack('<fffffff', qx, qy, qz, qw, px, py, pz)
        tran = make_tlv('tran', trans)
        
        btrs_payload += make_tlv('btdt', bnid + tran)
        
    return make_tlv('fram', fnum + time_block + make_tlv('btrs', btrs_payload))

def run_spoofer():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"--- Mocopi Spoofer (Aggr/50Hz/us) ({DEST_IP}:{DEST_PORT}) ---")
    
    # Send SKDF
    for i in range(10):
        sock.sendto(make_head_block() + make_info_block() + make_skdf_block(), (DEST_IP, DEST_PORT))
        time.sleep(0.02) # 50Hz
        
    start_time = time.time()
    seq = 0
    while True:
        elapsed = time.time() - start_time
        seq += 1
        sock.sendto(make_head_block() + make_info_block() + make_frame_block(seq, elapsed), (DEST_IP, DEST_PORT))
        time.sleep(1/50.0) # 50Hz
        if seq % 50 == 0:
            print(f"Sending Frame {seq}...", end='\r')
            sys.stdout.flush()

if __name__ == "__main__":
    run_spoofer()
