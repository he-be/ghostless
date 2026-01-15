using UnityEngine;
using UniVRM10;
using System.Collections;

namespace Ghostless
{
    [DefaultExecutionOrder(21000)]
    public class GhostlessMotionController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Animator _animator;
        [SerializeField] private Vrm10Instance _vrmInstance;

        [Header("Breathing")]
        [SerializeField] private bool _enableBreathing = true;
        [SerializeField] private float _breathIntensity = 1.0f;
        [SerializeField] private float _breathSpeed = 1.0f;

        [Header("Sway")]
        [SerializeField] private bool _enableSway = true;
        [SerializeField] private float _swayAmount = 1.0f;
        [SerializeField] private float _swaySpeed = 0.5f;

        // Internal State
        private Quaternion _initHipsRot;
        private Quaternion _initChestRot;
        private Quaternion _initSpineRot;
        private Quaternion _initHeadRot;
        private Quaternion _initLeftArmRot;
        private Quaternion _initRightArmRot;
        
        private float _breathTimer;
        private Quaternion _cumulativeBodySway = Quaternion.identity;
        private Quaternion _smoothedHeadRot = Quaternion.identity;

        // Speech Dynamics State
        private float _headSaccadeTimer = 0f;
        private Quaternion _headSaccadeOffset = Quaternion.identity;
        private Quaternion _targetHeadSaccadeOffset = Quaternion.identity;
        private float _headSaccadeSpeed = 2.0f;
        
        // External State
        private float _arousal = 0.5f;
        private bool _isSpeaking;
        private bool _debugSpeechOverride;
        private float _debugSpeechValue;

        public void SetArousal(float arousal) => _arousal = arousal;
        public void SetSpeakingState(bool isSpeaking) => _isSpeaking = isSpeaking;
        public void SetDebugSpeech(bool isOverride, float value) 
        { 
            _debugSpeechOverride = isOverride; 
            _debugSpeechValue = value; 
        }

        public void Initialize(Animator animator, Vrm10Instance vrmInstance)
        {
            _animator = animator;
            _vrmInstance = vrmInstance;

            if (_animator)
            {
                var hips = _animator.GetBoneTransform(HumanBodyBones.Hips); 
                var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
                var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
                var head = _animator.GetBoneTransform(HumanBodyBones.Head);
                var lArm = _animator.GetBoneTransform(HumanBodyBones.LeftUpperArm);
                var rArm = _animator.GetBoneTransform(HumanBodyBones.RightUpperArm);

                if (hips) _initHipsRot = hips.localRotation;
                if (chest) _initChestRot = chest.localRotation;
                if (spine) _initSpineRot = spine.localRotation;
                if (head) _initHeadRot = head.localRotation;
                if (lArm) _initLeftArmRot = lArm.localRotation;
                if (rArm) _initRightArmRot = rArm.localRotation;
            }
        }

        public void ManualLateUpdate()
        {
            if (!_animator) return;
            UpdateBreathing();
            UpdateSway(); // Calculates _cumulativeBodySway
            UpdateHeadMotion(); // Uses _cumulativeBodySway
            UpdateArmMotion();
        }

