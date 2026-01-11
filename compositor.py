"""
Compositor Module
Combines the OBS recording (Visuals), Slides (Background), and WAV files (Audio) into a final video.
"""

import os
import sys
import json
import argparse
import soundfile as sf
from moviepy import *

def get_audio_duration(path):
    f = sf.SoundFile(path)
    return len(f) / f.samplerate

import os
import sys
import json
import argparse
import subprocess
import soundfile as sf
# Use imageio_ffmpeg to ensure we have a valid ffmpeg path
from imageio_ffmpeg import get_ffmpeg_exe
from moviepy import *

def get_audio_duration(path):
    f = sf.SoundFile(path)
    return len(f) / f.samplerate

def main():
    parser = argparse.ArgumentParser(description="Ghostless Compositor (Hybrid)")
    parser.add_argument("scenario", help="Path to scenario.json")
    parser.add_argument("obs_video", help="Path to the OBS recording (.mov/.mp4)")
    parser.add_argument("--similarity", default=0.13, type=float, help="Chroma Key similarity (0.0-1.0)")
    parser.add_argument("--blend", default=0.2, type=float, help="Chroma Key blend (0.0-1.0)")
    parser.add_argument("--audio-offset", default=0.0, type=float, help="Audio sync offset in seconds (e.g. 0.2 to delay audio)")
    parser.add_argument("--output", default="final_output.mp4", help="Output filename")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary background file")
    args = parser.parse_args()

    # Load Scenario
    with open(args.scenario, 'r', encoding='utf-8') as f:
        scenario = json.load(f)

    assets_dir = os.path.dirname(os.path.abspath(args.scenario))
    voice_dir = os.path.join(assets_dir, "voice")
    images_dir = os.path.join(assets_dir, "images")

    # --- Step 1: Prepare Assets (Speed Optimized) ---
    print("[Step 1] Preparing Assets...")
    
    # Try to load recording_log.json for precise timing
    log_path = os.path.join(assets_dir, "recording_log.json")
    event_log = None
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            event_log = data.get("events", [])
            print(f"Loaded Recording Log from {log_path} ({len(event_log)} events)")

    # Lists for reconstruction
    audio_clips = []
    slide_events = [] # (time, file)
    
    if event_log:
        # Reconstruct from Log
        event_log.sort(key=lambda x: x["time"])
        for event in event_log:
            if event["type"] == "slide":
                slide_events.append((event["time"], os.path.join(images_dir, event["file"])))
            elif event["type"] == "audio":
                p = os.path.join(voice_dir, event["file"])
                if os.path.exists(p):
                    audio_start = event["time"] + args.audio_offset
                    audio_clips.append(AudioFileClip(p).with_start(audio_start))
        
        # Calculate End Time
        if audio_clips:
             last_audio = audio_clips[-1]
             total_duration = last_audio.start + last_audio.duration + 2.0
        else:
             total_duration = slide_events[-1][0] + 10.0 if slide_events else 10.0
             
    else:
        # Fallback estimation
        print("Warning: Log missing. Using estimation.")
        current_time = 1.0
        total_duration = 1.0
        for scene in scenario.get("scenes", []):
            # Audio
            voice_file = scene.get("voice_file")
            voice_path = os.path.join(voice_dir, voice_file)
            duration = get_audio_duration(voice_path) if os.path.exists(voice_path) else 5.0
            
            p = os.path.join(voice_dir, voice_file)
            if os.path.exists(p):
                 audio_clips.append(AudioFileClip(p).with_start(current_time + 0.5))
            
            # Slide
            image_file = scene.get("image_file")
            p = os.path.join(images_dir, image_file)
            slide_events.append((current_time, p))
            
            step = 0.5 + duration + 0.2
            current_time += step
        total_duration = current_time + 2.0

    # 1. Generate Master Audio (using MoviePy Audio - this is fast)
    print("Generating Master Audio...")
    temp_audio = "temp_master_audio.wav"
    final_audio = CompositeAudioClip(audio_clips)
    # Write audio file (WAV is faster and avoids codec issues)
    final_audio.write_audiofile(temp_audio, fps=44100, logger=None)
    
    # 2. Generate Slides Concat File (for FFmpeg)
    print("Generating Slide Sequence...")
    concat_file = "temp_slides_concat.txt"
    with open(concat_file, 'w', encoding='utf-8') as f:
        # Ensure we cover from 0.0 to end
        # FFmpeg concat: file, duration
        # We need relative durations.
        
        # Add initial black/delay if first slide isn't at 0
        current_head = 0.0
        
        # Fallback black image
        black_img = "temp_black.png"
        if not os.path.exists(black_img):
             # Make a small black image using MoviePy purely for file generation? 
             # Or Pillow.
             from PIL import Image
             Image.new('RGB', (1920, 1080), (0,0,0)).save(black_img)

        sorted_slides = sorted(slide_events, key=lambda x: x[0])
        
        for i, (t, img_path) in enumerate(sorted_slides):
            if not os.path.exists(img_path):
                img_path = black_img
                
            # Gap before this slide?
            if t > current_head:
                gap = t - current_head
                f.write(f"file '{os.path.abspath(black_img)}'\n")
                f.write(f"duration {gap:.3f}\n")
                current_head = t
            
            # Duration of this slide is until next slide or total_duration
            if i < len(sorted_slides) - 1:
                next_t = sorted_slides[i+1][0]
                duration = next_t - t
            else:
                duration = total_duration - t
            
            # Sanity check
            if duration < 0: duration = 0.1
            
            f.write(f"file '{os.path.abspath(img_path)}'\n")
            f.write(f"duration {duration:.3f}\n")
            current_head += duration
            
        # Add final entry again due to FFmpeg quirk? 
        # "Due to a quirk, the last image has to be specified twice" - some docs say.
        # Let's add a dummy entry to ensure the last duration holds?
        # Actually standard practice is just listing them.
        # But if the stream ends, we want it to hold? 
        # We will set -t on output anyway.
        # Let's duplicate the last image with a tiny duration just to close the stream safely.
        if sorted_slides:
            f.write(f"file '{os.path.abspath(sorted_slides[-1][1])}'\n")
            # f.write(f"duration 1.0\n") # Just to make sure it exists

    # --- Step 2: Single Pass FFmpeg Composition ---
    print(f"[Step 2] Compositing with FFmpeg (Hybrid Concat+Overlay)...")
    
    ffmpeg_exe = get_ffmpeg_exe()
    
    # Inputs:
    # 0: Slides (concat)
    # 1: Audio (master audio)
    # 2: OBS Video (greenscreen)
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file, # Input 0: Slides
        "-i", temp_audio, # Input 1: Audio
        "-i", args.obs_video, # Input 2: OBS
        # Scale OBS video to 1080p height (preserve aspect ratio), set fps to 30, chromakey, then overlay centered
        # scale=-1:1080 -> Keep AR, height 1080
        # flags=lanczos -> Better scaling quality
        # fps=30 -> Smooth downsample from 60fps
        # overlay=(W-w)/2:(H-h)/2 -> Center the character
        f"-filter_complex", 
        f"[2:v]fps=30,scale=-1:1080:flags=lanczos,chromakey=0x00FF00:{args.similarity}:{args.blend}[vt];[0:v]fps=30[bg];[bg][vt]overlay=(W-w)/2:(H-h)/2[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "h264_videotoolbox", "-b:v", "8000k", # Increased bitrate slightly
        "-c:a", "copy",
        "-t", str(total_duration),
        args.output
    ]
    
    print("Executing FFmpeg command:")
    print(" ".join(cmd))
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Success! Output saved to: {args.output}")
        if not args.keep_temp:
            if os.path.exists(temp_audio): os.remove(temp_audio)
            if os.path.exists(concat_file): os.remove(concat_file)
            if os.path.exists("temp_black.png"): os.remove("temp_black.png")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed: {e}")

if __name__ == "__main__":
    main()
