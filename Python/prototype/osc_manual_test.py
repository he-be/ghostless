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
    print("  s: Toggle Speech (Talk/Silent)")
    print("  q: Quit")
    
    is_speaking = False

    while True:
        try:
            key = input("Enter Command: ").strip()
            
            if key == 'q':
                break
                
            if key == '0':
                client.send_message("/ghostless/state/emotion", "neutral")
                print("Sent: neutral")
            elif key == '1':
                client.send_message("/ghostless/state/emotion", "joy")
                print("Sent: joy")
            elif key == '2':
                client.send_message("/ghostless/state/emotion", "angry")
                print("Sent: angry")
            elif key == '3':
                client.send_message("/ghostless/state/emotion", "sorrow")
                print("Sent: sorrow")
            elif key == '4':
                client.send_message("/ghostless/state/emotion", "fun")
                print("Sent: fun")
            elif key == 's':
                is_speaking = not is_speaking
                val = 1.0 if is_speaking else 0.0
                client.send_message("/ghostless/control/speech", val)
                print(f"Sent: speech={val}")
            else:
                print("Invalid key.")
                
        except KeyboardInterrupt:
            break
            
    print("Exiting.")

if __name__ == "__main__":
    main()
