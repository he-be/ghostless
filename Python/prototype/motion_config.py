"""
Motion Configuration Module
Maps semantic tags to OSC messages for Unity control.
"""

# Dictionary mapping semantic tags to a list of potential OSC actions.
# Each action is a dict with:
# - address: OSC address string
# - value: Value to send (float/int/string)
# - duration: Duration to hold the state (optional)

MOTION_DB = {
    # Basic Expressions (State Based)
    "neutral": [
        {"address": "/ghostless/state/emotion", "value": "neutral"}
    ],
    "joy": [
        {"address": "/ghostless/state/emotion", "value": "joy"}
    ],
    "angry": [
        {"address": "/ghostless/state/emotion", "value": "angry"}
    ],
    "sorrow": [
        {"address": "/ghostless/state/emotion", "value": "sorrow"}
    ],
    "fun": [
        {"address": "/ghostless/state/emotion", "value": "fun"}
    ],
    "surprise": [
        {"address": "/ghostless/state/emotion", "value": "surprise"}
    ],

    # Motions / Gestures (Trigger Based)
    # Ideally simpler triggers, or mapped to specific logic in Unity
    "greeting": [
        {"address": "/ghostless/trigger/gesture", "value": "bow"} 
    ],
    "agree": [
        {"address": "/ghostless/trigger/gesture", "value": "nod"}
    ],
    "deny": [
        {"address": "/ghostless/trigger/gesture", "value": "shake"}
    ],
    
    # Pre-motions (preparation before speaking)
    "pre_talk": [
         # Triggers Inhale behavior via Speaking State = True (will be set explicitly by Director too, but this acts as the 'cue')
         {"address": "/ghostless/control/speech", "value": 1.0} 
    ]
}
