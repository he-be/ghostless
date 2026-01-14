"""
Generate Dummy Assets
Creates dummy WAV files and empty PNG files for testing the prototype.
"""

import os
import numpy as np
import soundfile as sf

def create_sine_wave(filename, duration_sec, freq=440.0, sample_rate=44100):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), False)
    # Generate a simple sine wave
    audio_data = 0.5 * np.sin(2 * np.pi * freq * t)
    
    path = os.path.join("assets/voice", filename)
    sf.write(path, audio_data, sample_rate)
    print(f"Created audio: {path} ({duration_sec}s)")

def create_dummy_image(filename):
    path = os.path.join("assets/images", filename)
    # Create an empty file just to satisfy existence checks if implemented
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
    print(f"Created image: {path}")

def main():
    if not os.path.exists("assets/voice"):
        os.makedirs("assets/voice")
    if not os.path.exists("assets/images"):
        os.makedirs("assets/images")

    # Scene 1
    create_sine_wave("voice_001.wav", 3.0, freq=440.0)
    create_dummy_image("slide_001.png")

    # Scene 2
    create_sine_wave("voice_002.wav", 5.0, freq=554.37) # C#5
    create_dummy_image("slide_002.png")

    # Scene 3
    create_sine_wave("voice_003.wav", 2.0, freq=659.25) # E5
    create_dummy_image("slide_003.png")

if __name__ == "__main__":
    main()
