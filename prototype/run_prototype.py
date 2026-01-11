"""
Ghostless Prototype Runner
Main entry point to execute the automation workflow.
"""

import os
import argparse
from scene_director import SceneDirector

def main():
    parser = argparse.ArgumentParser(description="Ghostless Automation Prototype")
    parser.add_argument("scenario", help="Path to the JSON scenario file", default="test_scenario.json", nargs="?")
    parser.add_argument("--obs-pass", help="OBS WebSocket Password", default="")
    args = parser.parse_args()

    # Deduce assets_dir from scenario path
    scenario_path = os.path.abspath(args.scenario)
    assets_dir = os.path.dirname(scenario_path)
    # If scenario is just a filename in CWD, assets_dir is CWD.
    # But if we run as `python prototype/run_prototype.py assets_sample_1/scenario.json`, 
    # and we are in root, assets_dir will be /path/to/assets_sample_1.
    
    # If using default test_scenario.json which might be in prototype/, we need to be careful.
    # For now, let's trust the user to provide a path relative to CWD or absolute.
    
    print(f"Initializing Ghostless Director...")
    print(f"Scenario: {scenario_path}")
    print(f"Assets Dir: {assets_dir}")
    
    director = SceneDirector(scenario_path, assets_dir=assets_dir, obs_pass=args.obs_pass)
    director.run()

if __name__ == "__main__":
    main()
