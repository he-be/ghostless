"""
Scene Director Module
Orchestrates the timing of audio, acting, and background/slide changes.
"""

import os
import time
import json
import soundfile as sf
import sounddevice as sd
from virtual_actor import VirtualActor
from obs_controller import ObsController

class SceneDirector:
    def __init__(self, config_json_path, assets_dir="assets", obs_pass=''):
        self.config_json_path = config_json_path
        self.assets_dir = assets_dir
        self.actor = VirtualActor()
        self.obs = ObsController(password=obs_pass)
        self.scenario_data = self._load_scenario()

    def _load_scenario(self):
        with open(self.config_json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_audio_duration(self, filename):
        """Returns duration of wav file in seconds."""
        path = os.path.join(self.assets_dir, "voice", filename)
        if not os.path.exists(path):
            print(f"Warning: Audio file not found: {path}")
            return 5.0 # Fallback dummy duration
            
        f = sf.SoundFile(path)
        return len(f) / f.samplerate

    def _play_audio(self, filename):
        """Plays audio file to the default output (which should include BlackHole for 3tene)."""
        path = os.path.join(self.assets_dir, "voice", filename)
        if not os.path.exists(path):
            return

        data, fs = sf.read(path, dtype='float32')
        sd.play(data, fs)
        sd.wait() # Wait until finished

    def run(self):
        """Runs the entire scenario."""
        print(f"Starting Project: {self.scenario_data.get('project_title')}")
        
        recording_log = {
            "start_time": 0,
            "events": []
        }
        
        # Start OBS Recording
        self.obs.start_recording()
        
        # Give OBS a moment to stabilize
        time.sleep(1.0)
        
        # Record Start Time (Reference T=0)
        start_time = time.time()
        recording_log["start_time"] = start_time
        
        for scene in self.scenario_data.get("scenes", []):
            # Log Scene Start (for Slide Change)
            scene_start_relative = time.time() - start_time
            
            # Execute Scene
            # We need to capture when audio actually starts inside execute_scene.
            # To avoid major refactoring, we'll modify execute_scene to return audio start time or pass the log list.
            # Let's modify execute_scene to take the log list and reference start time.
            self.execute_scene_with_logging(scene, recording_log["events"], start_time)
            
        # Give a moment of silence at the end
        time.sleep(2.0)
            
        # Stop OBS Recording
        self.obs.stop_recording()
        self.actor.cleanup()
        
        # Save Log
        log_path = os.path.join(self.assets_dir, "recording_log.json")
        with open(log_path, 'w') as f:
            json.dump(recording_log, f, indent=2)
        print(f"Recording Log saved to {log_path}")
        print("Project Finished.")

    def execute_scene_with_logging(self, scene, event_log, start_time):
        """Executes a single scene with logging."""
        scene_id = scene.get("id")
        text = scene.get("text")
        motion_tag = scene.get("motion_tag")
        voice_file = scene.get("voice_file")
        image_file = scene.get("image_file")
        
        print(f"\n--- Scene {scene_id} Start ---")
        print(f"Displaying Slide: {image_file}")
        
        # Log Slide Event
        event_log.append({
            "type": "slide",
            "file": image_file,
            "time": time.time() - start_time
        })
        
        # 1. Pre-computation: Get Duration
        duration = self._get_audio_duration(voice_file)
        
        # 2. Pre-Action
        self.actor.perform_pre_motion()
        time.sleep(0.5)
        
        # 3. Action
        self.actor.perform_motion(motion_tag)
        
        print(f"Playing Audio: {voice_file} ('{text}')")
        
        # Log Audio Event
        audio_start_time = time.time() - start_time
        event_log.append({
            "type": "audio",
            "file": voice_file,
            "time": audio_start_time
        })
        
        self._play_audio(voice_file)
        
        # 4. Post-scene wait
        time.sleep(0.2)
        
        print(f"--- Scene {scene_id} End ---\n")

if __name__ == "__main__":
    # Test run
    director = SceneDirector("test_scenario.json")
    director.run()
