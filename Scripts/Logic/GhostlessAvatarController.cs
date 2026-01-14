using UnityEngine;
using UniVRM10;
using System.Collections;
using System.Collections.Generic;

namespace Ghostless
{
    /// <summary>
    /// The "Actor" brain.
    /// Manages autonomous behaviors (breathing, blinking, sway, gaze) and high-level emotion states.
    /// Receives commands from the "Director" (via GhostlessOscInput) but runs its own micro-movements.
    /// </summary>
    [DefaultExecutionOrder(21000)] // Run AFTER VRM (usually ~10000) to ensure overrides apply
    public class GhostlessAvatarController : MonoBehaviour
    {
        [Header("Target Avatar")]
        [SerializeField] private Vrm10Instance _vrmInstance;
        [SerializeField] private Animator _animator;

        [Header("Autonomy Settings")]
        [SerializeField] private bool _enableBreathing = true;
        [SerializeField] private float _breathIntensity = 1.0f;
        [SerializeField] private float _breathSpeed = 1.0f;

        [SerializeField] private bool _enableBlinking = true;
        [SerializeField] private float _baseBlinkInterval = 3.0f;

        [SerializeField] private bool _enableSway = true;
        [SerializeField] private float _swayAmount = 1.0f;
        [SerializeField] private float _swaySpeed = 0.5f;

        [SerializeField] private bool _enableEyeWander = true;
        [SerializeField] private float _eyeWanderAmount = 3.0f; // Degrees
        [SerializeField] private float _eyeWanderSpeed = 0.3f;

        [Header("State (ReadOnly)")]
        [SerializeField] private string _currentEmotion = "neutral";
        [SerializeField] private float _arousal = 0.5f; // 0.0 = sleep, 1.0 = excited
        [SerializeField] private bool _isSpeaking = false;

        // Internal State
        private float _breathTimer;
        private Quaternion _initChestRot;
        private Quaternion _initSpineRot;
        private Quaternion _initHeadRot;
        private Quaternion _initLeftEyeRot;
        private Quaternion _initRightEyeRot;
        private Quaternion _initLeftArmRot;
        private Quaternion _initRightArmRot;
        
        private Coroutine _blinkCoroutine;
        private SkinnedMeshRenderer _faceMesh;
        private int _blinkLIndex = -1;
        private int _blinkRIndex = -1;
        private float _currentBlinkWeight = 0f;

        // VRM 1.0 Standard Expression Keys
        private Dictionary<string, ExpressionKey> _emotionMap;

        private void Start()
        {
            if (_vrmInstance == null) _vrmInstance = GetComponent<Vrm10Instance>();
            if (_animator == null && _vrmInstance != null) _animator = _vrmInstance.GetComponent<Animator>();

            InitializeBones();
            InitializeExpressions();

            if (_enableBlinking)
            {
                _blinkCoroutine = StartCoroutine(BlinkRoutine());
            }
        }

        private Vector3 _initHipsPos;
        private Quaternion _initHipsRot; // New rotation field
        private Vector3 _initHeadPos; 

        private void InitializeBones()
        {
            if (_animator == null) 
            {
                Debug.LogError("[Ghostless] Animator is null in InitializeBones!");
                return;
            }

            var hips = _animator.GetBoneTransform(HumanBodyBones.Hips); 
            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
            var head = _animator.GetBoneTransform(HumanBodyBones.Head);
            var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);
            var lArm = _animator.GetBoneTransform(HumanBodyBones.LeftUpperArm);
            var rArm = _animator.GetBoneTransform(HumanBodyBones.RightUpperArm);

            if (hips)
            {
                 _initHipsPos = hips.localPosition;
                 _initHipsRot = hips.localRotation;
            }
            if (chest) _initChestRot = chest.localRotation;
            if (spine) _initSpineRot = spine.localRotation;
            if (head) 
            {
                _initHeadRot = head.localRotation;
                _initHeadPos = head.localPosition; 
            }
            if (lEye) _initLeftEyeRot = lEye.localRotation;
            if (rEye) _initRightEyeRot = rEye.localRotation;
            if (lArm) _initLeftArmRot = lArm.localRotation;
            if (rArm) _initRightArmRot = rArm.localRotation;

            Debug.Log($"[Ghostless] Bones Initialized. Hips: {hips!=null}, Chest: {chest!=null}, Head: {head!=null}, Arms: {lArm!=null}/{rArm!=null}");

