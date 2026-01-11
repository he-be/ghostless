"""
Motion Configuration Database
Maps semantic motion tags to 3tene MIDI note numbers.
"""

# 3tene MIDI Note definitions
# These are examples and should be adjusted to match the actual 3tene configuration.
# Standard MIDI notes: C4 is 60.

MOTION_DB = {
    # 挨拶・導入 (Greetings / Intro)
    "greeting": [60, 61],       # [Light Bow, Wave Hand]
    
    # 肯定・同意・強調 (Agree / Positive)
    "agree": [62, 63, 64],      # [Nod, Hand on Chest, Emphasize]
    
    # 否定・困惑 (Deny / Negative)
    "deny": [65, 66],           # [Shake Head, Shrug]
    
    # 思考・説明 (Thinking / Explaining)
    "thinking": [67, 68],       # [Hand on Chin, Fold Arms]
    
    # 待機・ニュートラル (Neutral)
    "neutral": [None]           # No specific motion command
}

# Intensity modifiers (Optional, for future expansion)
INTENSITY_MAP = {
    "low": 0,
    "normal": 1,
    "high": 2
}
