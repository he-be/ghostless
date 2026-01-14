# Ghostless Project: Architecture Review & Refactoring Plan (v2)

## 1. Critical Analysis of Current State

### 1.1. Protocol Mismatch
*   **Python Side (`motion_config.py`)**: Defines abstract Intent-driven commands (e.g., `joy` tags sends `/avatar/parameters/Expression` = 1).
*   **Unity Side (`GhostlessReceiver.cs`)**: Listens for concrete Control-driven commands (e.g., `/avatar/parameters/BrowsUp`, `/avatar/parameters/EyeBlink`).
*   **Result**: The current Python script cannot effectively control the Unity avatar because the OSC addresses and value types do not match.

### 1.2. Responsibility Ambiguity
*   **Micromanagement Risk**: The Unity receiver exposes low-level parameters like `EyeBlink` and `Breath`. If Python controls these, it must send high-frequency updates (frames per second) to simulate smooth breathing or natural blinking. This introduces:
    *   **Network Jitter**: Stuttering motion if OSC packets arrive irregularly.
    *   **Complexity**: Python "Director" code becomes cluttered with "Body Function" logic.
*   **Goal Definition**: The project goal is "Actual Time Driven" (sync) and "Intent Driven" (high-level). The current Unity implementation is "Puppet Driven" (low-level).

## 2. Proposed Architecture: "Director-Actor" Model

To achieve "Life Injection" (生命感の注入) and efficient automation, we will separate responsibilities strictly.

### 2.1. Python (The Director & Timekeeper)
*   **Role**: Determines *what* happens and *when*.
*   **Responsibilities**:
    *   **Scenario Execution**: Parsing JSON, managing the timeline based on precise WAV duration.
    *   **Intent Signaling**: Sending abstract commands ("Be Happy", "Look Here").
    *   **Audio Playback**: Playing WAV files (which Unity/OBS listens to via Loopback/Virtual Cable).
    *   **Macro-Control**: Triggering major gestures (Nod, Bow).
*   **Does NOT**:
    *   Calculate sine waves for breathing.
    *   Decide when to blink (unless it's a specific "Close Eyes" direction).
    *   Manage bone transitions directly.

### 2.2. Unity (The Autonomous Actor)
*   **Role**: Determines *how* it looks and feels.
*   **Responsibilities**:
    *   **Autonomy (Life Cycle)**:
        *   **Breathing**: Automatically animates chest/spine/shoulders based on an "Intensity" state.
        *   **Blinking**: Procedural random blinking (frequency modifiable by state).
        *   **Micro-movements**: Perlin noise for subtle head/body sway.
    *   **Interpretation**:
        *   Maps "Joy" (Int) -> BlendShape Combination (Mouth_Joy + Brows_Fun + Cheek_Lift).
        *   Smooths transitions (Damping).
    *   **LipSync**:
        *   Uses `OVRLipSync` or `uLipSync` to analyze incoming audio (from Virtual Cable) and drive mouth shapes locally. This warrants best sync without Python needing to send Visemes.

## 3. Communication Protocol (OSC Schema)

We will standardize the OSC address space to be **State-Based** rather than **Value-Based**.

| Category | Address | Type | Value / Description |
| :--- | :--- | :--- | :--- |
| **State** | `/ghostless/state/emotion` | String/Int | `"neutral"`, `"joy"`, `"angry"`, `"sorrow"` (or IDs 0-4) |
| **State** | `/ghostless/state/arousal` | Float | `0.0` - `1.0` (Controls breath speed, sway magnitude) |
| **Action** | `/ghostless/trigger/gesture` | String | `"nod"`, `"shake"`, `"bow"`, `"surprise"` |
| **Control** | `/ghostless/control/look_at` | Vector2 | `(x, y)` from `-1.0` to `1.0` (Screen space target) |
| **Control** | `/ghostless/control/speech` | Bool | `true` (Active speaking, boosts gesture freq), `false` |

## 4. Refactoring Policy

### 4.1. Phase 1: Unity Autonomy (The "Soul")
*   **Action**: Create `GhostlessAvatarController.cs`.
*   **Logic**:
    *   Implement `UpdateBreathing()`: Sine wave -> Chest/Shoulder bones.
    *   Implement `UpdateBlinking()`: Coroutine with random intervals.
    *   Implement `UpdateSway()`: Perlin noise -> Head/Spine rotation.
*   **Removal**: Remove these calculations from `GhostlessReceiver.cs` and remove dependence on external OSC for these.

### 4.2. Phase 2: OSC Standardization (The "Ear")
*   **Action**: Update `GhostlessReceiver.cs` (or rename to `GhostlessOscInput.cs`).
*   **Logic**:
    *   Listen for the new `/ghostless/*` addresses.
    *   Pass data to `GhostlessAvatarController`.
    *   Remove legacy mapping (`/avatar/parameters/HeadYaw` etc. can remain for debug, but primary control moves to high-level).

### 4.3. Phase 3: Python Update (The "Voice")
*   **Action**: Update `motion_config.py` in Python.
*   **Logic**:
    *   Map `joy` tag to `/ghostless/state/emotion` = `joy`.
    *   Map `pre_talk` tag to `/ghostless/control/speech` = `true` (Triggering inhale in Unity).

## 5. Directory Structure Cleanup

Organize `Assets/Ghostless` to separate the two worlds clearly.

```
Assets/Ghostless/
├── Python/                  <-- The Director (Python Env)
│   ├── .venv/
│   ├── scene_director.py
│   ├── motion_config.py
│   └── ...
├── Scripts/                 <-- The Actor (Unity C#)
│   ├── Network/
│   │   └── GhostlessOscInput.cs
│   ├── Logic/
│   │   ├── GhostlessAvatarController.cs
│   │   └── GhostlessAutomator.cs (Blink/Breath)
│   └── Utils/
└── Data/                    <-- JSON Scenarios & Logs
```
