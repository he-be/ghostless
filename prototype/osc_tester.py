import time
from pythonosc import udp_client

IP = "127.0.0.1"
PORT = 9000

def test_osc():
    client = udp_client.SimpleUDPClient(IP, PORT)
    
    print(f"Sending OSC tests to {IP}:{PORT}")
    
    actions = [
        ("/avatar/parameters/Expression", 1), # Joy
        ("/avatar/parameters/Expression", 0), # Neutral
        ("/avatar/parameters/Gesture", 1),    # Wave
        ("/avatar/parameters/Gesture", 0),    # Reset
    ]
    
    for addr, val in actions:
        print(f"Sending {addr} : {val}")
        client.send_message(addr, val)
        time.sleep(1)

if __name__ == "__main__":
    test_osc()
