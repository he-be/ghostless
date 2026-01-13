"""
Motion Configuration Module
Maps semantic tags to OSC messages for Unity control.
"""

# Dictionary mapping semantic tags to a list of potential OSC actions.
# Each action is a dict with:
# - address: OSC address string
# - value: Value to send (float/int/bool)
# - duration: Duration to hold the state (optional, for discrete triggers) or transition time

MOTION_DB = {
    # Basic Expressions
    "neutral": [
        {"address": "/avatar/parameters/Expression", "value": 0}
    ],
    "joy": [
        {"address": "/avatar/parameters/Expression", "value": 1} # Assuming 1 is Joy
    ],
    "angry": [
        {"address": "/avatar/parameters/Expression", "value": 2} # Assuming 2 is Angry
    ],
    "sorrow": [
        {"address": "/avatar/parameters/Expression", "value": 3} # Assuming 3 is Sorrow
    ],
    "fun": [
        {"address": "/avatar/parameters/Expression", "value": 4} # Assuming 4 is Fun
    ],

    # Motions / Gestures
    "greeting": [
        {"address": "/avatar/parameters/Gesture", "value": 1} # Wave or Bow
    ],
    "agree": [
        {"address": "/avatar/parameters/Gesture", "value": 2} # Nod
    ],
    "deny": [
        {"address": "/avatar/parameters/Gesture", "value": 3} # Head shake
    ],
    
    # Pre-motions (preparation before speaking)
    "pre_talk": [
         {"address": "/avatar/parameters/Breath", "value": 1.0} # Inhale
    ]
}