            // ... Face Mesh finding ...
            var smrs = GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach(var smr in smrs)
            {
                if (smr.sharedMesh.blendShapeCount > 0)
                {
                    _faceMesh = smr;
                    _blinkLIndex = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_L"); 
                    if (_blinkLIndex == -1) _blinkLIndex = smr.sharedMesh.GetBlendShapeIndex("Blink_L");
                    
                    _blinkRIndex = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_R");
                    if (_blinkRIndex == -1) _blinkRIndex = smr.sharedMesh.GetBlendShapeIndex("Blink_R");
                    
                    if (_blinkLIndex != -1) break; 
                }
            }
        }
        
        private void InitializeExpressions()
        {
            // Mapping string keys to VRM 1.0 ExpressionKeys
            _emotionMap = new Dictionary<string, ExpressionKey>
            {
                { "neutral", ExpressionKey.CreateFromPreset(ExpressionPreset.neutral) },
                { "joy", ExpressionKey.CreateFromPreset(ExpressionPreset.happy) },
                { "angry", ExpressionKey.CreateFromPreset(ExpressionPreset.angry) },
                { "sorrow", ExpressionKey.CreateFromPreset(ExpressionPreset.sad) },
                { "fun", ExpressionKey.CreateFromPreset(ExpressionPreset.relaxed) }, 
                { "surprise", ExpressionKey.CreateFromPreset(ExpressionPreset.surprised) }
            };
        }

        // Use LateUpdate to override VRM animations
        private void LateUpdate()
        {
            if (_vrmInstance == null || _animator == null) return;

            try 
            {
                UpdateBreathing();
            }
            catch (System.Exception e) { Debug.LogError($"[Ghostless] Error in UpdateBreathing: {e.Message}"); }

            try
            {
                UpdateSway();
            }
            catch (System.Exception e) { Debug.LogError($"[Ghostless] Error in UpdateSway: {e.Message}"); }

            try
            {
                UpdateEyeLook();
            }
            catch (System.Exception e) { Debug.LogError($"[Ghostless] Error in UpdateEyeLook: {e.Message}"); }
            
            try
            {
                UpdateArmMotion();
            }
            catch (System.Exception e) { Debug.LogError($"[Ghostless] Error in UpdateArmMotion: {e.Message}"); }
            
            // Apply Blink Logic (Override VRM)
            if (_faceMesh != null && _enableBlinking)
            {
                if (_blinkLIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkLIndex, _currentBlinkWeight);
                if (_blinkRIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkRIndex, _currentBlinkWeight);
            }
        }

        private void UpdateBreathing()
        {
            if (!_enableBreathing) return;

            // Perlin modulation for organic rate/intensity
            float t = Time.time;
            float speedMod = Mathf.PerlinNoise(t * 0.1f, 0) + 0.5f; 
            float intensityMod = Mathf.PerlinNoise(0, t * 0.1f) + 0.5f;

            float rate = _breathSpeed * speedMod * (0.8f + (_arousal * 0.5f)); 
            if (_isSpeaking) rate *= 1.2f;

            _breathTimer += Time.deltaTime * rate;

            float sinVal = Mathf.Sin(_breathTimer);
            float expansion = (sinVal + 1f) * 0.5f;
            float intensity = _breathIntensity * intensityMod * (0.5f + (_arousal * 0.5f));
            
            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            if (chest)
            {
                chest.localRotation = _initChestRot * Quaternion.Euler(expansion * intensity, 0, 0);
            }
        }

        private Quaternion _cumulativeBodySway = Quaternion.identity; // To track body lean for head stabilization

        private void UpdateSway()
        {
            if (!_enableSway) return;

            float t = Time.time * _swaySpeed;
            // Perlin Noise
            float noiseYaw = (Mathf.PerlinNoise(t, 0) - 0.5f) * 2.0f; 
            float noiseRoll = (Mathf.PerlinNoise(0, t) - 0.5f) * 2.0f;
            float noisePitch = (Mathf.PerlinNoise(t, t) - 0.5f) * 2.0f;

            // significantly INCREASED magnitude for visible shoulder movement
            float baseMag = 6.0f; // Increased from 4.0f for stronger lateral shift
            float magnitude = baseMag * (0.5f + (_arousal * 0.5f));
            if (_isSpeaking) magnitude *= 1.2f; 

            var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            var hips = _animator.GetBoneTransform(HumanBodyBones.Hips);
            
            // "IK-like" Kinematic Chain Sway
            // We rotate Spine and Chest to move the Shoulders/Head physically.
            // EMPHASIS: Horizontal Translation (Roll -> Z Axis)
            
            // Correction: Unity Euler(x, y, z) -> x=Pitch, y=Yaw, z=Roll
            // Previous code mapped Roll to X (Pitch), causing Forward/Back movement.
            // We now map Roll to Z (Sideways Lean).
            
            Quaternion spineRotOffset = Quaternion.Euler(noisePitch * magnitude * 0.1f, noiseYaw * magnitude * 0.3f, noiseRoll * magnitude * 1.5f);
            
            Quaternion chestRotOffset = Quaternion.Euler(noisePitch * magnitude * 0.1f, noiseYaw * magnitude * 0.3f, noiseRoll * magnitude * 0.8f);

            if (spine)
            {
                spine.localRotation = _initSpineRot * spineRotOffset;
            }
            if (chest)
            {
                 chest.localRotation = _initChestRot * chestRotOffset;
            }
            
            // Store stability target: The head needs to counter these to stay upright
            _cumulativeBodySway = spineRotOffset * chestRotOffset;
            
            // Hips: Small base stability (optional, keep small or disable if it breaks rig)
            /*
            if (hips) { hips.localRotation = _initHipsRot * Quaternion.Euler(noiseRoll * 0.5f, 0, 0); }
            */

            UpdateHeadMotion();
        }
        