        private float GetSpeechIntensity()
        {
            if (_debugSpeechOverride) return Mathf.Clamp01(_debugSpeechValue);

            if (_vrmInstance == null || _vrmInstance.Runtime == null) return 0f;

            // Sum up vowel weights (0.0 - 1.0)
            float intensity = 0f;
            intensity += _vrmInstance.Runtime.Expression.GetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.aa));
            intensity += _vrmInstance.Runtime.Expression.GetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.ih));
            intensity += _vrmInstance.Runtime.Expression.GetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.ou));
            intensity += _vrmInstance.Runtime.Expression.GetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.ee));
            intensity += _vrmInstance.Runtime.Expression.GetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.oh));
            
            return Mathf.Clamp01(intensity); 
        }

        private void UpdateBreathing()
        {
            if (!_enableBreathing) return;

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

        private void UpdateSway()
        {
            if (!_enableSway) return;

            float t = Time.time * _swaySpeed;
            float noiseYaw = (Mathf.PerlinNoise(t, 0) - 0.5f) * 2.0f; 
            float noiseRoll = (Mathf.PerlinNoise(0, t) - 0.5f) * 2.0f;
            float noisePitch = (Mathf.PerlinNoise(t, t) - 0.5f) * 2.0f;

            float baseMag = 0.6f; 
            float magnitude = baseMag * (0.5f + (_arousal * 0.5f));
            if (_isSpeaking) magnitude *= 1.2f; 

            var spine = _animator.GetBoneTransform(HumanBodyBones.Spine);
            var chest = _animator.GetBoneTransform(HumanBodyBones.Chest);
            
            Quaternion spineRotOffset = Quaternion.Euler(noisePitch * magnitude * 0.1f, noiseYaw * magnitude * 0.3f, noiseRoll * magnitude * 1.5f);
            Quaternion chestRotOffset = Quaternion.Euler(noisePitch * magnitude * 0.1f, noiseYaw * magnitude * 0.3f, noiseRoll * magnitude * 0.8f);

            if (spine) spine.localRotation = _initSpineRot * spineRotOffset;
            if (chest) chest.localRotation = _initChestRot * chestRotOffset;
            
            _cumulativeBodySway = spineRotOffset * chestRotOffset;
        }

        private void UpdateHeadMotion()
        {
            var head = _animator.GetBoneTransform(HumanBodyBones.Head);
            if (!head) return;

            // 1. Natural Head Drift
            float t = Time.time * (_swaySpeed * 1.0f); 
            
            float driftYaw = (Mathf.PerlinNoise(t + 10, 0) - 0.5f) * 2.0f; 
            float driftPitch = (Mathf.PerlinNoise(0, t + 10) - 0.5f) * 2.0f;
            float driftRoll = (Mathf.PerlinNoise(t + 5, t + 5) - 0.5f) * 2.0f;

            float driftMag = 1.0f * (1.0f + _arousal); 
            Quaternion naturalDrift = Quaternion.Euler(driftPitch * driftMag * 0.5f, driftYaw * driftMag, driftRoll * driftMag * 0.3f);

            // 2. Speech Dynamics
            Quaternion speakJitter = Quaternion.identity;
            
            float signal = GetSpeechIntensity(); 
            bool effectivelySpeaking = (signal > 0.05f) || _debugSpeechOverride;

            if (effectivelySpeaking)
            {
                float intensity = signal;
                // Reduced speed for Jitter (50%)
                float st = Time.time * 12.5f; 
                float speakYaw = (Mathf.PerlinNoise(st, 0) - 0.5f) * 1.0f;
                float speakPitch = (Mathf.PerlinNoise(0, st) - 0.5f) * 2.0f;
                float speakRoll = (Mathf.PerlinNoise(st, st) - 0.5f) * 2.0f;

                // Reduced Magnitude 
                float speakMag = (1.2f * intensity) + (_arousal * 0.5f * intensity);
                speakJitter = Quaternion.Euler(speakPitch * speakMag, speakYaw * speakMag * 0.5f, speakRoll * speakMag * 0.5f);
                
                // Saccades
                _headSaccadeTimer -= Time.deltaTime;
                if (_headSaccadeTimer <= 0)
                {
                    float rnd = Random.value;
                    if (rnd < 0.4f) 
                    {
                        // Glance Side 
                        float angle = Random.Range(1.5f, 3.5f) * (Random.value > 0.5f ? 1f : -1f);
                        _targetHeadSaccadeOffset = Quaternion.Euler(Random.Range(-0.5f, 0.5f), angle, Random.Range(-0.5f, 0.5f));
                        _headSaccadeSpeed = 8.0f; 
                        _headSaccadeTimer = Random.Range(2.0f, 6.0f); 
                    }
                    else if (rnd < 0.6f) 
                    {
                        // Nod 
                        float angle = Random.Range(1.5f, 3.5f);
                        _targetHeadSaccadeOffset = Quaternion.Euler(angle, Random.Range(-0.5f, 0.5f), 0);
                        _headSaccadeSpeed = 10.0f; 
                        _headSaccadeTimer = Random.Range(1.2f, 3.2f);
                    }
                    else
                    {
                        // Return to Center
                        _targetHeadSaccadeOffset = Quaternion.identity;
                        _headSaccadeSpeed = 2.0f;
                        _headSaccadeTimer = Random.Range(4.0f, 8.0f);
                    }
                }
            }
            else
            {
                _targetHeadSaccadeOffset = Quaternion.identity;
                _headSaccadeSpeed = 2.0f;
            }
            
            _headSaccadeOffset = Quaternion.Slerp(_headSaccadeOffset, _targetHeadSaccadeOffset, Time.deltaTime * _headSaccadeSpeed);

            // 3. Stabilization
            Quaternion fullStabilization = Quaternion.Inverse(_cumulativeBodySway);
            Quaternion partialStabilization = Quaternion.Slerp(Quaternion.identity, fullStabilization, 0.5f);
            
            Quaternion targetRot = _initHeadRot * partialStabilization * _headSaccadeOffset * naturalDrift * speakJitter;

            head.localRotation = targetRot;
        }

        private void UpdateArmMotion()
        {
            float t = Time.time;
            float leftArmX = Mathf.Sin(t * _breathSpeed) * 2.0f; 
            float rightArmX = Mathf.Sin(t * _breathSpeed) * 2.0f;
            
            if (_isSpeaking)
            {
                float st = Time.time * 6.0f; 
                float gestureL = (Mathf.PerlinNoise(st, 0) - 0.2f) * 10.0f; 
                float gestureR = (Mathf.PerlinNoise(0, st) - 0.2f) * 10.0f;
                leftArmX += gestureL;
                rightArmX += gestureR;
            }

            var lArm = _animator.GetBoneTransform(HumanBodyBones.LeftUpperArm);
            var rArm = _animator.GetBoneTransform(HumanBodyBones.RightUpperArm);

            float baseAngle = 65.0f;
            float drift = (Mathf.PerlinNoise(t*0.2f, 50) - 0.5f) * 5.0f;

            if (lArm)
            {
                Quaternion targetRot = _initLeftArmRot * Quaternion.Euler(0, 0, baseAngle + drift - (leftArmX * (_isSpeaking?1.0f:0.2f)));
                lArm.localRotation = Quaternion.Slerp(lArm.localRotation, targetRot, Time.deltaTime * 5f);
            }
            if (rArm)
            {
                Quaternion targetRot = _initRightArmRot * Quaternion.Euler(0, 0, -baseAngle - drift + (rightArmX * (_isSpeaking?1.0f:0.2f)));
                rArm.localRotation = Quaternion.Slerp(rArm.localRotation, targetRot, Time.deltaTime * 5f);
            }
        }
    }
}
