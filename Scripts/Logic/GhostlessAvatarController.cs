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
        [SerializeField] private float _eyeWanderAmount = 5.0f; // Degrees
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

        private void InitializeBones()
        {
            if (_animator == null) return;

            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
            var head = _animator.GetBoneTransform(HumanBodyBones.Head);
            var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);

            if (chest) _initChestRot = chest.localRotation;
            if (spine) _initSpineRot = spine.localRotation;
            if (head) _initHeadRot = head.localRotation;
            if (lEye) _initLeftEyeRot = lEye.localRotation;
            if (rEye) _initRightEyeRot = rEye.localRotation;

            // Find Face Mesh for Blinking (Direct BlendShape Control for micro-latency)
            var smrs = GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach(var smr in smrs)
            {
                if (smr.sharedMesh.blendShapeCount > 0)
                {
                    _faceMesh = smr;
                    _blinkLIndex = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_L"); // VRM standard-ish
                    if (_blinkLIndex == -1) _blinkLIndex = smr.sharedMesh.GetBlendShapeIndex("Blink_L");
                    
                    _blinkRIndex = smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_R");
                    if (_blinkRIndex == -1) _blinkRIndex = smr.sharedMesh.GetBlendShapeIndex("Blink_R");
                    
                    if (_blinkLIndex != -1) break; // Found it
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

            // Autonomy Updates
            UpdateBreathing();
            UpdateSway();
            UpdateEyeLook();
            
            // Apply Blink Logic (Override VRM)
            if (_faceMesh != null && _enableBlinking)
            {
                if (_blinkLIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkLIndex, _currentBlinkWeight);
                if (_blinkRIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkRIndex, _currentBlinkWeight);
            }
        }

        // --- Autonomy Implementation ---

        private void UpdateBreathing()
        {
            if (!_enableBreathing) return;

            float rate = _breathSpeed * (0.8f + (_arousal * 0.5f)); 
            if (_isSpeaking) rate *= 1.2f;

            _breathTimer += Time.deltaTime * rate;

            float sinVal = Mathf.Sin(_breathTimer);
            float intensity = _breathIntensity * (0.5f + (_arousal * 0.5f));
            
            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            if (chest)
            {
                // Simple chest 'heave'
                chest.localRotation = _initChestRot * Quaternion.Euler(sinVal * intensity, 0, 0);
            }
        }

        private void UpdateSway()
        {
            if (!_enableSway) return;

            float t = Time.time * _swaySpeed;
            float noiseYaw = (Mathf.PerlinNoise(t, 0) - 0.5f) * 2.0f; 
            float noiseRoll = (Mathf.PerlinNoise(0, t) - 0.5f) * 2.0f;

            float magnitude = _swayAmount * (0.5f + (_arousal * 0.5f));
            if (_isSpeaking) magnitude *= 1.5f; 

            var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
            if (spine)
            {
                spine.localRotation = _initSpineRot * Quaternion.Euler(noiseRoll * magnitude * 0.5f, noiseYaw * magnitude, 0);
            }
        }
        
        private void UpdateEyeLook()
        {
            if (!_enableEyeWander) return;
            
            float t = Time.time * _eyeWanderSpeed;
            // Separate noise for X (Pitch) and Y (Yaw)
            // Eyes usually move together
            
            // Slow wander + occasional saccade could be complex, but Perlin is a good start for 'alive' drift
            float wanderX = (Mathf.PerlinNoise(t, 10) - 0.5f) * 2.0f * _eyeWanderAmount; // Pitch (Up/Down)
            float wanderY = (Mathf.PerlinNoise(t, 20) - 0.5f) * 2.0f * _eyeWanderAmount * 1.5f; // Yaw (Left/Right) is usually wider

            var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);

            if (lEye) lEye.localRotation = _initLeftEyeRot * Quaternion.Euler(wanderX, wanderY, 0);
            if (rEye) rEye.localRotation = _initRightEyeRot * Quaternion.Euler(wanderX, wanderY, 0);
        }

        private IEnumerator BlinkRoutine()
        {
             while (true)
             {
                 if (_enableBlinking)
                 {
                     // Blink Close
                     float duration = 0.1f;
                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         float val = (t / duration) * 100f;
                         _currentBlinkWeight = val;
                         yield return null;
                     }
                     _currentBlinkWeight = 100f;

                     // Hold 
                     yield return new WaitForSeconds(0.02f);

                     // Blink Open
                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         float val = 100f - ((t / duration) * 100f);
                         _currentBlinkWeight = val;
                         yield return null;
                     }
                     _currentBlinkWeight = 0f;
                 }

                 // Wait for next blink
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