        private void UpdateHeadMotion()
        {
            var head = _animator.GetBoneTransform(HumanBodyBones.Head);
            if (!head) return;

            // 1. Natural Head Drift (The independent head movement)
            float t = Time.time * (_swaySpeed * 3.0f); 
            // Reduced frequency slightly for more "deliberate" look vs "jittery"
            float driftYaw = (Mathf.PerlinNoise(t + 10, 0) - 0.5f) * 2.0f; 
            float driftPitch = (Mathf.PerlinNoise(0, t + 10) - 0.5f) * 2.0f;
            float driftRoll = (Mathf.PerlinNoise(t + 5, t + 5) - 0.5f) * 2.0f;

            float driftMag = 2.0f * (1.0f + _arousal); 
            
            Quaternion naturalDrift = Quaternion.Euler(driftPitch * driftMag * 0.5f, driftYaw * driftMag, driftRoll * driftMag * 0.3f);

            // 2. Speaking Jitter / Vibration
            Quaternion speakJitter = Quaternion.identity;
            if (_isSpeaking)
            {
                float st = Time.time * 20.0f; // Snappier
                float speakYaw = (Mathf.PerlinNoise(st, 0) - 0.5f) * 2.0f;
                float speakPitch = (Mathf.PerlinNoise(0, st) - 0.5f) * 2.0f;
                float speakRoll = (Mathf.PerlinNoise(st, st) - 0.5f) * 2.0f;

                float speakMag = 1.5f + (_arousal * 2.0f); 
                speakJitter = Quaternion.Euler(speakPitch * speakMag, speakYaw * speakMag * 0.5f, speakRoll * speakMag * 0.5f);
            }
            
            // 3. Stabilization (Counter-Rotation)
            // If body leans Left (Roll -), Head must Roll (+) to stay level.
            // "Partially" compensate so the head still leans slightly with the body (Natural).
            // Factor 0.0 = Head locked to Body (Tilts with it)
            // Factor 1.0 = Head perfect Gyro (Stays World Vertical)
            // Factor 0.6 = Natural Human compensation
            
            Quaternion fullStabilization = Quaternion.Inverse(_cumulativeBodySway);
            Quaternion partialStabilization = Quaternion.Slerp(Quaternion.identity, fullStabilization, 0.6f);
            
            Quaternion targetRot = _initHeadRot * partialStabilization * naturalDrift * speakJitter;

            // Apply
            head.localRotation = targetRot;
        }



