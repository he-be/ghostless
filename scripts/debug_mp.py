import mediapipe as mp
print(f"File: {mp.__file__}")
print(f"Dir: {dir(mp)}")
try:
    import mediapipe.python.solutions as solutions
    print("Direct import of solutions successful")
except ImportError as e:
    print(f"Direct import failed: {e}")
