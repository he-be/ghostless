"""
Generate Real Scenario
Parses script.txt and audio files to create a scenario.json.
"""

import os
import json
import re
import random

# Available tags from motion_config
MOTION_TAGS = ["greeting", "agree", "deny", "thinking"]

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def generate_scenario(assets_dir, project_title="Real Asset Test"):
    script_path = os.path.join(assets_dir, "script.txt")
    voice_dir = os.path.join(assets_dir, "voice")
    output_path = os.path.join(assets_dir, "scenario.json")

    # Read Script
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]

    # List Audio Files
    audio_files = [f for f in os.listdir(voice_dir) if f.lower().endswith('.wav')]
    audio_files.sort(key=natural_sort_key)

    if len(lines) != len(audio_files):
        print(f"Error: Mismatch count. Script lines: {len(lines)}, Audio files: {len(audio_files)}")
        # For now, we truncate to the shorter one or error out. 
        # Let's truncate to min to be safe
        min_len = min(len(lines), len(audio_files))
        lines = lines[:min_len]
        audio_files = audio_files[:min_len]

    scenes = []
    for i, (text, audio_file) in enumerate(zip(lines, audio_files)):
        scene_id = f"{i+1:03d}"
        
        # Simple heuristic for tags (or just random for now as requested)
        # First scene is likely greeting, last is likely greeting/bow
        if i == 0:
            tag = "greeting"
        elif i == len(lines) - 1:
            tag = "greeting"
        else:
            tag = random.choice(MOTION_TAGS)

        scene = {
            "id": scene_id,
            "type": "talk",
            "text": text,
            "motion_tag": tag,
            "intensity": "normal",
            "image_file": f"slide_{scene_id}.png", # Placeholder, maybe user has images?
            "voice_file": audio_file
        }
        scenes.append(scene)

    scenario = {
        "project_title": project_title,
        "scenes": scenes
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(scenario, f, indent=2, ensure_ascii=False)
    
    print(f"Generated scenario at {output_path} with {len(scenes)} scenes.")

if __name__ == "__main__":
    generate_scenario("assets_sample_1")