        private void UpdateArmMotion()
        {
            // 1. Idle Arm Breath/Sway Link
            // Arms lag behind the body slightly
            float t = Time.time;
            float leftArmX = Mathf.Sin(t * _breathSpeed) * 2.0f; // Slight breath heave
            float rightArmX = Mathf.Sin(t * _breathSpeed) * 2.0f;
            
            float noiseT = t * 0.5f;
            float swayZ = (Mathf.PerlinNoise(noiseT, 0) - 0.5f) * 5.0f; // Subtle fwd/back

            // 2. Speaking Gestures
            if (_isSpeaking)
            {
                float st = Time.time * 6.0f; // Gesture speed
                // Random large gestures modulated by Perlin
                float gestureL = (Mathf.PerlinNoise(st, 0) - 0.2f) * 10.0f; // -2 to +8 deg
                float gestureR = (Mathf.PerlinNoise(0, st) - 0.2f) * 10.0f;
                
                // Only lift arms (positive Z usually means arms go OUT or FWD depending on axes, 
                // but here we rotate around Z to lift OUT/UP from sides)
                // Assuming standard T-pose: Z rotation moves arm UP/DOWN in frontal plane.
                
                // Let's add 'Expansion' gestures
                leftArmX += gestureL;
                rightArmX += gestureR;
            }

            var lArm = _animator.GetBoneTransform(HumanBodyBones.LeftUpperArm);
            var rArm = _animator.GetBoneTransform(HumanBodyBones.RightUpperArm);

            // Base Idle Rotation: Rotating arms DOWN (~75 deg). 
            // In standard Unity Humanoid, T-pose is 'identity' usually.
            // Rotations are relative to T-Pose.
            // Left Arm: Rotate -Z to go down.
            // Right Arm: Rotate +Z to go down.
            
            float baseAngle = 65.0f;
            
            // Add randomness to base angle so they aren't robotic
            float drift = (Mathf.PerlinNoise(t*0.2f, 50) - 0.5f) * 5.0f;

            if (lArm)
            {
                // Z axis rotation: Previous -75 was UP (Banzai). So we need +75 for DOWN.
                // Left Arm: +Z Rotation to go Down.
                Quaternion targetRot = _initLeftArmRot * Quaternion.Euler(0, 0, baseAngle + drift - (leftArmX * (_isSpeaking?1.0f:0.2f)));
                lArm.localRotation = Quaternion.Slerp(lArm.localRotation, targetRot, Time.deltaTime * 5f);
            }
            if (rArm)
            {
                // Right Arm: -Z Rotation to go Down.
                Quaternion targetRot = _initRightArmRot * Quaternion.Euler(0, 0, -baseAngle - drift + (rightArmX * (_isSpeaking?1.0f:0.2f)));
                rArm.localRotation = Quaternion.Slerp(rArm.localRotation, targetRot, Time.deltaTime * 5f);
            }
        }

        private enum GazeState { Wander, Glance, Scan }
        private GazeState _gazeState = GazeState.Wander;
        private float _gazeStateTimer = 0f;
        
        // Saccade State
        private float _saccadeTimer = 0f;
        private Vector3 _targetGazePoint = Vector3.zero;
        private Vector3 _currentGaze = Vector3.zero;

        private void UpdateEyeLook()
        {
            if (!_enableEyeWander) return;
            
            // 1. High-Level State Logic (Switching modes)
            _gazeStateTimer -= Time.deltaTime;
            if (_gazeStateTimer <= 0)
            {
                float r = Random.value;
                if (r < 0.7f) 
                {
                    _gazeState = GazeState.Wander;
                    _gazeStateTimer = Random.Range(3.0f, 8.0f); // Stay in wander longer
                }
                else if (r < 0.85f) 
                {
                    _gazeState = GazeState.Glance;
                    _gazeStateTimer = Random.Range(1.0f, 2.0f);
                }
                else 
                {
                    _gazeState = GazeState.Scan;
                    _gazeStateTimer = Random.Range(2.0f, 4.0f);
                }
                // Reset saccade on state change for immediate effect
                _saccadeTimer = 0;
            }

            // 2. Micro-Saccade Logic (Move - Stop - Move)
            _saccadeTimer -= Time.deltaTime;
            if (_saccadeTimer <= 0)
            {
                // Pick new Fixation Point
                if (_gazeState == GazeState.Wander)
                {
                     // Random point within range (Clamped 60% logic applied here in selection)
                     // Center bias: often near (0,0)
                     float rangeX = _eyeWanderAmount * 0.9f; // Yaw (reduced)
                     float rangeY = _eyeWanderAmount * 1.0f; // Pitch
                     
                     // Box-muller gaussian or just simple random?
                     // Simple random is fine, maybe slightly biased to center
                     float u = Random.value;
                     float wX = (u * u) * (Random.value > 0.5f ? 1 : -1) * rangeY; // Pitch
                     float wY = (Random.value - 0.5f) * 2.0f * rangeX; // Yaw

                     _targetGazePoint = new Vector3(wX, wY, 0);
                     _saccadeTimer = Random.Range(0.2f, 1.5f); // Fixation duration
                }
                else if (_gazeState == GazeState.Glance)
                {
                    // Look at specific target (Side Monitor)
                    // Add slight noise
                    float n = (Random.value - 0.5f) * 2.0f;
                    _targetGazePoint = new Vector3(5.0f + n, -15.0f + n, 0);
                    _saccadeTimer = Random.Range(0.5f, 1.0f);
                }
                else if (_gazeState == GazeState.Scan)
                {
                    // Reading / Scanning: Small jumps horizontally
                    // Where are we looking now?
                    float currentY = _targetGazePoint.y;
                    
                    // Move right (negative Y for Right Eye, wait... )
                    // Standard: +Y is Left, -Y is Right (usually).
                    // Let's assume scanning Left->Right (reading)
                    // Start Left (+10), go Right (-10)
                    
                    if (currentY < -5.0f) // End of line
                    {
                        // Return High (Left)
                        currentY = Random.Range(5.0f, 9.0f);
                        // Maybe change line (Pitch)
                        _targetGazePoint = new Vector3(Random.Range(-2f, 2f), currentY, 0);
                        _saccadeTimer = 0.4f; // Return sweep takes time? Or instant?
                    }
                    else
                    {
                        // Jump Right
                        currentY -= Random.Range(2.0f, 4.0f); 
                        _targetGazePoint = new Vector3(_targetGazePoint.x + Random.Range(-0.5f,0.5f), currentY, 0);
                        _saccadeTimer = Random.Range(0.15f, 0.3f); // Fast reading fixations
                    }
                }
            }

            // 3. Move Eyes
            // Saccades are fast. Use high Lerp speed.
            // But 'Ease-Out' is nice.
            _currentGaze = Vector3.Lerp(_currentGaze, _targetGazePoint, Time.deltaTime * 25.0f);

            var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);
            
