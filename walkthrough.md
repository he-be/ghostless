# Ghostless Refactoring Walkthrough

## Summary of Changes
We have successfully refactored the Ghostless project to separate responsibilities between Python (Director) and Unity (Actor).

### 1. Unity Side (The Actor)
*   **New Location**: `Assets/Ghostless/Scripts/`
*   **Separation**:
    *   `Logic/GhostlessAvatarController.cs`: Handles **autonomy** (Breathing, Blinking, Sway) and **state** (Emotion, Arousal).
    *   `Network/GhostlessOscInput.cs`: Handles **listening** to OSC and translating commands to the controller.
*   **Legacy**: The old `GhostlessReceiver.cs` has been moved to `Legacy/GhostlessReceiver.cs.bak`.

### 2. Python Side (The Director)
*   **Protocol Update**: `motion_config.py` now uses `/ghostless/state/*` addresses.
*   **Logic Update**: `scene_director.py` and `virtual_actor.py` explicitly manage the "Speaking State" to influence the avatar's breathing and sway intensity during playback.

## Setup Instructions (Unity)

1.  **Open the Scene**: Open your main recording scene.
2.  **Remove Old Script**: Locate the GameObject acting as your receiver (likely has `uOscServer`). Remove the missing script component (which was `GhostlessReceiver`).
3.  **Add New Scripts**:
    *   Add `GhostlessAvatarController` to your VRM Avatar GameObject.
    *   Add `GhostlessOscInput` to the same GameObject (or the one with `uOscServer`).
4.  **Configuration**:
    *   **GhostlessOscInput**: Ensure the `Avatar Controller` field is linked to your VRM GameObject.
    *   **GhostlessAvatarController**:
        *   Assign `Vrm Instance` and `Animator` if not auto-detected.
        *   Adjust `Breath Intensity`, `Sway Amount`, etc. to taste.
    *   **uOscServer**: Ensure it's active and listening on Port **9000** (default).

## Verification Steps

1.  **Play Unity Scene**:
    *   **Breathing**: Chest should heave rhythmically.
    *   **Blinking**: Avatar should blink randomly. (If not, `DefaultExecutionOrder` ensures it overrides VRM).
    *   **Eye Wander**: Eyes should subtly look around (Perlin noise).
2.  **Run Python Test**:
    ```bash
    cd Assets/Ghostless/Python/prototype
    python osc_manual_test.py
    ```
    (Note: You might need to update `osc_manual_test.py` manually if you want to test the new specific addresses, or just run the main director script).
3.  **Run Director**:
    ```bash
    python run_prototype.py
    ```
    *   Check if the avatar nods/changes expression when the script says so.
    *   Check if breathing intensifies when audio plays.

## Protocol Reference

| Function | Address | Value Type |
| :--- | :--- | :--- |
| **Emotion** | `/ghostless/state/emotion` | String (`joy`, `angry`, `neutral`) |
| **Speech** | `/ghostless/control/speech` | Float/Bool (`1.0` = Talking) |
| **Arousal** | `/ghostless/state/arousal` | Float (`0.0` - `1.0`) |
