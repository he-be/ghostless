"""
TCP Spy for Port 3910 (3tene Internal Protocol)

Purpose:
Mimic '3teneMoApp' by listening on TCP 3910.
Capture connection from 3tene PRO.
Log any data received (Handshake).
Allow sending test data (JSON) to see if 3tene reacts.
"""

import socket
import sys

BIND_IP = "127.0.0.1"
BIND_PORT = 3910

def run_spy():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind((BIND_IP, BIND_PORT))
        server_sock.listen(1)
        print(f"--- TCP Spy Listening on {BIND_IP}:{BIND_PORT} ---")
        print("Please ensure '3teneMoApp' is CLOSED.")
        print("Waiting for 3tene PRO to connect...")
        
        conn, addr = server_sock.accept()
        print(f"Accepted connection from {addr}")
        
        while True:
            data = conn.recv(4096)
            if not data:
                print("Connection closed by client.")
                break
            
            print(f"RX ({len(data)} bytes): {data}")
            try:
                print(f"RX String: {data.decode('utf-8')}")
            except:
                pass
            
            # If it's a Leap Motion handshake, it might look like HTTP or specific JSON.
            # We can try responding if we recognize it.
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        server_sock.close()

if __name__ == "__main__":
    run_spy()