            // Clamp Outward Rotation (White Eye Prevention)
            float maxOutward = 8.0f; 
            float maxInward = 30.0f; 

            if (lEye) 
            {
                // Left Eye: +Y is Outward
                float clampedY = Mathf.Clamp(_currentGaze.y, -maxInward, maxOutward);
                lEye.localRotation = _initLeftEyeRot * Quaternion.Euler(_currentGaze.x, clampedY, 0);
            }
            if (rEye) 
            {
                // Right Eye: -Y is Outward
                float clampedY = Mathf.Clamp(_currentGaze.y, -maxOutward, maxInward);
                rEye.localRotation = _initRightEyeRot * Quaternion.Euler(_currentGaze.x, clampedY, 0);
            }
        }

        private IEnumerator BlinkRoutine()
        {
             while (true)
             {
                 if (_enableBlinking)
                 {
                     float duration = 0.08f;
                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         _currentBlinkWeight = (t / duration) * 100f;
                         yield return null;
                     }
                     _currentBlinkWeight = 100f;

                     yield return new WaitForSeconds(Random.Range(0.01f, 0.05f));

                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         _currentBlinkWeight = 100f - ((t / duration) * 100f);
                         yield return null;
                     }
                     _currentBlinkWeight = 0f;
                 }

                 if (Random.value < 0.2f) 
                 {
                     yield return new WaitForSeconds(0.1f);
                     continue; 
                 }

                 float baseWait = Random.Range(_baseBlinkInterval * 0.5f, _baseBlinkInterval * 1.5f);
                 float waitTime = baseWait / (1.0f + _arousal); 
                 yield return new WaitForSeconds(waitTime);
             }
        }

        // --- Public / Director API ---

        public void SetEmotion(string emotionName)
        {
            if (_currentEmotion == emotionName) return;
            
            if (_emotionMap.ContainsKey(emotionName))
            {
                _currentEmotion = emotionName;
                ApplyEmotionToVRM(_emotionMap[emotionName]);
            }
            else
            {
                Debug.LogWarning($"[Ghostless] Unknown emotion: {emotionName}");
            }
        }

        private void ApplyEmotionToVRM(ExpressionKey key)
        {
            if (_vrmInstance == null || _vrmInstance.Runtime == null) return;
            
            // Reset others? Assuming VRM handles weights or we just set the main one to 1.0f
            // In a real sophisticated system, we might cross-fade.
            // VRM 1.0 Runtime usually manages a dictionary of weights.
            
            // For simplicity, we just set this preset to 1.
            // Note: This relies on VRM 1.0 Runtime API implementation details.
            // Basic approach: Set all presets to 0, target to 1.
            
            // Using UniVRM10 runtime controller if available, or just sending direct BlendShapes if customized.
            // Let's assume basic VRM 1.0 API usage:
             _vrmInstance.Runtime.Expression.SetWeight(key, 1.0f);
             
             // Reset others (naive approach)
             foreach(var kv in _emotionMap)
             {
                 if (!kv.Value.Equals(key))
                 {
                     _vrmInstance.Runtime.Expression.SetWeight(kv.Value, 0f);
                 }
             }
        }

        public void SetArousal(float value)
        {
            _arousal = Mathf.Clamp01(value);
        }

        public void SetSpeakingState(bool isSpeaking)
        {
            _isSpeaking = isSpeaking;
        }
    }
}
