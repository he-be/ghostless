"""
MIDI Tester for 3tene Configuration
Use this script to send specific MIDI notes to 3tene for assignment.

Usage:
    python midi_tester.py <note_number>
    
Example:
    python midi_tester.py 60
"""

import sys
import time
import mido

def send_test_note(note, port_partial_name="IAC"):
    try:
        outputs = mido.get_output_names()
        print(f"Available MIDI ports: {outputs}")
        
        # Find a port that contains the partial name
        target_port = next((p for p in outputs if port_partial_name in p), None)
        
        if not target_port:
            print(f"Error: No MIDI port matching '{port_partial_name}' found.")
            # Fallback: Suggest the first one if available
            if outputs:
                print(f"Suggestion: Try using the first available port: '{outputs[0]}'")
            return

        with mido.open_output(target_port) as port:
            print(f"Sending Note On {note} to '{target_port}'...")
            # Send Note On
            port.send(mido.Message('note_on', note=note, velocity=100))
            time.sleep(0.5)
            # Send Note Off (Good practice, though 3tene might only care about On)
            port.send(mido.Message('note_off', note=note, velocity=0))
            print("Done.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python midi_tester.py <note_number>")
        sys.exit(1)
        
    try:
        note_num = int(sys.argv[1])
        send_test_note(note_num)
    except ValueError:
        print("Please provide a valid integer for the note number.")
