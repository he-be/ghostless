import time
import sys
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder

IP = "127.0.0.1"
PORT = 9000

def main():
    client = udp_client.SimpleUDPClient(IP, PORT)
    print(f"--- Manual OSC Tester ({IP}:{PORT}) ---")
    print("Keys:")
    print("  0: Neutral")
    print("  1: Happy (Joy)")
    print("  2: Angry")
    print("  3: Sad (Sorrow)")
    print("  4: Relaxed (Fun)")
    print("  q: Quit")
    
    while True:
        try:
            key = input("Enter Command (0-4): ").strip()
            
            if key == 'q':
                break
                
            if key in ['0', '1', '2', '3', '4']:
                val = int(key)
                print(f"Sending /avatar/parameters/Expression : {val}")
                client.send_message("/avatar/parameters/Expression", val)
            else:
                print("Invalid key.")
                
        except KeyboardInterrupt:
            break
            
    print("Exiting.")

if __name__ == "__main__":
    main()
